"""
Respuestas de error estándar para la API (política v2, fail closed).
"""
from fastapi import HTTPException

# Wallet no configurada: cualquier acción manual API que requiera CLOB debe fallar con esto (no skip).
WALLET_NOT_CONFIGURED_STATUS = 409
WALLET_NOT_CONFIGURED_DETAIL = {
    "error": "WALLET_NOT_CONFIGURED",
    "message": "User wallet not configured",
}


def wallet_not_configured() -> HTTPException:
    """409 + payload estándar cuando falta wallet del usuario (política v2)."""
    return HTTPException(
        status_code=WALLET_NOT_CONFIGURED_STATUS,
        detail=WALLET_NOT_CONFIGURED_DETAIL,
    )
