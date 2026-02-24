# Script para configurar Port Forwarding en el router
# Esto permite que el móvil acceda desde Internet

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "CONFIGURAR PORT FORWARDING EN TU ROUTER" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

Write-Host "`n[INFO] Tu IP pública es: 37.10.132.52"
Write-Host "[INFO] Puerto del servidor: 5000"
Write-Host "[INFO] IP local del servidor: 192.168.1.1 o 10.0.2.15"

Write-Host "`nPasos para configurar en tu router:`n"
Write-Host "1. Abre: http://192.168.1.1 (o tu IP del router)"
Write-Host "2. Inicia sesión con admin/admin (o tus credenciales)"
Write-Host "3. Busca 'Port Forwarding' o 'Redirección de puertos'"
Write-Host "4. Crea una nueva regla:"
Write-Host "   - Protocolo: TCP"
Write-Host "   - Puerto externo: 5000"
Write-Host "   - IP interna: 192.168.1.1 (o 10.0.2.15)"
Write-Host "   - Puerto interno: 5000"
Write-Host "   - Guardar/Aplicar"

Write-Host "`n[✓] Una vez configurado, accede desde tu móvil:"
Write-Host "    http://37.10.132.52:5000"

Write-Host "`n" -ForegroundColor Green
Write-Host "⚠️  NOTA IMPORTANTE:" -ForegroundColor Yellow
Write-Host "Si tu router no tiene esa opción, descarga ngrok:"
Write-Host "  - Regístrate en https://ngrok.com (gratis)"
Write-Host "  - Obtén tu authtoken"
Write-Host "  - Ejecuta: ngrok authtoken TU_TOKEN"
Write-Host "  - Ejecuta: ngrok http 5000"
Write-Host "`n"
