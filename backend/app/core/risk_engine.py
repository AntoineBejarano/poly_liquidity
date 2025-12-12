"""
Risk engine - validates or rejects order intents according to risk rules.

DEPRECATED: Este archivo se mantiene por compatibilidad.
Usar app.core.risk_engine.risk_engine.RiskEngine en su lugar.
"""
from app.core.risk_engine import RiskEngine as NewRiskEngine, ApprovedOrderIntent

# Re-exportar para compatibilidad
RiskEngine = NewRiskEngine
