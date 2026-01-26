# Script PowerShell para ejecutar tests de integración Frontend-Backend

Write-Host "🧪 Ejecutando tests de integración Frontend-Backend..." -ForegroundColor Cyan
Write-Host ""

# Verificar que el backend está corriendo
Write-Host "📡 Verificando conexión con el backend..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -Method GET -TimeoutSec 2 -ErrorAction SilentlyContinue
    Write-Host "✅ Backend está corriendo" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Backend no responde en http://localhost:8000" -ForegroundColor Yellow
    Write-Host "   Asegúrate de que el backend esté corriendo antes de ejecutar los tests" -ForegroundColor Yellow
    exit 1
}

# Instalar dependencias si es necesario
Write-Host ""
Write-Host "📦 Verificando dependencias..." -ForegroundColor Yellow
try {
    pip install -q pytest pytest-asyncio httpx 2>$null
    Write-Host "✅ Dependencias verificadas" -ForegroundColor Green
} catch {
    Write-Host "❌ Error instalando dependencias" -ForegroundColor Red
    exit 1
}

# Ejecutar tests
Write-Host ""
Write-Host "🚀 Ejecutando tests..." -ForegroundColor Cyan
Set-Location (Split-Path $PSScriptRoot)
python -m pytest tests/integration/ -v --tb=short

# Generar reporte
Write-Host ""
Write-Host "📊 Generando reporte de endpoints..." -ForegroundColor Cyan
python -m pytest tests/integration/test_frontend_backend_alignment.py::test_generate_endpoint_report -v -s

Write-Host ""
Write-Host "✅ Tests completados" -ForegroundColor Green
Write-Host "   Revisa tests/integration/endpoint_alignment_report.json para el reporte completo" -ForegroundColor Gray

