from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from ldap3 import Server, Connection, ALL
from ldap3.utils.conv import escape_filter_chars
from dotenv import load_dotenv
import os

# Cargar variables de entorno
load_dotenv()

# ---------------- CONFIG APP ----------------

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# ---------------- CONFIG LDAP ----------------

LDAP_SERVER = os.getenv("LDAP_SERVER")
LDAP_PORT = int(os.getenv("LDAP_PORT", 389))
DOMAIN = os.getenv("DOMAIN")
BASE_DN = os.getenv("BASE_DN")

LDAP_ADMIN_USER = os.getenv("LDAP_ADMIN_USER")
LDAP_ADMIN_PASSWORD = os.getenv("LDAP_ADMIN_PASSWORD")

usuarios_conectados = {}

# ---------------- LDAP FUNCIONES ----------------

def autenticar_ldap(username, password):
    try:
        if not username or not password:
            return False, [], "", username

        server = Server(LDAP_SERVER, port=LDAP_PORT, get_info=ALL)

        # Formato UPN compatible con AD
        user_upn = f"{username}@{DOMAIN}"

        conn = Connection(
            server,
            user=user_upn,
            password=password,
            auto_bind=True
        )

        conn.unbind()

        info = obtener_info_usuario_ldap(username)

        return True, info["grupos"], info["email"], info["display_name"]

    except Exception as e:
        print("ERROR AUTENTICACION LDAP:", e)
        return False, [], "", username


def obtener_info_usuario_ldap(username):
    try:
        server = Server(LDAP_SERVER, port=LDAP_PORT, get_info=ALL)

        admin_upn = f"{LDAP_ADMIN_USER}@{DOMAIN}"

        conn = Connection(
            server,
            user=admin_upn,
            password=LDAP_ADMIN_PASSWORD,
            auto_bind=True
        )

        safe_username = escape_filter_chars(username)

        search_filter = f"(sAMAccountName={safe_username})"

        conn.search(
            BASE_DN,
            search_filter,
            attributes=["memberOf", "mail", "displayName"]
        )

        info = {
            "display_name": username,
            "email": "",
            "grupos": []
        }

        if conn.entries:
            entry = conn.entries[0]

            if entry.displayName:
                info["display_name"] = str(entry.displayName)

            if entry.mail:
                info["email"] = str(entry.mail)

            if entry.memberOf:
                info["grupos"] = [str(g) for g in entry.memberOf]

        conn.unbind()
        return info

    except Exception as e:
        print("ERROR BUSQUEDA LDAP:", e)
        return {
            "display_name": username,
            "email": "",
            "grupos": []
        }


# ---------------- ROLES ----------------

def obtener_rol(grupos):
    grupos_str = " ".join(g.lower() for g in grupos)

    if "admin" in grupos_str:
        return "admin"
    elif "manager" in grupos_str:
        return "manager"
    return "user"


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
def login():
    data = request.json
    username = data.get("user", "").strip()
    password = data.get("password", "").strip()

    valido, grupos, email, display_name = autenticar_ldap(username, password)

    if not valido:
        return jsonify({"success": False}), 401

    rol = obtener_rol(grupos)

    session["username"] = username
    session["display_name"] = display_name
    session["role"] = rol

    return jsonify({
        "success": True,
        "display_name": display_name,
        "role": rol
    })


# ---------------- SOCKET.IO ----------------

@socketio.on("connect")
def conectar():
    if "username" not in session:
        return False

    usuarios_conectados[request.sid] = {
        "username": session["username"],
        "display_name": session["display_name"],
        "role": session["role"]
    }

    emit(
        "message",
        f"{session['display_name']} se ha unido al chat",
        broadcast=True
    )


@socketio.on("send_message")
def recibir_mensaje(data):
    user_info = usuarios_conectados.get(request.sid)
    if not user_info:
        return

    mensaje = data.get("message", "").strip()

    if mensaje:
        emit(
            "message",
            f"{user_info['display_name']}: {mensaje}",
            broadcast=True
        )


@socketio.on("disconnect")
def desconexion():
    user_info = usuarios_conectados.pop(request.sid, None)

    if user_info:
        emit(
            "message",
            f"{user_info['display_name']} salió del chat",
            broadcast=True
        )


# ⚠️ NO PONEMOS socketio.run AQUÍ
# Solo se arranca desde run.py