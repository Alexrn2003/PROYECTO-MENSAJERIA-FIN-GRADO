# Chat Corporativo - LDAP

## Inicio Rápido

### Instalación
```powershell
cd C:\EasyCom-Mensajería\Servidor
pip install -r requisitos.txt
```

### Ejecutar Servidor

**Opción 1: Solo localhost (recomendado)**
```powershell
python run_server.py
```
- ✅ No requiere permisos especiales
- ✅ Acceso desde: `http://localhost:8080`
- ❌ No accesible desde otras máquinas

**Opción 2: Acceso desde red (requiere administrador)**
```powershell
# Clic derecho en PowerShell → "Ejecutar como administrador"
python run_server_network.py
```
- ✅ Accesible desde otras máquinas en la red
- ✅ Acceso desde móviles en misma WiFi
- ❌ Requiere permisos de administrador

### Solución de Problemas

Si ves el error "Intento de acceso a un socket no permitido":
1. **Usa `run_server.py`** (solo localhost) - no requiere admin
2. **O ejecuta como administrador** y usa `run_server_network.py`
3. **O cambia el puerto** en `.env`: `PORT=8080`

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
http://localhost:8080
```

---

## Acceso desde Móvil (Misma Red)

Abre en el navegador de tu móvil:

**Opción 1:**
```
http://192.168.1.1:8080
```

**Opción 2:**
```
http://10.0.2.15:8080
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
├── run_server.py          # Script de inicio (localhost)
├── run_server_network.py  # Script de inicio (red - requiere admin)
├── .env                   # Variables de configuración
├── requisitos.txt         # Dependencias Python
├── config_port_forwarding.ps1  # Guía de conexión móvil
├── server.log            # Log de eventos
├── server.err            # Log de errores
├── Cliente/              # Cliente Python
├── Static/               # chat.js, style.css
└── templates/            # login.html, chat.html
```

---

## Logs

- **server.log**: Eventos de autenticación y conexiones
- **server.err**: Errores y excepciones

---

**Status**: ✅ Funcional - Todos los usuarios pueden iniciar sesión
