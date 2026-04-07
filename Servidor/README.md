# 🔐 EasyCom - Chat Corporativo HTTPS en Windows Server

**Proyecto**: TFG ASIR - Chat seguro con autenticación LDAP  
**Tecnología**: Python Flask + SocketIO + Active Directory + HTTPS/IIS  
**Estado**: ✅ Listo para implementar en Windows Server  

---

## 🚀 Inicio Rápido (9 pasos)

### En tu máquina de desarrollo (5 minutos):

```bash
# 1. Generar certificados SSL/TLS
cd Servidor/
python generate_ssl_cert.py "easycom.local"

# Esto crea: cert.pem y key.pem
```

### En Windows Server (20-30 minutos):

```powershell
# 2. Copiar carpeta Servidor a:
# C:\inetpub\wwwroot\easycom\

# 3. Instalar dependencias
cd C:\inetpub\wwwroot\easycom
pip install -r requirements.txt

# 4. Ejecutar configuración automática (PowerShell como Admin)
.\setup_iis.ps1

# 5. Iniciar servidor Flask
python run_server.py

# 6. Acceder en navegador
# https://easycom.local
# (Aceptar advertencia de certificado autofirmado)
```

---

## 📂 Estructura del Proyecto

```
Servidor/
├── 📄 README.md (este archivo)
├── 📄 RESUMEN_EJECUTIVO.md ← DOCUMENTACIÓN COMPLETA
├── 🔧 Configuración
│   ├── .env (variables de entorno)
│   ├── requirements.txt (dependencias Python)
│   ├── web.config (IIS proxy reverso)
│   └── config_port_forwarding.ps1
├── 🐍 Código
│   ├── server.py (aplicación Flask principal)
│   ├── run_server.py (inicia el servidor)
│   └── generate_ssl_cert.py (genera certificados SSL)
├── 🖱️ Frontend
│   ├── templates/ (HTML: login, chat, admin)
│   └── Static/ (CSS, JavaScript)
├── 👥 Cliente
│   └── Cliente/cliente.py (cliente Python para testing)
├── 🛠️ Automatización
│   └── setup_iis.ps1 (configura IIS automáticamente)
└── 📊 Base de datos
    └── historial.db (SQLite - historial de mensajes)
```

---

## ✨ Características

- ✅ **HTTPS Seguro**: Certificados SSL/TLS con proxy inverso IIS
- ✅ **Chat Tiempo Real**: WebSocket bidireccional con SocketIO
- ✅ **Autenticación LDAP**: Integración con Active Directory
- ✅ **Multi-usuario**: Múltiples usuarios conectados simultáneamente
- ✅ **Departamentos**: Canales por departamento (RR.HH., Ventas, IT, etc.)
- ✅ **Mensajes Privados**: DM entre usuarios
- ✅ **Admin Panel**: Estadísticas y monitoreo
- ✅ **Historial**: Base de datos persistente de mensajes

---

## 🔒 Seguridad Implementada

| Característica | Descripción |
|---|---|
| **HTTPS/TLS** | Todo el tráfico cifrado (puerto 443) |
| **Certificados Digitales** | Autofirmados (desarrollo), reales con Let's Encrypt (producción) |
| **Proxy Inverso** | IIS actúa como intermediario entre cliente y servidor |
| **WebSocket Seguro** | Chat usa WSS (WebSocket Secure) |
| **LDAP Authentication** | Usuarios verificados contra Active Directory |
| **CORS Controlado** | Solo orígenes permitidos |
| **Headers Seguridad** | HSTS, CSP, X-Frame-Options, etc. |
| **Bloqueo Archivos** | .py, .env, __pycache__ no accesibles públicamente |
| **Rate Limiting** | Protección contra ataques de fuerza bruta |

---

## 📝 Requisitos

### Windows Server:
- Windows Server 2016 o superior
- Acceso con permisos de Administrador
- IIS + Application Request Routing (ARR)
- Python 3.8+
- Active Directory (para LDAP)

### Desarrollo:
- Python 3.8+
- pip (gestor de paquetes)
- OpenSSL (para generar certificados)

---

## 📖 Documentación

**RESUMEN_EJECUTIVO.md** contiene:
- Explicación de TODOS los cambios realizados
- 9 pasos detallados para Windows Server
- Solución de problemas
- Arquitectura del sistema
- Conceptos ASIR aprendidos
- Preguntas esperadas en defensa TFG

