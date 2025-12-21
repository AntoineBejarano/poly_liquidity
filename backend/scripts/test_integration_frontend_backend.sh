#!/bin/bash
# Script para ejecutar tests de integración Frontend-Backend

echo "🧪 Ejecutando tests de integración Frontend-Backend..."
echo ""

# Verificar que el backend está corriendo
echo "📡 Verificando conexión con el backend..."
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Backend está corriendo"
else
    echo "⚠️  Backend no responde en http://localhost:8000"
    echo "   Asegúrate de que el backend esté corriendo antes de ejecutar los tests"
    exit 1
fi

# Instalar dependencias si es necesario
echo ""
echo "📦 Verificando dependencias..."
pip install -q pytest pytest-asyncio httpx 2>/dev/null || {
    echo "❌ Error instalando dependencias"
    exit 1
}

# Ejecutar tests
echo ""
echo "🚀 Ejecutando tests..."
cd "$(dirname "$0")/.."
python -m pytest tests/integration/ -v --tb=short

# Generar reporte
echo ""
echo "📊 Generando reporte de endpoints..."
python -m pytest tests/integration/test_frontend_backend_alignment.py::test_generate_endpoint_report -v -s

echo ""
echo "✅ Tests completados"
echo "   Revisa tests/integration/endpoint_alignment_report.json para el reporte completo"

