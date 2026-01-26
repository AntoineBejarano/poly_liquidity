# Parámetros Protegidos - Protección contra Errores Humanos

## Objetivo

No todos los parámetros deberían ser editables sin fricción. Algunos parámetros críticos deben estar protegidos para evitar errores humanos.

---

## Tipos de Protección

### 1. is_readonly = true

**Significado:** El parámetro NO puede ser modificado desde el frontend.

**Uso:** Para parámetros que solo deben cambiarse mediante migraciones o cambios de código controlados.

**Ejemplo:** Parámetros de infraestructura que requieren cambios arquitectónicos.

### 2. requires_confirmation = true

**Significado:** El parámetro requiere confirmación explícita antes de cambiar.

**Uso:** Para parámetros críticos que pueden afectar seguridad o comportamiento del sistema.

**Implementación:**
- Frontend debe mostrar diálogo de confirmación
- Usuario debe proporcionar `confirmation_token` (ej. escribir "CONFIRM" o similar)
- Backend valida el token antes de aplicar el cambio

---

## Parámetros que Deben Estar Protegidos

### 🔴 Críticos (requires_confirmation = true)

#### 1. `allow_zero_checker`
- **Razón:** Afecta seguridad - permite sistema sin checkers
- **Protección:** `requires_confirmation = true`
- **Frontend:** Mostrar advertencia: "Permitir sistema sin checkers puede resultar en decisiones no confiables"

#### 2. `execution_mode = LIVE`
- **Razón:** Cambio a LIVE activa trading real con dinero real
- **Protección:** `requires_confirmation = true`
- **Frontend:** 
  - Mostrar advertencia grande y clara
  - Requerir escribir "LIVE" o similar como confirmation_token
  - Mostrar resumen de configuración actual antes de confirmar

#### 3. `latency_fail_mode`
- **Razón:** Afecta comportamiento de seguridad del sistema
- **Protección:** `requires_confirmation = true`
- **Frontend:** Explicar impacto en fail-safes

#### 4. `quorum_base`
- **Razón:** Afecta lógica core del EventEngine
- **Protección:** `requires_confirmation = true`
- **Frontend:** Explicar impacto en confirmación de eventos

#### 5. `min_feed_confidence`
- **Razón:** Afecta confiabilidad de decisiones
- **Protección:** `requires_confirmation = true`
- **Frontend:** Explicar impacto en calidad de señales

### ⚠️ Importantes (requires_confirmation = true, pero menos críticos)

#### 6. `max_global_exposure`
- **Razón:** Afecta límites de riesgo globales
- **Protección:** `requires_confirmation = true`
- **Frontend:** Mostrar exposición actual vs nuevo límite

#### 7. `max_exposure_per_market`
- **Razón:** Afecta límites de riesgo por mercado
- **Protección:** `requires_confirmation = true`
- **Frontend:** Mostrar exposición actual vs nuevo límite

#### 8. `cancel_on_red`
- **Razón:** Afecta comportamiento en situaciones de alta latencia
- **Protección:** `requires_confirmation = true`
- **Frontend:** Explicar impacto en gestión de órdenes

### 📝 Normales (sin protección especial)

- `safety_tick`
- `target_margin`
- `min_entry_price`
- `max_order_size`
- `scan_interval_seconds`
- Etc.

---

## Implementación en Backend

### ConfigService

**Método para actualizar:**
```python
def update_config(
    self, 
    key: str, 
    value: Any, 
    confirmation_token: Optional[str] = None
) -> bool:
    """
    Actualiza un parámetro de configuración.
    
    Args:
        key: Clave del parámetro
        value: Nuevo valor
        confirmation_token: Token de confirmación (requerido si requires_confirmation = true)
    
    Returns:
        True si se actualizó, False si falló validación
    """
    config = self._get_config(key)
    
    # Verificar is_readonly
    if config.is_readonly:
        raise ValueError(f"Parameter {key} is readonly and cannot be modified")
    
    # Verificar requires_confirmation
    if config.requires_confirmation:
        if not confirmation_token:
            raise ValueError(f"Parameter {key} requires confirmation token")
        if not self._validate_confirmation_token(key, confirmation_token):
            raise ValueError(f"Invalid confirmation token for {key}")
    
    # Validar valor según min/max
    if config.min_value and value < config.min_value:
        raise ValueError(f"Value {value} below minimum {config.min_value}")
    if config.max_value and value > config.max_value:
        raise ValueError(f"Value {value} above maximum {config.max_value}")
    
    # Actualizar en DB
    # ...
    
    # Invalidar cache
    self.invalidate_cache(key)
    
    return True
```

### Endpoint del Frontend

**PUT** `/api/config/{key}`

**Request:**
```json
{
  "value": "LIVE",
  "value_type": "string",
  "confirmation_token": "LIVE"  // Requerido si requires_confirmation = true
}
```

**Response (si requiere confirmación pero no se proporcionó):**
```json
{
  "error": "confirmation_required",
  "message": "This parameter requires confirmation",
  "requires_confirmation": true,
  "confirmation_prompt": "Type 'LIVE' to confirm changing execution mode to LIVE"
}
```

---

## Implementación en Frontend

### Componente de Configuración

**Para parámetros normales:**
- Input directo
- Validación en tiempo real
- Guardar inmediatamente

**Para parámetros con requires_confirmation:**
- Input con botón "Cambiar"
- Al hacer clic, mostrar diálogo de confirmación
- Requerir escribir confirmation_token
- Mostrar advertencia clara del impacto
- Solo guardar después de confirmar

**Para parámetros con is_readonly:**
- Mostrar valor pero deshabilitado
- Mostrar badge "Read-only"
- Explicar por qué es readonly

### Ejemplo de Diálogo de Confirmación

```tsx
<ConfirmationDialog
  title="Cambiar Execution Mode a LIVE"
  warning="⚠️ Esto activará trading real con dinero real"
  confirmationPrompt="Escribe 'LIVE' para confirmar"
  requiredToken="LIVE"
  onConfirm={(token) => updateConfig('execution_mode', 'LIVE', token)}
/>
```

---

## Valores por Defecto en Migración

Al poblar `system_config` con valores iniciales, marcar:

```sql
-- Parámetros críticos
INSERT INTO system_config (key, value, value_type, category, is_readonly, requires_confirmation, description)
VALUES 
  ('allow_zero_checker', 'false', 'bool', 'event_engine', false, true, 'Permitir sistema operativo sin checkers (sin trading)'),
  ('execution_mode', 'DRY_RUN', 'string', 'system', false, true, 'Modo de ejecución: DRY_RUN, PAPER, LIVE'),
  ('latency_fail_mode', 'strict', 'string', 'risk', false, true, 'Modo de fail-safe por latencia'),
  ('quorum_base', '2', 'int', 'event_engine', false, true, 'Quorum base para confirmación de eventos'),
  ('min_feed_confidence', '0.8', 'float', 'event_engine', false, true, 'Confianza mínima requerida de checkers');
```

---

## Validación

Los parámetros están protegidos cuando:

- [ ] Parámetros críticos tienen `requires_confirmation = true`
- [ ] Frontend muestra diálogo de confirmación para parámetros protegidos
- [ ] Backend valida confirmation_token antes de aplicar cambios
- [ ] Parámetros readonly no pueden ser modificados
- [ ] Frontend muestra claramente qué parámetros están protegidos y por qué

