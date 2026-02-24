from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from ldap3 import Server, Connection, ALL
from dotenv import load_dotenv
import os


# Cargo las variables de entorno desde .env
load_dotenv()


app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")


# ---------------- CONFIGURACIÓN LDAP ----------------
# Aquí configuro los parámetros de conexión a mi servidor LDAP
LDAP_SERVER = os.getenv("LDAP_SERVER", "ldap://172.16.3.13")  # IP o nombre del servidor LDAP
DOMAIN = os.getenv("DOMAIN", "easycom.local")                # Dominio de la empresa
BASE_DN = os.getenv("BASE_DN", "DC=easycom,DC=local")        # Base DN del árbol LDAP
LDAP_PORT = int(os.getenv("LDAP_PORT", "389"))               # Puerto LDAP (389 sin SSL, 636 con SSL)

# Credenciales de administrador para búsquedas LDAP
LDAP_ADMIN_USER = os.getenv("LDAP_ADMIN_USER", "administrador")
LDAP_ADMIN_PASSWORD = os.getenv("LDAP_ADMIN_PASSWORD", "")

# Diccionario para usuarios conectados: {sid: {username, display_name, role}}
usuarios_conectados = {}


# ---------------- AUTENTICACIÓN Y BÚSQUEDA LDAP ----------------
# Aquí separo la autenticación del usuario y la búsqueda de su información

def obtener_info_usuario_ldap(username):
    """
    Obtengo información del usuario usando las credenciales de administrador.
    Así puedo buscar aunque el usuario normal no tenga permisos de búsqueda.
    Si falla, devuelvo información básica.
    """
    try:
        if not LDAP_ADMIN_PASSWORD:
            print("   Credenciales de admin no configuradas")
            return {
                "display_name": username.capitalize(),
                "email": "",
                "grupos": []
            }
        
        server = Server(LDAP_SERVER, port=LDAP_PORT, get_info=ALL, connect_timeout=5)
        admin_dn = f"{LDAP_ADMIN_USER.lower()}@{DOMAIN.lower()}"
        
        print(f"   Buscando información de {username}...")
        conn_admin = Connection(
            server,
            user=admin_dn,
            password=LDAP_ADMIN_PASSWORD,
            auto_bind=True,
            receive_timeout=5
        )
        
        search_filter = f"(|(sAMAccountName={username})(sAMAccountName={username.lower()})(cn={username}))"
        
        conn_admin.search(
            BASE_DN,
            search_filter,
            attributes=["memberOf", "mail", "displayName", "department", "cn", "givenName", "sn"]
        )
        
        info = {
            "display_name": username.capitalize(),
            "email": "",
            "grupos": []
        }
        
        if conn_admin.entries:
            entry = conn_admin.entries[0]
            
            if "displayName" in entry and entry.displayName:
                info["display_name"] = str(entry.displayName)
            elif "givenName" in entry and "sn" in entry and entry.givenName and entry.sn:
                info["display_name"] = f"{entry.givenName} {entry.sn}"
            
            if "mail" in entry and entry.mail:
                info["email"] = str(entry.mail)
            
            if "memberOf" in entry and entry.memberOf:
                info["grupos"] = [str(g) for g in entry.memberOf]
            
            print(f"   Información obtenida: {info['display_name']}")
        
        conn_admin.unbind()
        return info
        
    except Exception as e:
        print(f"   Advertencia: No se pudo obtener información: {str(e)}")
        return {
            "display_name": username.capitalize(),
            "email": "",
            "grupos": []
        }

