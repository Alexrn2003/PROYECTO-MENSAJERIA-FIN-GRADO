# Script alternativo para ejecutar el servidor con acceso desde red
# Requiere ejecutar como administrador

from dotenv import load_dotenv
load_dotenv()

import os
import sys
from server import app, socketio

# Detectar si usar HTTP o HTTPS
USE_HTTPS = os.getenv("USE_HTTPS", "false").lower() == "true"
PORT = int(os.getenv("PORT", 5000))

if __name__ == "__main__":
    print("========================================")
    print("   SERVIDOR EASYCOM (MODO RED)")
    print("   ⚠️  REQUIERE ADMINISTRADOR")
    print("========================================")

    # Configuración HTTPS
    ssl_context = None
    protocol = "HTTP"

    if USE_HTTPS:
        cert_file = "cert.pem"
        key_file = "key.pem"

        if not os.path.exists(cert_file) or not os.path.exists(key_file):
            print(f"❌ Error: No se encontraron los certificados SSL/TLS")
            sys.exit(1)

        ssl_context = (cert_file, key_file)
        protocol = "HTTPS"

    print(f"Protocolo: {protocol}")
    print(f"Puerto: {PORT}")
    print(f"Host: 0.0.0.0 (acceso desde red)")
    print(f"Acceso local: http://localhost:{PORT}")
    print(f"Acceso red: http://192.168.1.1:{PORT} o http://10.0.2.15:{PORT}")
    print("========================================\n")

    try:
        socketio.run(
            app,
            host="0.0.0.0",  # Acceso desde todas las interfaces
            port=PORT,
            debug=False,
            ssl_context=ssl_context
        )
    except PermissionError as e:
        print(f"❌ ERROR DE PERMISOS: {e}")
        print("💡 SOLUCIÓN: Ejecuta este script como administrador")
        sys.exit(1)
    except OSError as e:
        print(f"❌ ERROR DE SOCKET: {e}")
        sys.exit(1)