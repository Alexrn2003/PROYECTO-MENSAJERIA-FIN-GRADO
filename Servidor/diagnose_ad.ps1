# Script de diagnóstico de Active Directory
# Este script requiere acceso al módulo ActiveDirectory de PowerShell
# Ejecuta como administrador en tu máquina conectada al dominio

# Verificar si el módulo AD está disponible
try {
    Import-Module ActiveDirectory -ErrorAction Stop
    Write-Host "Módulo ActiveDirectory cargado correctamente`n" -ForegroundColor Green
} catch {
    Write-Host "ERROR: No se pudo cargar el módulo ActiveDirectory." -ForegroundColor Red
    Write-Host "Asegúrate de ejecutar esto como administrador en una máquina conectada al dominio." -ForegroundColor Yellow
    exit 1
}

# Obtener el dominio actual
$domain = (Get-ADDomain -ErrorAction SilentlyContinue).DNSRoot
$baseDN = (Get-ADDomain -ErrorAction SilentlyContinue).DistinguishedName

Write-Host "Dominio detectado: $domain" -ForegroundColor Cyan
Write-Host "Base DN: $baseDN`n" -ForegroundColor Cyan

# Listar TODOS los usuarios del dominio con atributos clave
Write-Host "====== LISTADO DE USUARIOS DEL DOMINIO ======`n" -ForegroundColor Yellow

$users = Get-ADUser -Filter * -Properties sAMAccountName, UserPrincipalName, DisplayName, Mail, Enabled, LockedOut, PasswordLastSet, PasswordExpired, PasswordNotRequired, Description, DistinguishedName

$report = @()
foreach ($user in $users) {
    $report += [PSCustomObject]@{
        "sAMAccountName" = $user.sAMAccountName
        "UPN" = $user.UserPrincipalName
        "DisplayName" = $user.DisplayName
        "Email" = $user.Mail
        "Enabled" = $user.Enabled
        "LockedOut" = $user.LockedOut
        "PasswordLastSet" = $user.PasswordLastSet
        "PasswordExpired" = $user.PasswordExpired
        "PasswordNotRequired" = $user.PasswordNotRequired
        "DistinguishedName" = $user.DistinguishedName
        "Description" = $user.Description
    }
}

# Mostrar tabla
$report | Format-Table -AutoSize

# Exportar a CSV para análisis detallado
$csvPath = "C:\EasyCom-Mensajería\Servidor\ad_users_report.csv"
$report | Export-Csv -Path $csvPath -NoTypeInformation -Encoding UTF8
Write-Host "`nReporte exportado a: $csvPath" -ForegroundColor Green

# Análisis de problemas comunes
Write-Host "`n====== ANÁLISIS DE PROBLEMAS ======`n" -ForegroundColor Yellow

$disabledUsers = $report | Where-Object { $_.Enabled -eq $false }
if ($disabledUsers) {
    Write-Host "⚠ Usuarios DESHABILITADOS:" -ForegroundColor Red
    $disabledUsers | ForEach-Object { Write-Host "  - $($_.sAMAccountName)" }
}

$lockedUsers = $report | Where-Object { $_.LockedOut -eq $true }
if ($lockedUsers) {
    Write-Host "`n⚠ Usuarios BLOQUEADOS:" -ForegroundColor Red
    $lockedUsers | ForEach-Object { Write-Host "  - $($_.sAMAccountName)" }
}

$expiredPwd = $report | Where-Object { $_.PasswordExpired -eq $true }
if ($expiredPwd) {
    Write-Host "`n⚠ Contraseñas EXPIRADAS:" -ForegroundColor Red
    $expiredPwd | ForEach-Object { Write-Host "  - $($_.sAMAccountName)" }
}

$noUPN = $report | Where-Object { -not $_.UPN }
if ($noUPN) {
    Write-Host "`n⚠ Usuarios SIN UPN configurado:" -ForegroundColor Yellow
    $noUPN | ForEach-Object { Write-Host "  - $($_.sAMAccountName) (DN: $($_.DistinguishedName))" }
}

$pwdNotSet = $report | Where-Object { -not $_.PasswordLastSet }
if ($pwdNotSet) {
    Write-Host "`n⚠ Usuarios SIN PasswordLastSet (nunca han establecido contraseña):" -ForegroundColor Yellow
    $pwdNotSet | ForEach-Object { Write-Host "  - $($_.sAMAccountName)" }
}

# Información sobre el dominio
Write-Host "`n====== INFORMACIÓN DEL DOMINIO ======`n" -ForegroundColor Yellow
$domainInfo = Get-ADDomain
Write-Host "Nombre de dominio: $($domainInfo.Name)" -ForegroundColor Cyan
Write-Host "FQDN: $($domainInfo.DNSRoot)" -ForegroundColor Cyan
Write-Host "Nivel funcional: $($domainInfo.DomainMode)" -ForegroundColor Cyan
Write-Host "Controladores de dominio:"
Get-ADDomainController -Filter * | ForEach-Object {
    Write-Host "  - $($_.Name) ($($_.OperatingSystem))" -ForegroundColor Cyan
}

Write-Host "`n====== FIN DEL DIAGNÓSTICO ======`n" -ForegroundColor Green
Write-Host "Para más detalles sobre un usuario específico, ejecuta:" -ForegroundColor Cyan
Write-Host '  Get-ADUser "nombreUsuario" -Properties *' -ForegroundColor Gray
