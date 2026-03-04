#!/usr/bin/env python3
"""
Cliente básico para el sistema de chat.
Compatible con el servidor creado en el proyecto.
"""

import socket
import threading

def recibir_mensajes(sock):
    """Hilo para recibir mensajes del servidor."""
    while True:
        try:
            data = sock.recv(4096)
            if not data:
                print(" Conexión cerrada por el servidor.")
                break
            print(data.decode('utf-8'), end="")   # ya incluye \n
        except Exception:
            print(" Error recibiendo datos. Desconectado.")
            break

def main():
    print("=== CLIENTE DE CHAT EMPRESARIAL ===\n")

    # IP del servidor
    server_ip = input("IP del servidor: ").strip()
    username = input("Nombre de usuario: ").strip()

    # Crear socket TCP
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    print("\n Conectando al servidor...")
    try:
        sock.connect((server_ip, 5000))
    except Exception as e:
        print(f" Error al conectar: {e}")
        return

    print("🟢 Conectado. Esperando mensajes...\n")

    # Enviar username (primer mensaje obligatorio)
    sock.sendall((username + "\n").encode('utf-8'))

    # Hilo que recibe mensajes del servidor
    hilo_receptor = threading.Thread(target=recibir_mensajes, args=(sock,), daemon=True)
    hilo_receptor.start()

    # Bucle para enviar mensajes
    try:
        while True:
            msg = input()
            if msg.lower() in ("exit", "quit"):
                print(" Desconectando...")
                sock.close()
                break
            sock.sendall(msg.encode('utf-8'))
    except KeyboardInterrupt:
        print("\n Interrupción detectada, cerrando...")
        sock.close()

if __name__ == "__main__":
    main()
