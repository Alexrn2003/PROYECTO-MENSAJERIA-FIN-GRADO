#!/usr/bin/env powershell
# Script simplificado para configurar IIS con proxy inverso a Flask

Write-Host "`n=== CONFIGURAR IIS PARA EASYCOM ===" -ForegroundColor Cyan
Write-Host "Sitio: EasyCom"
Write-Host "Backend: http://localhost:8080"
Write-Host "Dominio: easycom.local"
Write-Host ""

# Verificar admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")
if (-not $isAdmin) {
    Write-Host "ERROR: Este script debe ejecutarse como Administrador" -ForegroundColor Red
    exit 1
}

# Variables
$SiteName = "EasyCom"
$HostName = "easycom.local"
$HTTPPort = 80
$HTTPSPort = 443
$PhysicalPath = "C:\inetpub\wwwroot\easycom"
$PoolName = "EasyCom-Pool"
$BackendURL = "http://localhost:8080"

try {
    Import-Module WebAdministration -ErrorAction Stop
    Write-Host "[OK] WebAdministration cargado" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] No se pudo cargar WebAdministration: $_" -ForegroundColor Red
    exit 1
}

# 1. Crear directorio
Write-Host "`n[1] Crear directorio raiz..." -ForegroundColor Yellow
if (-not (Test-Path $PhysicalPath)) {
    New-Item -Path $PhysicalPath -ItemType Directory -Force | Out-Null
    Write-Host "    OK: $PhysicalPath" -ForegroundColor Green
} else {
    Write-Host "    YA EXISTE: $PhysicalPath" -ForegroundColor Gray
}

# 2. Crear Application Pool
Write-Host "`n[2] Crear Application Pool..." -ForegroundColor Yellow
if (-not (Test-Path "IIS:\AppPools\$PoolName")) {
    New-WebAppPool -Name $PoolName | Out-Null
    Write-Host "    OK: $PoolName creado" -ForegroundColor Green
} else {
    Write-Host "    YA EXISTE: $PoolName" -ForegroundColor Gray
}

# 3. Crear sitio web
Write-Host "`n[3] Crear sitio web..." -ForegroundColor Yellow
if (-not (Test-Path "IIS:\Sites\$SiteName")) {
    New-WebSite -Name $SiteName -Port $HTTPPort -PhysicalPath $PhysicalPath -ApplicationPool $PoolName | Out-Null
    Write-Host "    OK: $SiteName creado" -ForegroundColor Green
} else {
    Write-Host "    YA EXISTE: $SiteName" -ForegroundColor Gray
}

# 4. Agregar host binding HTTP
Write-Host "`n[4] Configurar Host Binding HTTP..." -ForegroundColor Yellow
$site = Get-WebSite -Name $SiteName
$httpBinding = $site.Bindings.Collection | Where-Object { $_.protocol -eq "http" -and $_.bindingInformation -like "*$HostName*" }

if (-not $httpBinding) {
    New-WebBinding -Name $SiteName -Protocol http -Port $HTTPPort -HostHeader $HostName | Out-Null
    Write-Host "    OK: http://$HostName:$HTTPPort" -ForegroundColor Green
} else {
    Write-Host "    YA EXISTE: http://$HostName:$HTTPPort" -ForegroundColor Gray
}

# 5. Crear certificado autofirmado
Write-Host "`n[5] Crear certificado SSL/TLS..." -ForegroundColor Yellow
$cert = Get-ChildItem Cert:\LocalMachine\My | Where-Object { $_.Subject -like "*$HostName*" } | Select-Object -First 1

