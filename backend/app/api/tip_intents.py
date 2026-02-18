"""
API REST TipIntents: listar, crear, actualizar, resolver, aprobar, rechazar, ejecutar.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.auth import get_current_user, User
from app.api.websocket import broadcast_strategy_event
from app.database import get_db
from app.models.tip_intent import TipIntent
from app.core.tipster.tip_intent_service import (
    create_tip_intent_from_message,
    resolve_tip_intent as resolve_tip_intent_svc,
)

router = APIRouter(tags=["tip_intents"])


class CreateTipIntentRequest(BaseModel):
    raw_text: Optional[str] = None
    telegram_message_id: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    image_base64: Optional[str] = None
    caption: Optional[str] = None


class RejectRequest(BaseModel):
    reason: Optional[str] = None


def _tip_to_item(t: TipIntent) -> Dict[str, Any]:
    return {
        "id": str(t.id),
        "strategy_id": str(t.strategy_id),
        "user_id": t.user_id,
        "telegram_message_id": t.telegram_message_id,
        "telegram_chat_id": t.telegram_chat_id,
        "raw_text": t.raw_text,
        "parsed": t.parsed,
        "ps3838_event_id": str(t.ps3838_event_id) if t.ps3838_event_id is not None else None,
        "ps3838_league_id": str(t.ps3838_league_id) if t.ps3838_league_id is not None else None,
        "ps3838_period_number": int(t.ps3838_period_number) if t.ps3838_period_number is not None else None,
        "ps3838_line_id": t.ps3838_line_id,
        "ps3838_odds": float(t.ps3838_odds) if t.ps3838_odds is not None else None,
        "suggested_stake_usd": float(t.suggested_stake_usd) if t.suggested_stake_usd is not None else None,
        "risk_class": t.risk_class,
        "status": t.status,
        "ps3838_bet_id": t.ps3838_bet_id,
        "approved_at": t.approved_at.isoformat() if t.approved_at else None,
        "rejected_at": t.rejected_at.isoformat() if t.rejected_at else None,
        "executed_at": t.executed_at.isoformat() if t.executed_at else None,
        "rejection_reason": t.rejection_reason,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }


def _ensure_tip_belongs_to_user(tip: TipIntent, user_id: str) -> None:
    if tip.user_id != user_id:
        raise HTTPException(status_code=404, detail="TipIntent not found")


@router.get("/strategies/{strategy_id}/tip-intents")
async def list_tip_intents(
    strategy_id: UUID,
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Lista TipIntents de la estrategia. Filtro opcional por status."""
    from app.models.strategy import Strategy
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy or strategy.created_by != current_user.id:
        raise HTTPException(status_code=404, detail="Strategy not found")

    q = db.query(TipIntent).filter(
        TipIntent.strategy_id == strategy_id,
        TipIntent.user_id == current_user.id,
    )
    if status:
        q = q.filter(TipIntent.status == status)
    total = q.count()
    items = q.order_by(TipIntent.created_at.desc()).offset(offset).limit(limit).all()
    return {"items": [_tip_to_item(t) for t in items], "total": total}


