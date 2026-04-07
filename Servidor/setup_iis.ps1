# Script PowerShell para configurar IIS con proxy inverso para EasyCom
# Ejecutar como Administrador en Windows Server

# Ver al final la sección de SETUP MANUAL si tienes dudas

param(
    [string]$SiteName = "EasyCom",
    [string]$HostName = "easycom.local",
    [int]$HTTPPort = 80,
    [int]$HTTPSPort = 443,
    [int]$BackendPort = 5000,
    [string]$BackendURL = "http://localhost:5000"
)

# Colores para PowerShell
function Write-Title { Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan; Write-Host $args -ForegroundColor Cyan; Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan }
function Write-Success { Write-Host "✓ $args" -ForegroundColor Green }
function Write-Error { Write-Host "✗ $args" -ForegroundColor Red }
function Write-Warning { Write-Host "⚠ $args" -ForegroundColor Yellow }
function Write-Info { Write-Host "ℹ $args" -ForegroundColor Blue }

# Verificar si es Administrador
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")
if (-not $isAdmin) {
    Write-Error "Este script debe ejecutarse como Administrador"
    Write-Info "Abre PowerShell como Administrador y vuelve a intentar"
    exit 1
}

Write-Title "CONFIGURAR IIS PARA EASYCOM CON HTTPS"
Write-Info "Sitio: $SiteName"
Write-Info "Host: $HostName"
Write-Info "Backend: $BackendURL"
Write-Info ""

# Paso 1: Verificar IIS instalado
Write-Title "PASO 1: Verificar IIS"
if (Get-WindowsFeature -Name "Web-Server" | Where-Object Installed) {
    Write-Success "IIS está instalado"
} else {
    Write-Error "IIS no está instalado"
    Write-Info "Instálalo desde Server Manager → Add Roles and Features"
    exit 1
}

# Paso 2: Verificar ARR instalado
Write-Title "PASO 2: Verificar Application Request Routing (ARR)"
$arrModule = Get-Module -Name WebAdministration -ListAvailable
if ($arrModule) {
    Write-Success "Módulo WebAdministration disponible"
} else {
    Write-Error "Se requiere Application Request Routing"
    Write-Info "Descargalo de: https://www.iis.net/downloads/microsoft/application-request-routing"
    Write-Info "Instálalo e importe el módulo"
    exit 1
}

try {
    Import-Module WebAdministration -ErrorAction Stop
    Write-Success "Módulo WebAdministration cargado"
} catch {
    Write-Error "No se pudo cargar WebAdministration: $_"
    exit 1
}

# Paso 3: Crear Application Pool
Write-Title "PASO 3: Crear Application Pool"
$poolName = "$SiteName-Pool"
$poolPath = "IIS:\AppPools\$poolName"

if (Test-Path $poolPath) {
    Write-Warning "Application Pool ya existe: $poolName"
} else {
    try {
        New-Item $poolPath -Force | Out-Null
        
        $pool = Get-Item $poolPath
        $pool.processModel.identityType = "ApplicationPoolIdentity"
        $pool | Set-ItemProperty -Name "autoStart" -Value $true
        
        $pool.Update()
        Write-Success "Application Pool creado: $poolName"
    } catch {
        Write-Error "Error al crear Application Pool: $_"
        exit 1
    }
}

# Paso 4: Crear directorio raíz del sitio
Write-Title "PASO 4: Crear directorio raíz del sitio"
$siteRoot = "C:\inetpub\wwwroot\$($SiteName.ToLower())"

if (-not (Test-Path $siteRoot)) {
    try {
        New-Item -Path $siteRoot -ItemType Directory -Force | Out-Null
        Write-Success "Directorio creado: $siteRoot"
    } catch {
        Write-Error "Error al crear directorio: $_"
        exit 1
    }
} else {
    Write-Warning "Directorio ya existe: $siteRoot"
}

# Paso 5: Crear sitio web
Write-Title "PASO 5: Crear sitio web en IIS"
$sitePath = "IIS:\Sites\$SiteName"

if (Test-Path $sitePath) {
    Write-Warning "Sitio web ya existe: $SiteName"
    Write-Info "Usando configuración existente"
} else {
    try {
        New-WebSite -Name $SiteName -Port $HTTPPort -Protocol http -PhysicalPath $siteRoot -ApplicationPool $poolName | Out-Null
        Write-Success "Sitio web creado: $SiteName (puerto $HTTPPort)"
    } catch {
        Write-Error "Error al crear sitio web: $_"
        exit 1
    }
}