if (-not $cert) {
    try {
        $cert = New-SelfSignedCertificate -CertStoreLocation "cert:\LocalMachine\My" `
            -DnsName $HostName, "localhost", "127.0.0.1" `
            -FriendlyName "EasyCom SSL Certificate" `
            -NotAfter (Get-Date).AddYears(2)
        Write-Host "    OK: Certificado creado - Thumbprint: $($cert.Thumbprint)" -ForegroundColor Green
    } catch {
        Write-Host "    ERROR: No se pudo crear certificado: $_" -ForegroundColor Red
    }
} else {
    Write-Host "    EXISTE: Thumbprint $($cert.Thumbprint)" -ForegroundColor Gray
}

# 6. Agregar host binding HTTPS
Write-Host "`n[6] Configurar Host Binding HTTPS..." -ForegroundColor Yellow
$httpsBinding = $site.Bindings.Collection | Where-Object { $_.protocol -eq "https" -and $_.bindingInformation -like "*$HostName*" }

if (-not $httpsBinding) {
    try {
        New-WebBinding -Name $SiteName -Protocol https -Port $HTTPSPort -HostHeader $HostName -SslFlags "Sni" | Out-Null
        $binding = Get-WebBinding -Name $SiteName -Protocol https | Select-Object -First 1
        $binding.AddSslCertificate($cert.Thumbprint, "my")
        Write-Host "    OK: https://$HostName:$HTTPSPort" -ForegroundColor Green
    } catch {
        Write-Host "    ERROR: $_" -ForegroundColor Red
    }
} else {
    Write-Host "    YA EXISTE: https://$HostName:$HTTPSPort" -ForegroundColor Gray
}

# 7. Crear web.config con proxy reverso
Write-Host "`n[7] Crear web.config con proxy reverso..." -ForegroundColor Yellow
$webConfigPath = "$PhysicalPath\web.config"

$webConfig = @"
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <system.webServer>
        <rewrite>
            <rules>
                <rule name="Force HTTPS" stopProcessing="true">
                    <match url="(.*)" />
                    <conditions>
                        <add input="{HTTPS}" pattern="^OFF`$" />
                    </conditions>
                    <action type="Redirect" url="https://{HTTP_HOST}{REQUEST_URI}" redirectType="Permanent" />
                </rule>
                <rule name="ProxyToFlask" stopProcessing="true">
                    <match url="(.*)" />
                    <conditions>
                        <add input="{REQUEST_FILENAME}" matchType="IsFile" negate="true" />
                        <add input="{REQUEST_FILENAME}" matchType="IsDirectory" negate="true" />
                    </conditions>
                    <action type="Rewrite" url="$BackendURL/{R:1}" appendQueryString="true" />
                </rule>
            </rules>
        </rewrite>
        <proxy enabled="true" />
        <webSocket enabled="true" />
        <urlCompression doDynamicCompression="true" doStaticCompression="true" />
    </system.webServer>
</configuration>
"@

try {
    $webConfig | Out-File -FilePath $webConfigPath -Encoding UTF8 -Force
    Write-Host "    OK: $webConfigPath" -ForegroundColor Green
} catch {
    Write-Host "    ERROR: $_" -ForegroundColor Red
}

# 8. Configurar permisos NTFS
Write-Host "`n[8] Configurar permisos NTFS..." -ForegroundColor Yellow
try {
    $poolIdentity = "IIS AppPool\$PoolName"
    $acl = Get-Acl $PhysicalPath
    $permission = New-Object System.Security.AccessControl.FileSystemAccessRule(
        $poolIdentity, "Modify", "ContainerInherit,ObjectInherit", "None", "Allow"
    )
    $acl.AddAccessRule($permission)
    Set-Acl -Path $PhysicalPath -AclObject $acl
    Write-Host "    OK: Permisos para $poolIdentity" -ForegroundColor Green
} catch {
    Write-Host "    ADVERTENCIA: $_" -ForegroundColor Yellow
}

# 9. Iniciar sitio
Write-Host "`n[9] Iniciar sitio web..." -ForegroundColor Yellow
try {
    $site = Get-WebSite -Name $SiteName
    if ($site.State -eq "Stopped") {
        Start-WebSite -Name $SiteName
    }
    Write-Host "    OK: Sitio ejecutandose" -ForegroundColor Green
} catch {
    Write-Host "    ERROR: $_" -ForegroundColor Red
}

# Resumen
Write-Host "`n" -ForegroundColor White
Write-Host "╔════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  CONFIGURACION COMPLETADA                  ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Write-Host "Acceso HTTP:  http://easycom.local" -ForegroundColor Green
Write-Host "Acceso HTTPS: https://easycom.local" -ForegroundColor Green
Write-Host "Backend:      $BackendURL" -ForegroundColor Green
Write-Host ""
Write-Host "PROXIMOS PASOS:" -ForegroundColor Yellow
Write-Host "1. Inicia la aplicacion Flask:"
Write-Host "   python run_server.py" -ForegroundColor White
Write-Host ""
Write-Host "2. Abre el navegador:"
Write-Host "   https://easycom.local" -ForegroundColor White
Write-Host ""
Write-Host "3. Acepta el certificado autofirmado" -ForegroundColor Yellow
Write-Host ""
