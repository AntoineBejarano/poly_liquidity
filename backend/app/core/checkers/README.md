# Sistema de Checkers

El sistema de checkers permite detectar la finalización de eventos externos de forma dinámica y configurable.

## Arquitectura

### Componentes principales

1. **BaseChecker**: Clase abstracta base que todos los checkers deben implementar
2. **CheckerRegistry**: Registro global que mapea `implementation_key` a clases de checkers
3. **CheckerResult**: Modelo de resultado que retorna cada checker
4. **SecretService**: Servicio que proporciona credenciales a los checkers en tiempo de ejecución

### Flujo de ejecución

1. El `EventEngine` carga los checkers activos para una categoría desde la DB
2. Para cada checker:
   - Carga credenciales dinámicamente desde `SecretService` (si `secret_name` está configurado)
   - Instancia el checker usando el `implementation_key`
   - Ejecuta `check()` con el `external_event_id` y las credenciales
3. Agrega los resultados usando reglas de quórum
4. Actualiza el estado del evento en memoria y DB

## Cómo agregar un nuevo checker

### 1. Crear la implementación del checker

Crea un nuevo archivo en `backend/app/core/checkers/implementations/`:

```python
"""
Mi nuevo checker - descripción de qué detecta.
"""
import httpx
from app.core.checkers.base import BaseChecker, CheckerResult
from typing import Optional, Dict
from datetime import datetime


class MiNuevoChecker(BaseChecker):
    """
    Descripción del checker.
    
    Expected external_event_id format: "formato:ejemplo:123"
    Expected credentials: {"api_key": "...", "otro_param": "..."}
    """
    
    async def check(
        self,
        external_event_id: str,
        credentials: Optional[Dict[str, str]] = None
    ) -> CheckerResult:
        """
        Verifica si el evento está finalizado.
        
        Args:
            external_event_id: Identificador del evento externo
            credentials: Dict con credenciales (API keys, tokens, etc.)
        
        Returns:
            CheckerResult con state, confidence, etc.
        """
        if not credentials or "api_key" not in credentials:
            return CheckerResult(
                state="LIVE",
                confidence=0.1,
                finished_at=None,
                raw_payload={"error": "No credentials provided"},
                source="mi_nuevo_checker"
            )
        
        api_key = credentials.get("api_key")
        
        try:
            # Tu lógica aquí
            # 1. Parsear external_event_id
            # 2. Hacer llamada a API externa
            # 3. Determinar si el evento está finalizado
            # 4. Retornar CheckerResult
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                # Ejemplo de llamada API
                # response = await client.get(
                #     "https://api.example.com/events/123",
                #     headers={"Authorization": f"Bearer {api_key}"}
                # )
                # data = response.json()
                
                # Si el evento está finalizado:
                if False:  # Reemplazar con lógica real
                    return CheckerResult(
                        state="FINISHED",
                        confidence=0.95,
                        finished_at=datetime.utcnow(),  # O desde la API
                        raw_payload={"data": "..."},
                        source="mi_nuevo_checker"
                    )
                
                # Si no está finalizado:
                return CheckerResult(
                    state="LIVE",
                    confidence=0.5,
                    finished_at=None,
                    raw_payload={"data": "..."},
                    source="mi_nuevo_checker"
                )
        
        except httpx.TimeoutException:
            return CheckerResult(
                state="LIVE",
                confidence=0.1,
                finished_at=None,
                raw_payload={"error": "Timeout"},
                source="mi_nuevo_checker"
            )
        except Exception as e:
            return CheckerResult(
                state="LIVE",
                confidence=0.1,
                finished_at=None,
                raw_payload={"error": str(e)},
                source="mi_nuevo_checker"
            )
```

### 2. Registrar el checker

Edita `backend/app/core/checkers/implementations/__init__.py`:

```python
from .mi_nuevo_checker import MiNuevoChecker

# Auto-register
checker_registry.register("mi_nuevo_checker", MiNuevoChecker)
```

### 3. Crear entrada en la base de datos

Usa el frontend o la API para crear un `EventChecker`:

```bash
POST /checkers
{
  "implementation_key": "mi_nuevo_checker",
  "category": "categoria_relevante",
  "name": "Mi Nuevo Checker",
  "description": "Descripción del checker"
}
```

### 4. Configurar credenciales (opcional)

Si el checker requiere credenciales:

```bash
POST /checkers/secrets
{
  "name": "api_key_mi_checker",
  "value": "tu_api_key_aqui",
  "description": "API key para Mi Nuevo Checker"
}

POST /checkers/{checker_id}/configs
{
  "secret_name": "api_key_mi_checker",
  "weight": 1.0,
  "timeout_seconds": 5.0,
  "enabled": true
}
```

## Checkers incluidos

### MockChecker
- **implementation_key**: `mock_checker`
- **Propósito**: Testing, siempre retorna LIVE
- **Credenciales**: No requiere

### SportsChecker
- **implementation_key**: `sports_checker`
- **Propósito**: Detectar finalización de eventos deportivos
- **external_event_id format**: `sport:league:event_id` o `event_id`
- **Credenciales**: `{"api_key": "...", "api_url": "..."}` (opcional)
- **Estado**: Placeholder - necesita integración real con API deportiva

### CryptoChecker
- **implementation_key**: `crypto_checker`
- **Propósito**: Detectar eventos relacionados con criptomonedas
- **external_event_id format**: `crypto:symbol:target_price` o `crypto:symbol`
- **Credenciales**: `{"api_key": "..."}`
- **Estado**: Placeholder - necesita integración real con API de crypto

## Mejores prácticas

1. **Manejo de errores**: Siempre retorna `LIVE` con baja confianza en caso de error
2. **Timeouts**: Usa timeouts cortos (5 segundos o menos) para no bloquear el event loop
3. **Confidence**: 
   - 0.9-1.0: Muy seguro de que el evento está finalizado
   - 0.7-0.9: Bastante seguro
   - 0.5-0.7: Incierto
   - <0.5: Baja confianza, probablemente LIVE
4. **Raw payload**: Incluye datos útiles para auditoría y debugging
5. **Source**: Siempre incluye el nombre del checker en `source`

## Testing

Para probar un checker:

```python
from app.core.checkers.implementations.mi_nuevo_checker import MiNuevoChecker

checker = MiNuevoChecker()
result = await checker.check(
    external_event_id="test:123",
    credentials={"api_key": "test_key"}
)
print(result)
```