# Paso 6: Configurar host binding
Write-Title "PASO 6: Configurar Host Binding"

$site = Get-WebSite -Name $SiteName
if ($site) {
    # Verificar si existe binding HTTP
    $httpBinding = $site.Bindings.Collection | Where-Object { $_.protocol -eq "http" }
    
    if ($httpBinding) {
        Write-Warning "Host binding HTTP ya existe"
    } else {
        try {
            New-WebBinding -Name $SiteName -Protocol http -Port $HTTPPort -HostHeader $HostName
            Write-Success "Host binding configurado: http://$HostName"
        } catch {
            Write-Error "Error al configurar binding: $_"
        }
    }
} else {
    Write-Error "No se pudo encontrar el sitio: $SiteName"
    exit 1
}

# Paso 7: Crear/usar certificado autofirmado
Write-Title "PASO 7: Configurar Certificado SSL/TLS"

$existingCert = Get-ChildItem Cert:\LocalMachine\My | Where-Object { $_.Subject -like "*$HostName*" }

if ($existingCert) {
    Write-Warning "Certificado ya existe: $($existingCert.Thumbprint)"
    $certThumbprint = $existingCert.Thumbprint
} else {
    Write-Warning "Creando certificado autofirmado..."
    Write-Info "Este es solo para desarrollo/testing"
    
    try {
        $cert = New-SelfSignedCertificate -CertStoreLocation "cert:\LocalMachine\My" `
            -DnsName $HostName, "localhost", "127.0.0.1" `
            -FriendlyName "EasyCom Application" `
            -NotAfter (Get-Date).AddYears(2) `
            -KeySpec KeyExchange -ErrorAction Stop
        
        $certThumbprint = $cert.Thumbprint
        Write-Success "Certificado autofirmado creado: $certThumbprint"
    } catch {
        Write-Error "Error al crear certificado: $_"
        Write-Info "Intenta manualmente en IIS Manager → Server Certificates"
        exit 1
    }
}

# Paso 8: Crear binding HTTPS
Write-Title "PASO 8: Crear Binding HTTPS"

$httpsBinding = $site.Bindings.Collection | Where-Object { $_.protocol -eq "https" }

if ($httpsBinding) {
    Write-Warning "Binding HTTPS ya existe"
} else {
    try {
        New-WebBinding -Name $SiteName -Protocol https -Port $HTTPSPort -HostHeader $HostName -SslFlags "Sni"
        
        $binding = Get-WebBinding -Name $SiteName -Protocol https
        $binding.AddSslCertificate($certThumbprint, "my")
        
        Write-Success "Binding HTTPS creado: https://$HostName"
    } catch {
        Write-Error "Error al crear binding HTTPS: $_"
        Write-Info "Intenta manualmente en IIS Manager"
    }
}

# Paso 9: Habilitar proxy inverso
Write-Title "PASO 9: Habilitar Proxy Inverso (Application Request Routing)"

try {
    # Habilitar ARR en el servidor
    $iisConfig = Get-IISConfigSection -CommitPath "MACHINE/WEBROOT/APPHOST" -SectionPath "system.webServer/proxy"
    
    if ($iisConfig) {
        Set-IISConfigAttributeValue -ConfigSection $iisConfig -AttributeName "enabled" -AttributeValue $true
        Write-Success "Proxy Reverso habilitado en servidor"
    }
} catch {
    Write-Warning "No se pudo habilitar ARR automáticamente: $_"
    Write-Info "Habilítalo manualmente:"
    Write-Info "  IIS Manager → Tu servidor → Application Request Routing Cache"
    Write-Info "  → Enable proxy"
}

# Paso 10: Crear archivo de configuración web.config para proxy
Write-Title "PASO 10: Crear configuración de Proxy Inverso (web.config)"

