"""
API de conexión Telegram: send_code, sign_in, get_dialogs, save_connection.
Requiere TELEGRAM_API_ID y TELEGRAM_API_HASH en env.
"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.auth import get_current_user, User
from app.core.telegram.service import TelegramConnectionService, TelegramFloodError
from app.database import get_db
from app.models.external_data_source import ExternalDataSource

router = APIRouter(prefix="/telegram", tags=["telegram"])

telegram_service = TelegramConnectionService()


class SendCodeRequest(BaseModel):
    phone: str


class SignInRequest(BaseModel):
    phone: str
    code: str
    phone_code_hash: str
    session_pending_hex: str = Field(..., description="Sesión de send-code; phone_code_hash solo es válido en esa sesión")
    password: Optional[str] = None


class DialogsRequest(BaseModel):
    session_encrypted_hex: str


class SaveConnectionRequest(BaseModel):
    """Guarda la sesión Telegram como ExternalDataSource (cuenta Telegram)."""
    name: str = Field(..., min_length=1, max_length=255)
    session_encrypted_hex: str = Field(..., min_length=1)
    monitored_chats: List[str] = Field(default_factory=list, description="Lista de chat_id a monitorear")
    chat_filters: Optional[Dict[str, Dict[str, str]]] = Field(
        None,
        description='Filtros por chat_id: {"-100123": {"include_regex": "...", "exclude_regex": "..."}}',
    )


@router.post("/send-code")
async def send_code(
    body: SendCodeRequest,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Envía código de verificación al teléfono del usuario."""
    try:
        out = await telegram_service.send_code_request(body.phone)
        return out
    except TelegramFloodError as e:
        raise HTTPException(
            status_code=429,
            detail={
                "code": "PHONE_NUMBER_FLOOD",
                "message": str(e),
                "retry_after_seconds": e.retry_after_seconds,
            },
        )
    except RuntimeError as e:
        if "not installed" in str(e).lower():
            raise HTTPException(status_code=501, detail="Telegram integration not available (telethon not installed)")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Telegram send-code failed: {getattr(e, 'message', str(e))}",
        )


@router.post("/sign-in")
async def sign_in(
    body: SignInRequest,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Completa el login con el código. Devuelve session_encrypted para guardar."""
    try:
        out = await telegram_service.sign_in(
            body.phone,
            body.code,
            body.phone_code_hash,
            body.session_pending_hex,
            password=body.password,
        )
        return out
    except RuntimeError as e:
        if "not installed" in str(e).lower():
            raise HTTPException(status_code=501, detail="Telegram integration not available")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Telegram sign-in failed: {getattr(e, 'message', str(e))}",
        )


@router.post("/dialogs")
async def get_dialogs(
    body: DialogsRequest,
    current_user: User = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """Lista grupos/canales del usuario con la sesión guardada."""
    try:
        return await telegram_service.get_dialogs(body.session_encrypted_hex)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        if "not installed" in str(e).lower():
            raise HTTPException(status_code=501, detail="Telegram integration not available")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Telegram get-dialogs failed: {getattr(e, 'message', str(e))}",
        )


@router.post("/save-connection")
async def save_connection(
    body: SaveConnectionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Guarda la sesión Telegram como ExternalDataSource (connector_type=telegram).
    Flujo: sign_in → get_dialogs → usuario elige chats → save_connection.
    """
    try:
        connector_config: Dict[str, Any] = {
            "session_encrypted_hex": body.session_encrypted_hex,
            "monitored_chats": list(body.monitored_chats),
        }
        if body.chat_filters:
            connector_config["chat_filters"] = body.chat_filters
        source = ExternalDataSource(
            name=body.name,
            connector_type="telegram",
            connector_config=connector_config,
            is_active=True,
            created_by=current_user.id,
        )
        db.add(source)
        db.commit()
        db.refresh(source)
        return {
            "id": str(source.id),
            "name": source.name,
            "connector_type": source.connector_type,
            "monitored_chats": body.monitored_chats,
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Telegram save-connection failed: {getattr(e, 'message', str(e))}",
        )
