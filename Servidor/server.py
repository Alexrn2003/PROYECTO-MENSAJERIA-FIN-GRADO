from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from ldap3 import Server, Connection, ALL
from ldap3.utils.conv import escape_filter_chars
from dotenv import load_dotenv
import sqlite3
from datetime import datetime
import os
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

# Middleware para proxy inverso (IIS, nginx, Apache, etc.)
# Permite que Flask conozca el cliente real (IP) y protocolo original (HTTPS)
app.wsgi_app = ProxyFix(
    app.wsgi_app,
    x_for=1,      # De encabezado X-Forwarded-For
    x_proto=1,    # De encabezado X-Forwarded-Proto
    x_host=1,     # De encabezado X-Forwarded-Host
    x_port=1,     # De encabezado X-Forwarded-Port
    x_prefix=1    # De encabezado X-Forwarded-Prefix
)

load_dotenv()

# ---------------- CONFIG ----------------

CORS(app, 
     origins="*",
     allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])

# SocketIO con soporte para proxy inverso HTTPS/WSS
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode="threading",
    # Configuración para HTTPS en producción (IIS)
    engineio_logger=False,  # Desactivar logs detallados
    logger=False,
    # Permitir upgrade a WebSocket
    ping_timeout=60,
    ping_interval=25,
    # Transports en orden de preferencia
    transports=["websocket", "http_long_polling"]
)

limiter = Limiter(get_remote_address, app=app, default_limits=["200 per day"])

LDAP_SERVER   = os.getenv("LDAP_SERVER")
LDAP_PORT     = int(os.getenv("LDAP_PORT", 389))
DOMAIN        = os.getenv("DOMAIN")
BASE_DN       = os.getenv("BASE_DN")
LDAP_ADMIN    = os.getenv("LDAP_ADMIN_USER")
LDAP_PASSWORD = os.getenv("LDAP_ADMIN_PASSWORD")

# Usuarios conectados en este momento: clave = sid del socket
usuarios_conectados = {}

# Qué grupos LDAP corresponden a qué departamento del chat
GRUPOS_DEPARTAMENTO = {
    "rrhh":             "RRHH",
    "recursos humanos": "RRHH",
    "informatica":      "Informatica",
    "it":               "Informatica",
    "ventas":           "Ventas",
    "contabilidad":     "Contabilidad",
    "administracion":   "Administracion",
    "marketing":        "Marketing",
    "soporte":          "Soporte",
}

# Grupos que dan acceso al canal de directivos
GRUPOS_DIRECTIVOS = ["directivos", "direccion", "gerencia", "domain admins", "administrators"]


# ---------------- BASE DE DATOS ----------------

