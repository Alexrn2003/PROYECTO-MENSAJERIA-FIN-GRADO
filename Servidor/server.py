from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from ldap3 import Server, Connection, ALL

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# ---------------- LDAP CONFIG ----------------
LDAP_SERVER = "ldap://127.0.0.1"   # IP de tu controlador de dominio
DOMAIN = "easycom.local"
BASE_DN = "DC=easycom,DC=local"

usuarios_conectados = {}

# ---------------- LDAP LOGIN ----------------
def autenticar_ldap(username, password):
    user_dn = f"{username}@{DOMAIN}"

    try:
        server = Server(LDAP_SERVER, get_info=ALL)
        conn = Connection(server, user=user_dn, password=password)

        if not conn.bind():
            return False, []

        conn.search(BASE_DN, f"(sAMAccountName={username})", attributes=["memberOf"])
        grupos = conn.entries[0]["memberOf"].values if conn.entries else []

        conn.unbind()
        return True, grupos

    except Exception as e:
        print("Error LDAP:", e)
        return False, []

def obtener_rol(grupos):
    for g in grupos:
        if "ChatAdmins" in g:
            return "ADMIN"
        if "ChatRRHH" in g:
            return "RRHH"
    return "USER"

# ---------------- RUTAS WEB ----------------
@app.route("/")
def index():
    return render_template("login.html")

@app.route("/chat")
def chat():
    return render_template("chat.html")

@app.route("/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("user")
    password = data.get("password")

    valido, grupos = autenticar_ldap(username, password)

    if valido:
        rol = obtener_rol(grupos)
        return jsonify({"success": True, "username": username, "role": rol})
    else:
        return jsonify({"success": False})

# ---------------- CHAT WEBSOCKET ----------------
@socketio.on("connect_user")
def conectar_usuario(data):
    username = data["username"]
    usuarios_conectados[request.sid] = username
    emit("message", f"🔵 {username} se ha unido al chat", broadcast=True)

@socketio.on("send_message")
def recibir_mensaje(data):
    username = usuarios_conectados.get(request.sid, "Desconocido")
    mensaje = data["message"]
    emit("message", f"{username}: {mensaje}", broadcast=True)

@socketio.on("disconnect")
def desconexion():
    username = usuarios_conectados.get(request.sid, "Alguien")
    emit("message", f"🔴 {username} salió del chat", broadcast=True)

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
