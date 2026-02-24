#!/usr/bin/env python3
"""
Script para iniciar el servidor de chat EasyCom.
Este script carga las variables de entorno y inicia el servidor Flask.
"""

import os
from dotenv import load_dotenv

# Cargar configuración
load_dotenv()

# Mostrar configuración actual
print("=" * 70)
print("SERVIDOR DE CHAT EASYCOM - INICIALIZANDO")
print("=" * 70)
print("\nConfiguración LDAP:")
print(f"   Servidor: {os.getenv('LDAP_SERVER', 'ldap://172.16.3.13')}")
print(f"   Puerto: {os.getenv('LDAP_PORT', '389')}")
print(f"   Dominio: {os.getenv('DOMAIN', 'easycom.local')}")
print(f"   Base DN: {os.getenv('BASE_DN', 'DC=easycom,DC=local')}")

print("\nIniciando servidor Flask...")
print("=" * 70)

# Importar después de cargar el .env
from server import app, socketio

if __name__ == "__main__":
    try:
        print("\n Servidor escuchando en:")
        print("    http://localhost:5000")
        print("    http://127.0.0.1:5000")
        print("\n   Para acceder desde otra máquina:")
        print("    http://<IP_LOCAL>:5000")
        print("\n   Presiona Ctrl+C para detener el servidor\n")
        
        socketio.run(app, host="0.0.0.0", port=5000, debug=False)
    except KeyboardInterrupt:
        print("\n\n Servidor detenido")
    except Exception as e:
        print(f"\n Error: {e}")