def autenticar_ldap(username, password):
    """
    Autentico un usuario contra Active Directory usando UPN (User Principal Name).
    Devuelvo: (éxito: bool, grupos: list, email: str, display_name: str)
    
    1. Primero autentico el usuario (verifico credenciales)
    2. Luego busco su información usando las credenciales de administrador (así evito restricciones de permisos)
    """
    try:
        if not username or not password:
            print("Usuario o contraseña vacíos")
            return False, [], "", username

        print(f"Intentando autenticar: {username}")
        
        server = Server(LDAP_SERVER, port=LDAP_PORT, get_info=ALL, connect_timeout=5)

        # Intento múltiples formatos de bind: UPN, user@domain, DOMAIN\user.
        candidates = []
        if '@' in username:
            candidates.append(username)
        candidates.append(f"{username}@{DOMAIN}")
        candidates.append(f"{DOMAIN}\\{username}")

        bind_success = False
        last_error = None

        for cand in candidates:
            print(f"   Intentando bind con: {cand}")
            try:
                conn = Connection(
                    server,
                    user=cand,
                    password=password,
                    auto_bind=True,
                    receive_timeout=5
                )
                conn.unbind()
                bind_success = True
                print(f"   Bind exitoso con: {cand}")
                break
            except Exception as auth_err:
                last_error = auth_err
                print(f"   Bind fallido con {cand}: {auth_err}")

        # Si no funcionó con los formatos sencillos, intento buscar el DN usando admin
        if not bind_success:
            try:
                print("   Intentando buscar distinguishedName del usuario para bind...")
                admin_dn = f"{LDAP_ADMIN_USER}@{DOMAIN}"
                conn_admin = Connection(server, user=admin_dn, password=LDAP_ADMIN_PASSWORD, auto_bind=True, receive_timeout=5)
                search_filter = f"(|(sAMAccountName={username})(userPrincipalName={username})(cn={username}))"
                conn_admin.search(BASE_DN, search_filter, attributes=['distinguishedName'])
                if conn_admin.entries:
                    dn = conn_admin.entries[0].entry_dn
                    print(f"   Encontrado DN: {dn}, intentando bind con DN...")
                    try:
                        conn = Connection(server, user=dn, password=password, auto_bind=True, receive_timeout=5)
                        conn.unbind()
                        bind_success = True
                        print(f"   Bind exitoso con DN: {dn}")
                    except Exception as dn_err:
                        last_error = dn_err
                        print(f"   Bind fallido con DN: {dn}: {dn_err}")
                else:
                    print("   No se encontró DN para el usuario.")
                conn_admin.unbind()
            except Exception as e_admin:
                print(f"   Error buscando DN con admin: {e_admin}")
                last_error = e_admin

        if not bind_success:
            print(f"   Autenticación fallida: {last_error}")
            return False, [], "", username

        print(f"   Autenticación exitosa")

        print(f"   Obteniendo información del usuario...")
        info = obtener_info_usuario_ldap(username)
        
        display_name = info.get("display_name", username.capitalize())
        email = info.get("email", "")
        grupos = info.get("grupos", [])
        
        print(f"   Usuario: {display_name}")
        if email:
            print(f"   Email: {email}")
        print(f"   Grupos: {len(grupos)}")
        
        return True, grupos, email, display_name

    except Exception as e:
        print(f"ERROR LDAP: {str(e)}")
        return False, [], "", username

# Función para obtener el rol basado en grupos
def obtener_rol(grupos):
    """
    Determino el rol del usuario según sus grupos en AD.
    """
    grupos_str = ' '.join(str(g).lower() for g in grupos)
    
    if 'admin' in grupos_str or 'administradores' in grupos_str:
        return 'admin'
    elif 'manager' in grupos_str or 'responsable' in grupos_str:
        return 'manager'
    else:
        return 'user'

    
# ---------------- RUTAS WEB ----------------
@app.route("/")
def index():
    return render_template("login.html")

@app.route("/chat")
def chat():
    return render_template("chat.html")

@app.route("/login", methods=["POST"])
def login():
    """Ruta que maneja el login de usuarios."""
    data = request.json
    username = data.get("user", "").strip()
    password = data.get("password", "").strip()

    if not username or not password:
        return jsonify({"success": False, "error": "Usuario o contraseña vacíos"}), 400

    valido, grupos, email, display_name = autenticar_ldap(username, password)

    if valido:
        rol = obtener_rol(grupos)
        return jsonify({
            "success": True,
            "username": username,
            "display_name": display_name,
            "email": email,
            "role": rol,
            "groups": grupos
        })
    else:
        return jsonify({"success": False, "error": "Credenciales inválidas"}), 401

@socketio.on("connect_user")
def conectar_usuario(data):
    """Maneja la conexión de un usuario al chat."""
    username = data.get("username", "Usuario")
    display_name = data.get("display_name", username)
    role = data.get("role", "user")
    
    # Guardo la información del usuario conectado
    usuarios_conectados[request.sid] = {
        "username": username,
        "display_name": display_name,
        "role": role
    }
    
    mensaje = f"{display_name} ({role}) se ha unido al chat"
    print(f"{mensaje}")
    emit("message", mensaje, broadcast=True)

@socketio.on("send_message")
def recibir_mensaje(data):
    """Manejo los mensajes del chat."""
    user_info = usuarios_conectados.get(request.sid, {
        "username": "Desconocido",
        "display_name": "Desconocido",
        "role": "user"
    })
    
    display_name = user_info.get("display_name", "Desconocido")
    mensaje = data.get("message", "")
    
    if mensaje.strip():
        emit("message", f"{display_name}: {mensaje}", broadcast=True)

@socketio.on("disconnect")
def desconexion():
    """Manejo la desconexión de un usuario."""
    user_info = usuarios_conectados.pop(request.sid, None)
    
    if user_info:
        display_name = user_info.get("display_name", "Alguien")
        mensaje = f"{display_name} salió del chat"
        print(f"{mensaje}")
        emit("message", mensaje, broadcast=True)

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
