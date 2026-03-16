from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from ldap3 import Server, Connection, ALL
from ldap3.utils.conv import escape_filter_chars
from dotenv import load_dotenv
import os

load_dotenv()

# ---------------- CONFIG ----------------

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

CORS(app, origins=["http://localhost:5000"])
socketio = SocketIO(app, cors_allowed_origins=["http://localhost:5000"], async_mode="threading")

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
    """Extrae el nombre del grupo del DN de LDAP.
    Ejemplo: CN=RRHH,OU=Grupos,DC=easycom,DC=local -> rrhh
    """
    try:
        cn = dn.split(",")[0]        # CN=RRHH
        nombre = cn.split("=")[1]    # RRHH
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

    # Validar longitud máxima
    if len(username) > 50 or len(password) > 128:
        return jsonify({"success": False, "error": "Datos no válidos"}), 400

    valido, grupos, display_name = autenticar_ldap(username, password)

    if not valido:
        return jsonify({"success": False, "error": "Usuario o contraseña incorrectos"}), 401

    departamento  = obtener_departamento(grupos)
    directivo     = es_directivo(grupos)

    session["username"]     = username
    session["display_name"] = display_name
    session["departamento"] = departamento
    session["es_directivo"] = directivo

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


# ---------------- SOCKET.IO ----------------

@socketio.on("connect")
def al_conectar():
    if "username" not in session:
        return False

    username     = session["username"]
    display_name = session["display_name"]
    departamento = session["departamento"]
    directivo    = session["es_directivo"]

    # Guardar al usuario
    usuarios_conectados[request.sid] = {
        "username":     username,
        "display_name": display_name,
        "departamento": departamento,
        "es_directivo": directivo
    }

    # Unirse al canal global y al canal personal (para DMs)
    join_room("global")
    join_room(username)

    # Unirse al canal del departamento si tiene uno
    if departamento:
        join_room(departamento.lower())

    # Unirse al canal de directivos si le corresponde
    if directivo:
        join_room("directivos")

    # Avisar al canal global
    emit("sistema", f"{display_name} se ha conectado", room="global")

    # Mandar la lista actualizada de usuarios a todos
    emit("lista_usuarios", _lista_usuarios(), broadcast=True)


@socketio.on("mensaje")
def al_recibir_mensaje(data):
    if "username" not in session:
        return

    username     = session["username"]
    display_name = session["display_name"]
    departamento = session["departamento"]
    directivo    = session["es_directivo"]

    canal   = data.get("canal", "global")
    mensaje = data.get("mensaje", "").strip()

    # Validar mensaje
    if not mensaje or len(mensaje) > 500:
        return

    # Comprobar que el usuario tiene acceso al canal
    if canal == "directivos" and not directivo:
        return

    if canal not in ["global", "directivos"]:
        # Es un canal de departamento, solo puede entrar si es su departamento
        if canal != departamento.lower():
            return

    emit("nuevo_mensaje", {
        "usuario":  display_name,
        "mensaje":  mensaje,
        "canal":    canal
    }, room=canal)


@socketio.on("mensaje_directo")
def al_recibir_dm(data):
    if "username" not in session:
        return

    display_name = session["display_name"]
    username     = session["username"]

    destinatario_username = data.get("destinatario", "")
    mensaje               = data.get("mensaje", "").strip()

    # Validar mensaje
    if not mensaje or len(mensaje) > 500 or not destinatario_username:
        return

    # Comprobar que el destinatario existe (está conectado)
    destinatario_existe = any(
        u["username"] == destinatario_username
        for u in usuarios_conectados.values()
    )

    if not destinatario_existe:
        return

    # Mandar al destinatario
    emit("nuevo_dm", {
        "de":       display_name,
        "de_user":  username,
        "mensaje":  mensaje,
        "es_propio": False
    }, room=destinatario_username)

    # Mandar copia al remitente (para que vea su propio mensaje)
    emit("nuevo_dm", {
        "de":       display_name,
        "de_user":  username,
        "para":     destinatario_username,
        "mensaje":  mensaje,
        "es_propio": True
    }, room=username)


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
