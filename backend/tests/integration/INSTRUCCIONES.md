# 🧪 Tests de Integración Frontend-Backend

## 📋 Resumen

Este conjunto de tests verifica que el frontend está **completamente alineado** con el backend:

1. ✅ **Alineación de Endpoints**: Todos los endpoints que el frontend usa existen en el backend
2. ✅ **Contratos de Datos**: Los endpoints devuelven el formato esperado por el frontend
3. ✅ **Tipos de Datos**: Los tipos coinciden (string, number, boolean, etc.)

## 🚀 Ejecución Rápida

### Opción 1: Script Automático (Recomendado)

**Windows (PowerShell):**
```powershell
cd backend
.\scripts\test_integration_frontend_backend.ps1
```

**Linux/Mac:**
```bash
cd backend
chmod +x scripts/test_integration_frontend_backend.sh
./scripts/test_integration_frontend_backend.sh
```

### Opción 2: Manual

```bash
# 1. Asegúrate de que el backend esté corriendo
#    (debe estar en http://localhost:8000)

# 2. Instala dependencias (si no están instaladas)
pip install pytest pytest-asyncio httpx

# 3. Ejecuta los tests
cd backend
pytest tests/integration/ -v

# 4. Genera el reporte de endpoints
pytest tests/integration/test_frontend_backend_alignment.py::test_generate_endpoint_report -v -s
```

## 📊 Qué Verifican los Tests

### Test 1: `test_frontend_backend_endpoint_alignment`

**Qué hace:**
- Escanea todos los archivos `.ts` y `.tsx` del frontend
- Extrae todas las llamadas `api.get()`, `api.post()`, etc.
- Escanea todos los archivos `api/*.py` del backend
- Extrae todos los decoradores `@router.get()`, `@router.post()`, etc.
- Compara y reporta endpoints faltantes

**Ejemplo de salida:**
```
✅ PASSED: Todos los endpoints del frontend existen en el backend
```

O si hay problemas:
```
❌ FAILED: Se encontraron 3 endpoints del frontend que no existen en el backend:
  POST /strategies/{id}/custom-action (from app/strategies/[id]/page.tsx)
  GET /markets/custom-list (from app/markets/page.tsx)
  ...
```

### Test 2: `test_api_contracts.py`

**Qué hace:**
- Hace requests reales a los endpoints del backend
- Verifica que devuelven JSON válido
- Valida que los campos esperados por el frontend están presentes
- Verifica que los tipos de datos son correctos

**Ejemplo de salida:**
```
✅ test_series_endpoint_contract PASSED
✅ test_markets_endpoint_contract PASSED
✅ test_events_endpoint_contract PASSED
❌ test_tags_endpoint_contract FAILED
   Contrato no cumplido:
   tags[0].tag_id: Tipo incorrecto. Esperado: string, Recibido: number
```

## 📄 Reporte de Endpoints

Después de ejecutar los tests, se genera un archivo JSON con el análisis completo:

**Ubicación:** `backend/tests/integration/endpoint_alignment_report.json`

**Contenido:**
```json
{
  "frontend_endpoints_count": 45,
  "backend_endpoints_count": 120,
  "missing_endpoints": [
    {
      "method": "POST",
      "path": "/strategies/{id}/custom-action",
      "path_template": "/strategies/{id}/custom-action",
      "file": "app/strategies/[id]/page.tsx"
    }
  ],
  "frontend_endpoints": [...],
  "backend_endpoints": [...]
}
```

## 🔧 Solución de Problemas

### Error: "No se puede conectar al backend"

**Solución:**
1. Asegúrate de que el backend esté corriendo:
   ```bash
   cd backend
   uvicorn app.main:app --reload
   ```

2. Verifica que esté en el puerto correcto:
   ```bash
   curl http://localhost:8000/health
   ```

### Error: "httpx no está instalado"

**Solución:**
```bash
pip install httpx
```

### Error: "Endpoint no existe"

**Solución:**
- Si el endpoint realmente no existe: Crearlo en el backend
- Si el endpoint existe pero con diferente path: Actualizar el frontend o el backend para que coincidan

### Error: "Contrato no cumplido"

**Solución:**
- Revisar el error específico (campo faltante, tipo incorrecto)
- Ajustar el backend para devolver el formato esperado
- O actualizar el frontend para aceptar el formato actual

## 📝 Endpoints Críticos Verificados

Los siguientes endpoints son verificados especialmente:

- ✅ `GET /series` - Lista de series
- ✅ `GET /markets` - Lista de markets
- ✅ `GET /markets/events/list` - Lista de events
- ✅ `GET /tags` - Lista de tags
- ✅ `GET /strategies` - Lista de estrategias
- ✅ `GET /strategies/{id}` - Detalles de estrategia
- ✅ `GET /strategies/{id}/intents` - Intents de estrategia
- ✅ `GET /strategies/{id}/metrics` - Métricas de estrategia
- ✅ `POST /strategies/{id}/activate` - Activar estrategia
- ✅ `POST /strategies/{id}/deactivate` - Desactivar estrategia
- ✅ `PATCH /markets/{id}/enable` - Activar/desactivar market

## 🎯 Próximos Pasos

1. **Ejecutar los tests** para identificar desalineaciones
2. **Revisar el reporte** `endpoint_alignment_report.json`
3. **Corregir endpoints faltantes** o actualizar el frontend
4. **Ajustar contratos** si los tipos no coinciden
5. **Re-ejecutar** hasta que todos los tests pasen

## 💡 Tips

- Ejecuta los tests **antes de cada deploy** para asegurar alineación
- Si agregas un nuevo endpoint en el backend, ejecuta los tests para verificar que el frontend lo puede usar
- Si cambias el formato de respuesta de un endpoint, ejecuta los tests para verificar compatibilidad

