# Chat Corporativo - LDAP

## Inicio Rápido

### Instalación
```powershell
cd C:\EasyCom-Mensajería\Servidor
pip install -r requisitos.txt
python run_server.py
```

El servidor se iniciará en `http://localhost:5000`

---

## Credenciales de Prueba

| Usuario | Contraseña |
|---------|-----------|
| administrador | Naniyalex_2003 |
| ClienteMiguel | TempNewPwd123!ABC |
| Alejandro | TempNewPwd456!DEF |
| ejemploS | TempNewPwd789!GHI |
| ClienteGenerico | ClienteGenerico@2025Secure |

---

## Acceso desde PC

**URL Local:**
```
http://localhost:5000
```

---

## Acceso desde Móvil (Misma Red)

Abre en el navegador de tu móvil:

**Opción 1:**
```
http://192.168.1.1:5000
```

**Opción 2:**
```
http://10.0.2.15:5000
```

---

## Acceso desde Móvil (Internet)

Para acceder desde Internet (IP externa 37.10.132.52):

Ejecuta el script de configuración:
```powershell
powershell -ExecutionPolicy Bypass -File config_port_forwarding.ps1
```

Este te guiará para configurar port forwarding en tu router.

---

## Estructura de Archivos

```
Servidor/
├── server.py              # Servidor Flask + Socket.IO
├── run_server.py          # Script de inicio
├── .env                   # Variables de configuración
├── requisitos.txt         # Dependencias Python
├── config_port_forwarding.ps1  # Guía de conexión móvil
├── server.log            # Log de eventos
├── server.err            # Log de errores
├── Cliente/              # Cliente Python
├── Static/               # chat.js
└── templates/            # login.html, chat.html
```

---

## Logs

- **server.log**: Eventos de autenticación y conexiones
- **server.err**: Errores y excepciones

---

**Status**: ✅ Funcional - Todos los usuarios pueden iniciar sesión
