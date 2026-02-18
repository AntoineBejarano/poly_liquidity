"""
TipIntent model - Tip de Telegram (parseado y opcionalmente resuelto a PS3838).

Flujo: PENDING → APPROVED/REJECTED → EXECUTED/FAILED.
"""
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.models.base import BaseModel

class TipIntent(BaseModel):
    """
    Tip proveniente de Telegram (tipster), parseado y opcionalmente ejecutado en PS3838.
    """

    __tablename__ = "tip_intents"

    strategy_id = Column(UUID(as_uuid=True), ForeignKey("strategies.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("neon_auth.users_sync.id"), nullable=True, index=True)

    telegram_message_id = Column(String, nullable=True, index=True)  # dedup
    telegram_chat_id = Column(String, nullable=True)
    raw_text = Column(Text, nullable=True)
    parsed = Column(JSONB, nullable=True)  # partido, seleccion, cuota, stake, etc.

    ps3838_event_id = Column(Numeric(20, 0), nullable=True)
    ps3838_league_id = Column(Numeric(10, 0), nullable=True)
    ps3838_period_number = Column(Numeric(5, 0), nullable=True)
    ps3838_line_id = Column(String, nullable=True)
    ps3838_odds = Column(Numeric(10, 4), nullable=True)
    suggested_stake_usd = Column(Numeric(12, 4), nullable=True)
    risk_class = Column(String, nullable=True)  # low, medium, high

    status = Column(String, nullable=False, default="PENDING", index=True)  # PENDING, APPROVED, REJECTED, EXECUTED, FAILED
    ps3838_bet_id = Column(String, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    executed_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
