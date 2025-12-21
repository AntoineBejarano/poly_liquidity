# Tests de Integración Frontend-Backend

Este directorio contiene tests de integración para verificar que el frontend está completamente alineado con el backend.

## Tests Disponibles

### 1. `test_frontend_backend_alignment.py`

Verifica que todos los endpoints que el frontend usa existen en el backend.

**Ejecutar:**
```bash
# Desde el directorio backend
pytest tests/integration/test_frontend_backend_alignment.py -v

# Generar reporte de endpoints
python -m pytest tests/integration/test_frontend_backend_alignment.py::test_generate_endpoint_report -v
```

**Qué verifica:**
- Extrae todos los endpoints que el frontend llama (de archivos `.ts`, `.tsx`)
- Extrae todos los endpoints definidos en el backend (de archivos `api/*.py`)
- Compara y reporta endpoints faltantes
- Genera un reporte JSON con todos los endpoints

### 2. `test_api_contracts.py`

Verifica que los endpoints devuelven el formato esperado por el frontend.

**Ejecutar:**
```bash
# Desde el directorio backend
pytest tests/integration/test_api_contracts.py -v
```

**Qué verifica:**
- Los endpoints devuelven JSON válido
- Los campos esperados por el frontend están presentes
- Los tipos de datos son correctos (string, number, boolean, array, object, null)

## Requisitos

1. **Backend corriendo**: El backend debe estar ejecutándose en `http://localhost:8000`
2. **Dependencias**: 
   ```bash
   pip install pytest pytest-asyncio httpx
   ```

## Ejecutar Todos los Tests

```bash
# Desde el directorio backend
pytest tests/integration/ -v
```

## Interpretar Resultados

### ✅ Test Pasa
- Todos los endpoints del frontend existen en el backend
- Los contratos de datos coinciden

### ❌ Test Falla
- **Endpoints faltantes**: El frontend llama a endpoints que no existen en el backend
  - **Solución**: Crear los endpoints faltantes o actualizar el frontend
- **Contratos no cumplidos**: Los endpoints devuelven datos en formato diferente
  - **Solución**: Ajustar el backend para devolver el formato esperado o actualizar el frontend

## Reporte de Endpoints

Después de ejecutar `test_generate_endpoint_report`, se genera un archivo:
- `tests/integration/endpoint_alignment_report.json`

Este archivo contiene:
- Lista completa de endpoints del frontend
- Lista completa de endpoints del backend
- Endpoints faltantes (frontend usa pero backend no tiene)

## Notas

- Los tests que requieren autenticación pueden fallar con 401/403, esto es esperado
- Algunos endpoints pueden requerir datos específicos (IDs, etc.) para funcionar correctamente
- Los tests de contratos validan solo los primeros 5 items de arrays para evitar tiempos largos