@router.get("/strategies/{strategy_id}/tip-intents/summary")
async def get_tip_intents_summary(
    strategy_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Resumen para dashboard: conteo por estado y total."""
    from app.models.strategy import Strategy
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy or strategy.created_by != current_user.id:
        raise HTTPException(status_code=404, detail="Strategy not found")
    from sqlalchemy import func
    counts = (
        db.query(TipIntent.status, func.count(TipIntent.id))
        .filter(
            TipIntent.strategy_id == strategy_id,
            TipIntent.user_id == current_user.id,
        )
        .group_by(TipIntent.status)
        .all()
    )
    total = sum(c[1] for c in counts)
    by_status = {str(s): n for s, n in counts}
    return {"total": total, "by_status": by_status}


@router.post("/strategies/{strategy_id}/tip-intents")
async def create_tip_intent(
    strategy_id: UUID,
    body: CreateTipIntentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Crea un TipIntent desde mensaje (texto o imagen). Para pruebas y envío manual."""
    from app.models.strategy import Strategy
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy or strategy.created_by != current_user.id:
        raise HTTPException(status_code=404, detail="Strategy not found")

    image_bytes = None
    if body.image_base64:
        import base64
        try:
            image_bytes = base64.b64decode(body.image_base64)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid image_base64: {e}")

    tip = create_tip_intent_from_message(
        db=db,
        strategy_id=strategy_id,
        user_id=current_user.id,
        telegram_message_id=body.telegram_message_id,
        telegram_chat_id=body.telegram_chat_id,
        raw_text=body.raw_text,
        image_bytes=image_bytes,
        caption=body.caption,
    )
    try:
        await broadcast_strategy_event(
            strategy_id, "tip_intent_created", {"tip_id": str(tip.id), "status": tip.status}
        )
    except Exception:
        pass
    return _tip_to_item(tip)


@router.get("/tip-intents/{tip_intent_id}")
async def get_tip_intent(
    tip_intent_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Obtiene un TipIntent por ID."""
    tip = db.query(TipIntent).filter(TipIntent.id == tip_intent_id).first()
    if not tip:
        raise HTTPException(status_code=404, detail="TipIntent not found")
    _ensure_tip_belongs_to_user(tip, current_user.id)
    return _tip_to_item(tip)


@router.post("/tip-intents/{tip_intent_id}/resolve")
async def resolve_tip_intent(
    tip_intent_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Ejecuta match resolution contra PS3838 y actualiza el TipIntent."""
    tip = db.query(TipIntent).filter(TipIntent.id == tip_intent_id).first()
    if not tip:
        raise HTTPException(status_code=404, detail="TipIntent not found")
    _ensure_tip_belongs_to_user(tip, current_user.id)
    try:
        tip = await resolve_tip_intent_svc(db, tip_intent_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    try:
        await broadcast_strategy_event(
            tip.strategy_id, "tip_intent_resolved", {"tip_id": str(tip.id), "status": tip.status}
        )
    except Exception:
        pass
    return _tip_to_item(tip)


@router.post("/tip-intents/{tip_intent_id}/approve")
async def approve_tip_intent(
    tip_intent_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Aprueba el tip (status → APPROVED)."""
    tip = db.query(TipIntent).filter(TipIntent.id == tip_intent_id).first()
    if not tip:
        raise HTTPException(status_code=404, detail="TipIntent not found")
    _ensure_tip_belongs_to_user(tip, current_user.id)
    if tip.status != "PENDING":
        raise HTTPException(status_code=400, detail=f"Tip is {tip.status}, cannot approve")
    tip.status = "APPROVED"
    tip.approved_at = datetime.utcnow()
    db.commit()
    db.refresh(tip)
    try:
        await broadcast_strategy_event(
            tip.strategy_id, "tip_intent_approved", {"tip_id": str(tip.id), "status": tip.status}
        )
    except Exception:
        pass
    return _tip_to_item(tip)


@router.post("/tip-intents/{tip_intent_id}/reject")
async def reject_tip_intent(
    tip_intent_id: UUID,
    body: Optional[RejectRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Rechaza el tip (status → REJECTED)."""
    tip = db.query(TipIntent).filter(TipIntent.id == tip_intent_id).first()
    if not tip:
        raise HTTPException(status_code=404, detail="TipIntent not found")
    _ensure_tip_belongs_to_user(tip, current_user.id)
    if tip.status != "PENDING" and tip.status != "APPROVED":
        raise HTTPException(status_code=400, detail=f"Tip is {tip.status}, cannot reject")
    tip.status = "REJECTED"
    tip.rejected_at = datetime.utcnow()
    tip.rejection_reason = (body.reason if body else None) or None
    db.commit()
    db.refresh(tip)
    try:
        await broadcast_strategy_event(
            tip.strategy_id, "tip_intent_rejected", {"tip_id": str(tip.id), "status": tip.status}
        )
    except Exception:
        pass
    return _tip_to_item(tip)


@router.post("/tip-intents/{tip_intent_id}/execute")
async def execute_tip_intent(
    tip_intent_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Encola ejecución (Execution Graph con place_bet_ps3838).
    MVP: marca como EXECUTED si ya está APPROVED; integración real con Execution Graph en siguiente iteración.
    """
    tip = db.query(TipIntent).filter(TipIntent.id == tip_intent_id).first()
    if not tip:
        raise HTTPException(status_code=404, detail="TipIntent not found")
    _ensure_tip_belongs_to_user(tip, current_user.id)
    if tip.status != "APPROVED":
        raise HTTPException(status_code=400, detail="Tip must be APPROVED to execute")
    # TODO: encolar en Execution Graph (risk_check → odds_still_valid → place_bet_ps3838)
    tip.status = "EXECUTED"
    tip.executed_at = datetime.utcnow()
    db.commit()
    db.refresh(tip)
    try:
        await broadcast_strategy_event(
            tip.strategy_id, "tip_intent_executed", {"tip_id": str(tip.id), "status": tip.status}
        )
    except Exception:
        pass
    return _tip_to_item(tip)
