#!/usr/bin/env python3

from dotenv import load_dotenv
load_dotenv()

from server import app, socketio

if __name__ == "__main__":
    print("========================================")
    print("   SERVIDOR EASYCOM INICIANDO")
    print("========================================")
    print("Accede desde: http://localhost:5000")
    print("========================================\n")

    socketio.run(
        app,
        host="0.0.0.0",
        port=5000,
        debug=True
    )