def init_db():
    """Crea las tablas si no existen."""
    conn = sqlite3.connect("historial.db")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS mensajes (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            canal   TEXT NOT NULL,
            usuario TEXT NOT NULL,
            mensaje TEXT NOT NULL,
            fecha   TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

init_db()


# ---------------- HISTORIAL ----------------

def guardar_mensaje(canal, usuario, mensaje):
    """Guarda un mensaje en la base de datos."""
    conn = sqlite3.connect("historial.db")
    conn.execute(
        "INSERT INTO mensajes (canal, usuario, mensaje, fecha) VALUES (?, ?, ?, ?)",
        (canal, usuario, mensaje, datetime.now().strftime("%H:%M"))
    )
    conn.commit()
    conn.close()


def cargar_historial(canal, limite=50):
    """Devuelve los últimos 50 mensajes de un canal."""
    conn = sqlite3.connect("historial.db")
    cursor = conn.execute(
        "SELECT usuario, mensaje, fecha FROM mensajes WHERE canal = ? ORDER BY id DESC LIMIT ?",
        (canal, limite)
    )
    mensajes = [{"usuario": r[0], "mensaje": r[1], "fecha": r[2]} for r in cursor]
    conn.close()
    return list(reversed(mensajes))


def cargar_historial_dm(user1, user2, limite=50):
    """Devuelve los últimos mensajes entre dos usuarios (en ambas direcciones)."""
    canal1 = "dm:" + user1 + ":" + user2
    canal2 = "dm:" + user2 + ":" + user1
    conn = sqlite3.connect("historial.db")
    cursor = conn.execute(
        "SELECT usuario, mensaje, fecha FROM mensajes WHERE canal IN (?, ?) ORDER BY id DESC LIMIT ?",
        (canal1, canal2, limite)
    )
    mensajes = [{"usuario": r[0], "mensaje": r[1], "fecha": r[2]} for r in cursor]
    conn.close()
    return list(reversed(mensajes))


# ---------------- FUNCIONES LDAP ----------------

def autenticar_ldap(username, password):
    """Intenta hacer login con las credenciales del dominio."""
    try:
        if not username or not password:
            return False, [], ""

        servidor = Server(LDAP_SERVER, port=LDAP_PORT, get_info=ALL)
        upn = f"{username}@{DOMAIN}"

        conn = Connection(servidor, user=upn, password=password, auto_bind=True)
        conn.unbind()

        info = buscar_info_usuario(username)
        return True, info["grupos"], info["display_name"]

    except Exception as e:
        print(f"[LOGIN ERROR] {e}")
        return False, [], username


def buscar_info_usuario(username):
    """Busca información del usuario en el Active Directory."""
    try:
        servidor = Server(LDAP_SERVER, port=LDAP_PORT, get_info=ALL)
        admin_upn = f"{LDAP_ADMIN}@{DOMAIN}"

        conn = Connection(servidor, user=admin_upn, password=LDAP_PASSWORD, auto_bind=True)

        nombre_seguro = escape_filter_chars(username)
        conn.search(BASE_DN, f"(sAMAccountName={nombre_seguro})", attributes=["memberOf", "mail", "displayName"])

        info = {"display_name": username, "grupos": []}

        if conn.entries:
            entrada = conn.entries[0]
            if entrada.displayName:
                info["display_name"] = str(entrada.displayName)
            if entrada.memberOf:
                info["grupos"] = [str(g) for g in entrada.memberOf]

        conn.unbind()
        return info

    except Exception as e:
        print(f"[LDAP BUSQUEDA ERROR] {e}")
        return {"display_name": username, "grupos": []}


def nombre_del_grupo(dn):
    """Extrae el nombre del grupo del DN de LDAP."""
    try:
        cn = dn.split(",")[0]
        nombre = cn.split("=")[1]
        return nombre.lower()
    except:
        return ""


def obtener_departamento(grupos):
    """Devuelve el departamento del usuario según sus grupos de LDAP."""
    for dn in grupos:
        nombre = nombre_del_grupo(dn)
        if nombre in GRUPOS_DEPARTAMENTO:
            return GRUPOS_DEPARTAMENTO[nombre]
    return ""


def es_directivo(grupos):
    """Comprueba si el usuario pertenece a un grupo de directivos."""
    for dn in grupos:
        nombre = nombre_del_grupo(dn)
        if nombre in GRUPOS_DIRECTIVOS:
            return True
    return False


# ---------------- RUTAS WEB ----------------

@app.route("/")
def index():
    return render_template("login.html")


@app.route("/chat")
def chat():
    if "username" not in session:
        return render_template("login.html")
    return render_template("chat.html")


@app.route("/login", methods=["POST"])
@limiter.limit("5 per minute")
def login():
    datos = request.json
    username = datos.get("user", "").strip()
    password = datos.get("password", "").strip()

    if len(username) > 50 or len(password) > 128:
        return jsonify({"success": False, "error": "Datos no válidos"}), 400

    valido, grupos, display_name = autenticar_ldap(username, password)

    if not valido:
        return jsonify({"success": False, "error": "Usuario o contraseña incorrectos"}), 401

    departamento = obtener_departamento(grupos)
    directivo    = es_directivo(grupos)

    session["username"]     = username
    session["display_name"] = display_name
    session["departamento"] = departamento
    session["es_directivo"] = directivo
    session["grupos"]       = grupos

    return jsonify({
        "success":      True,
        "display_name": display_name,
        "departamento": departamento,
        "es_directivo": directivo
    })


@app.route("/logout")
def logout():
    session.clear()
    return jsonify({"success": True})


@app.route("/historial/<canal>")
def historial(canal):
    if "username" not in session:
        return jsonify([]), 401
    return jsonify(cargar_historial(canal))


@app.route("/historial_dm/<destinatario>")
def historial_dm(destinatario):
    if "username" not in session:
        return jsonify([]), 401
    return jsonify(cargar_historial_dm(session["username"], destinatario))


# ---------------- PANEL DE ADMINISTRACIÓN ----------------

def es_domain_admin():
    """Comprueba si el usuario actual es Domain Admin."""
    grupos = session.get("grupos", [])
    for dn in grupos:
        nombre = nombre_del_grupo(dn)
        if nombre in ["domain admins", "administrators"]:
            return True
    return False


@app.route("/admin")
def admin_panel():
    if "username" not in session or not es_domain_admin():
        return render_template("login.html")
    return render_template("admin.html")


@app.route("/admin/stats")
def admin_stats():
    if "username" not in session or not es_domain_admin():
        return jsonify({}), 403

    conn = sqlite3.connect("historial.db")

    total = conn.execute("SELECT COUNT(*) FROM mensajes").fetchone()[0]
    dms   = conn.execute("SELECT COUNT(*) FROM mensajes WHERE canal LIKE 'dm:%'").fetchone()[0]

    por_canal = conn.execute(
        """SELECT canal as nombre, COUNT(*) as total
           FROM mensajes WHERE canal NOT LIKE 'dm:%'
           GROUP BY canal ORDER BY total DESC LIMIT 8"""
    ).fetchall()

    por_usuario = conn.execute(
        """SELECT usuario as nombre, COUNT(*) as total
           FROM mensajes GROUP BY usuario ORDER BY total DESC LIMIT 8"""
    ).fetchall()

    conn.close()

    return jsonify({
        "usuarios_conectados": len(set(u["username"] for u in usuarios_conectados.values())),
        "mensajes_hoy":    0,
        "mensajes_total":  total,
        "dms_total":       dms,
        "por_canal":   [{"nombre": r[0], "total": r[1]} for r in por_canal],
        "por_usuario": [{"nombre": r[0], "total": r[1]} for r in por_usuario],
    })


@app.route("/admin/historial")
def admin_historial():
    if "username" not in session or not es_domain_admin():
        return jsonify({}), 403

    pagina  = int(request.args.get("pagina", 1))
    por_pag = int(request.args.get("por_pagina", 30))
    canal   = request.args.get("canal", "").strip()
    usuario = request.args.get("usuario", "").strip()
    offset  = (pagina - 1) * por_pag

    where  = []
    params = []

    if canal:
        where.append("canal = ?")
        params.append(canal)
    if usuario:
        where.append("usuario LIKE ?")
        params.append("%" + usuario + "%")

    clause = ("WHERE " + " AND ".join(where)) if where else ""

    conn   = sqlite3.connect("historial.db")
    total  = conn.execute(f"SELECT COUNT(*) FROM mensajes {clause}", params).fetchone()[0]
    rows   = conn.execute(
        f"SELECT canal, usuario, mensaje, fecha FROM mensajes {clause} ORDER BY id DESC LIMIT ? OFFSET ?",
        params + [por_pag, offset]
    ).fetchall()
    conn.close()

    return jsonify({
        "total": total,
        "mensajes": [{"canal": r[0], "usuario": r[1], "mensaje": r[2], "fecha": r[3]} for r in rows]
    })


@app.route("/admin/usuarios")
def admin_usuarios():
    if "username" not in session or not es_domain_admin():
        return jsonify([]), 403

    vistos = set()
    lista  = []
    for info in usuarios_conectados.values():
        if info["username"] not in vistos:
            vistos.add(info["username"])
            lista.append({
                "username":     info["username"],
                "display_name": info["display_name"],
                "departamento": info["departamento"],
                "es_directivo": info["es_directivo"],
                "dispositivo":  info.get("dispositivo", "—"),
                "ip":           info.get("ip", "—"),
            })

    return jsonify(lista)


@app.route("/admin/expulsar", methods=["POST"])
def admin_expulsar():
    if "username" not in session or not es_domain_admin():
        return jsonify({"ok": False}), 403

    username = request.json.get("username", "")

    for sid, info in list(usuarios_conectados.items()):
        if info["username"] == username:
            socketio.emit("forzar_desconexion", {
                "motivo": "Has sido desconectado por un administrador."
            }, room=sid)

    return jsonify({"ok": True})


@app.route("/admin/canales")
def admin_canales():
    if "username" not in session or not es_domain_admin():
        return jsonify([]), 403

    conn = sqlite3.connect("historial.db")
    rows = conn.execute(
        "SELECT canal, COUNT(*) as total, MAX(fecha) as ultimo FROM mensajes GROUP BY canal ORDER BY total DESC"
    ).fetchall()
    conn.close()

    return jsonify([{"canal": r[0], "total": r[1], "ultimo": r[2]} for r in rows])


@app.route("/admin/borrar_canal", methods=["POST"])
def admin_borrar_canal():
    if "username" not in session or not es_domain_admin():
        return jsonify({"ok": False}), 403

    canal = request.json.get("canal", "")
    if not canal:
        return jsonify({"ok": False}), 400

    conn = sqlite3.connect("historial.db")
    conn.execute("DELETE FROM mensajes WHERE canal = ?", (canal,))
    conn.commit()
    conn.close()

    return jsonify({"ok": True})



def detectar_dispositivo(ua):
    """Devuelve una descripción legible del dispositivo a partir del User-Agent."""
    ua_lower = ua.lower()

    # Sistema operativo
    if "windows nt" in ua_lower:
        if "windows nt 10" in ua_lower:
            so = "Windows 10/11"
        elif "windows nt 6.3" in ua_lower:
            so = "Windows 8.1"
        elif "windows nt 6.1" in ua_lower:
            so = "Windows 7"
        else:
            so = "Windows"
    elif "macintosh" in ua_lower or "mac os x" in ua_lower:
        so = "macOS"
    elif "iphone" in ua_lower:
        so = "iPhone"
    elif "ipad" in ua_lower:
        so = "iPad"
    elif "android" in ua_lower:
        so = "Android"
    elif "linux" in ua_lower:
        so = "Linux"
    else:
        so = "Desconocido"

    # Navegador
    if "edg/" in ua_lower or "edge/" in ua_lower:
        nav = "Edge"
    elif "opr/" in ua_lower or "opera" in ua_lower:
        nav = "Opera"
    elif "chrome/" in ua_lower:
        nav = "Chrome"
    elif "firefox/" in ua_lower:
        nav = "Firefox"
    elif "safari/" in ua_lower:
        nav = "Safari"
    else:
        nav = "Navegador desconocido"

    return f"{so} · {nav}"



# ---------------- SOCKET.IO ----------------

@socketio.on("connect")
def al_conectar():
    if "username" not in session:
        return False

    username     = session["username"]
    display_name = session["display_name"]
    departamento = session["departamento"]
    directivo    = session["es_directivo"]

    # Detectar dispositivo desde User-Agent
    ua = request.headers.get("User-Agent", "")
    dispositivo = detectar_dispositivo(ua)

    usuarios_conectados[request.sid] = {
        "username":     username,
        "display_name": display_name,
        "departamento": departamento,
        "es_directivo": directivo,
        "dispositivo":  dispositivo,
        "user_agent":   ua,
        "ip":           request.remote_addr or "—",
    }

    join_room("global")
    join_room(username)

    if departamento:
        join_room(departamento.lower())

    if directivo:
        join_room("directivos")

    emit("sistema", f"{display_name} se ha conectado", room="global")
    emit("lista_usuarios", _lista_usuarios(), broadcast=True)


@socketio.on("mensaje")
def al_recibir_mensaje(data):
    if "username" not in session:
        return

    display_name = session["display_name"]
    departamento = session["departamento"]
    directivo    = session["es_directivo"]

    canal   = data.get("canal", "global")
    mensaje = data.get("mensaje", "").strip()

    if not mensaje or len(mensaje) > 500:
        return

    if canal == "directivos" and not directivo:
        return

    if canal not in ["global", "directivos"]:
        if canal != departamento.lower():
            return

    guardar_mensaje(canal, display_name, mensaje)

    emit("nuevo_mensaje", {
        "usuario": display_name,
        "mensaje": mensaje,
        "canal":   canal,
        "fecha":   datetime.now().strftime("%H:%M")
    }, room=canal)


@socketio.on("mensaje_directo")
def al_recibir_dm(data):
    if "username" not in session:
        return

    display_name          = session["display_name"]
    username              = session["username"]
    destinatario_username = data.get("destinatario", "")
    mensaje               = data.get("mensaje", "").strip()

    if not mensaje or len(mensaje) > 500 or not destinatario_username:
        return

    destinatario_existe = any(
        u["username"] == destinatario_username
        for u in usuarios_conectados.values()
    )

    if not destinatario_existe:
        return

    hora = datetime.now().strftime("%H:%M")

    # Guardar en base de datos
    guardar_mensaje("dm:" + username + ":" + destinatario_username, display_name, mensaje)

    emit("nuevo_dm", {
        "de":        display_name,
        "de_user":   username,
        "mensaje":   mensaje,
        "fecha":     hora,
        "es_propio": False
    }, room=destinatario_username)

    emit("nuevo_dm", {
        "de":        display_name,
        "de_user":   username,
        "para":      destinatario_username,
        "mensaje":   mensaje,
        "fecha":     hora,
        "es_propio": True
    }, room=username)


@socketio.on("escribiendo")
def al_escribiendo(data):
    if "username" not in session:
        return

    display_name = session["display_name"]
    username     = session["username"]
    tipo         = data.get("tipo", "canal")

    if tipo == "dm":
        destinatario = data.get("destinatario", "")
        if not destinatario:
            return
        emit("escribiendo", {
            "tipo":    "dm",
            "de":      display_name,
            "de_user": username,
        }, room=destinatario)
    else:
        canal = data.get("canal", "global")
        emit("escribiendo", {
            "tipo":    "canal",
            "canal":   canal,
            "de":      display_name,
            "de_user": username,
        }, room=canal, include_self=False)


@socketio.on("disconnect")
def al_desconectar():
    info = usuarios_conectados.pop(request.sid, None)

    if info:
        emit("sistema", f"{info['display_name']} se ha desconectado", room="global")
        emit("lista_usuarios", _lista_usuarios(), broadcast=True)


# ---------------- HELPERS ----------------

def _lista_usuarios():
    """Devuelve una lista limpia de usuarios conectados para el frontend."""
    vistos = set()
    lista  = []

    for info in usuarios_conectados.values():
        u = info["username"]
        if u not in vistos:
            vistos.add(u)
            lista.append({
                "username":     info["username"],
                "display_name": info["display_name"],
                "departamento": info["departamento"]
            })

    return lista


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