$webConfigPath = "$siteRoot\web.config"
$webConfig = @"
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <system.webServer>
        <!-- Reescritura de URLs (Proxy Inverso) -->
        <rewrite>
            <rules>
                <!-- Redireccionar HTTP a HTTPS -->
                <rule name="Force HTTPS" stopProcessing="true">
                    <match url="(.*)" />
                    <conditions>
                        <add input="{HTTPS}" pattern="^OFF$" />
                    </conditions>
                    <action type="Redirect" url="https://{HTTP_HOST}{REQUEST_URI}" redirectType="Permanent" />
                </rule>
                
                <!-- Proxy Inverso a servidor Flask -->
                <rule name="ProxyToFlask" stopProcessing="true">
                    <match url="(.*)" />
                    <conditions>
                        <add input="{REQUEST_FILENAME}" matchType="IsFile" negate="true" />
                        <add input="{REQUEST_FILENAME}" matchType="IsDirectory" negate="true" />
                    </conditions>
                    <action type="Rewrite" url="$BackendURL/{R:1}" appendQueryString="true" />
                </rule>
            </rules>
            
            <!-- Headers de proxy reverso -->
            <outboundRules>
                <!-- Preservar cabeceras de respuesta -->
            </outboundRules>
        </rewrite>
        
        <!-- Proxy-->
        <proxy enabled="true" />
        
        <!-- WebSocket -->
        <webSocket enabled="true" />
        
        <!-- Compresión -->
        <urlCompression doDynamicCompression="true" doStaticCompression="true" />
        
        <!-- Seguridad -->
        <security>
            <requestFiltering>
                <fileExtensions>
                    <add fileExtension=".py" allowed="false" />
                    <add fileExtension=".pyc" allowed="false" />
                </fileExtensions>
            </requestFiltering>
        </security>
    </system.webServer>
</configuration>
"@

try {
    $webConfig | Out-File -FilePath $webConfigPath -Encoding UTF8 -Force
    Write-Success "web.config creado: $webConfigPath"
} catch {
    Write-Error "Error al crear web.config: $_"
}

# Paso 11: Configurar permisos NTFS
Write-Title "PASO 11: Configurar Permisos NTFS"

try {
    $poolIdentity = "IIS AppPool\$poolName"
    $acl = Get-Acl $siteRoot
    $permission = New-Object System.Security.AccessControl.FileSystemAccessRule(
        $poolIdentity,
        "Modify",
        "ContainerInherit,ObjectInherit",
        "None",
        "Allow"
    )
    $acl.AddAccessRule($permission)
    Set-Acl -Path $siteRoot -AclObject $acl
    
    Write-Success "Permisos configurados para: $poolIdentity"
} catch {
    Write-Warning "No se pudo configurar permisos automáticamente: $_"
    Write-Info "Configüralos manualmente en el Explorador de Archivos"
}

# Paso 12: Iniciar sitio
Write-Title "PASO 12: Iniciar Sitio Web"

try {
    $site = Get-WebSite -Name $SiteName
    if ($site.State -eq "Stopped") {
        Start-WebSite -Name $SiteName
        Write-Success "Sitio web iniciado"
    } else {
        Write-Success "Sitio web ya está ejecutándose"
    }
} catch {
    Write-Error "Error al iniciar sitio: $_"
}

# Resumen final
Write-Title "✅ CONFIGURACIÓN COMPLETADA"
Write-Success "Sitio web: $SiteName"
Write-Success "URL HTTP: http://$HostName"
Write-Success "URL HTTPS: https://$HostName (con certificado autofirmado)"
Write-Success "Backend: $BackendURL"
Write-Success "Application Pool: $poolName"

Write-Info ""
Write-Info "PRÓXIMOS PASOS:"
Write-Info "1. Inicia el servidor Flask: python run_server.py"
Write-Info "2. Accede a: https://$HostName"
Write-Info "3. Acepta la advertencia del navegador (certificado autofirmado)"
Write-Info "4. Prueba el login con tus credenciales LDAP"

Write-Warning ""
Write-Warning "IMPORTANTE PARA PRODUCCIÓN:"
Write-Warning "• Este certificado es AUTOFIRMADO solo para desarrollo"
Write-Warning "• Para producción, obtén un certificado de:"
Write-Warning "  - Let's Encrypt (gratuito): https://letsencrypt.org"
Write-Warning "  - o de una CA como GoDaddy, Sectigo, etc."

Write-Info ""
Write-Info "Para más ayuda, consulta: CONFIGURAR_HTTPS_IIS.md"

# ============================================================================
# SETUP MANUAL "
# Si este script no funciona, sigue estos pasos manualmente:
# 
# 1. IIS Manager (inetmgr)
# 2. Add Website
#    - Name: EasyCom
#    - Path: C:\inetpub\wwwroot\easycom
#    - Application Pool: EasyCom-Pool (crear nuevo)
#    - Binding: http, puerto 80, host easycom.local
# 3. Añadir otro binding: https, puerto 443, easycom.local
# 4. Seleccionar certificado (crear autofirmado si hace falta)
# 5. URL Rewrite: Crear regla Reverse Proxy a http://localhost:5000
# 6. Guardar web.config con la configuración proxy
# ============================================================================