👉 **Lee primero RESUMEN_EJECUTIVO.md para instrucciones completas**

---

## 🔧 Archivos Clave

| Archivo | Propósito |
|---------|-----------|
| **server.py** | Aplicación Flask principal (LDAP, SocketIO, BD) |
| **run_server.py** | Script para iniciar el servidor |
| **generate_ssl_cert.py** | Genera certificados autofirmados |
| **setup_iis.ps1** | Automatiza configuración de IIS |
| **web.config** | Configuración IIS (proxy reverso, seguridad) |
| **.env** | Variables de configuración (LDAP, secretos) |

---

## ⚡ Comandos Esenciales

```bash
# Generar certificados
python generate_ssl_cert.py "easycom.local"

# Instalar dependencias
pip install -r requirements.txt

# Iniciar servidor (modo HTTP para desarrollo)
python run_server.py

# Verificar que Flask corre en puerto 5000
netstat -ano | findstr :5000

# Probar HTTPS en Windows Server
curl https://easycom.local -k

# Ver logs
Get-Content C:\inetpub\logs\LogFiles\*
```

---

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────┐
│  Cliente (Navegador HTTPS)                   │
│  https://easycom.local:443                  │
└────────────────┬────────────────────────────┘
                 │ HTTPS + TLS Cifrado
                 ▼
┌─────────────────────────────────────────────┐
│  Windows Server - IIS (Proxy Reverso)        │
│  • Certificado SSL/TLS                       │
│  • URL Rewrite → localhost:5000              │
│  • WebSocket habilitado                      │
│  • Headers de seguridad                      │
└────────────────┬────────────────────────────┘
                 │ HTTP (interno, no expuesto)
                 ▼
┌─────────────────────────────────────────────┐
│  Servidor Python (localhost:5000)            │
│  • Flask (aplicación web)                    │
│  • SocketIO (chat en tiempo real)            │
│  • LDAP (autenticación Active Directory)     │
│  • SQLite (historial de mensajes)            │
└─────────────────────────────────────────────┘
```

---

## 🎓 Para tu Defensa TFG

**Demuestra funcionalidad**:
1. HTTPS activo (candado en navegador)
2. Login con usuario LDAP real
3. Chat en tiempo real
4. Múltiples usuarios simultáneos
5. Historial de mensajes

**Explica conceptos**:
- ¿Por qué HTTPS? → Seguridad, cifrado, privacidad
- ¿Cómo funciona el proxy reverso? → IIS reenvía a Flask
- ¿Qué es certificado SSL/TLS? → Identidad + cifrado digital
- ¿WebSocket? → Comunicación bidireccional (ideal para chat)
- ¿LDAP? → Integración con Active Directory corporativo

---

## 🚨 Solución Rápida

| Problema | Verificar |
|----------|-----------|
| No se conecta | Firewall: `New-NetFirewallRule -DisplayName "HTTPS" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 443` |
| Proxy error | Flask corre: `netstat -ano \| findstr :5000` |
| WebSocket no funciona | `web.config` debe tener `<webSocket enabled="true" />` |
| LDAP falla | Credenciales en `.env` correctas |
| Puerto 5000 ocupado | Cambiar PORT en `.env` |

---

## 📞 Más Información

- 📖 **RESUMEN_EJECUTIVO.md** ← LEE ESTO PRIMERO
- 🔍 **server.py** - Código principal con comentarios
- ⚙️ **web.config** - Configuración IIS documentada
- 🛠️ **setup_iis.ps1** - Script de automatización

---

## 🎯 Checklist Pre-Implementación

- [ ] Python 3.8+ instalado en Windows Server
- [ ] IIS instalado
- [ ] Application Request Routing (ARR) instalado
- [ ] Certificados generados (`cert.pem`, `key.pem`)
- [ ] Carpeta copiada a `C:\inetpub\wwwroot\easycom`
- [ ] Dependencias instaladas: `pip install -r requirements.txt`
- [ ] Script ejecutado: `.\setup_iis.ps1`
- [ ] Servidor Flask iniciado: `python run_server.py`
- [ ] Acceso a `https://easycom.local` ✅
- [ ] Login LDAP funciona ✅
- [ ] Chat en tiempo real funciona ✅

---

## 📄 Licencia

Proyecto educativo - TFG ASIR 2026

---

**¿Necesitas ayuda?** Lee **RESUMEN_EJECUTIVO.md** para guía completa paso a paso.

🚀 **¡Listo para implementar!**
