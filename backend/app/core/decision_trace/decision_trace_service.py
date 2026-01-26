"""
Decision Trace Service - Maneja el logging de decisiones del bot.
"""
import logging
import hashlib
import json
from typing import Dict, Any, Optional
from datetime import datetime
from uuid import UUID, uuid4

from app.database import SessionLocal
from app.models.decision_trace import DecisionTrace
from app.core.config_service import config_service

logger = logging.getLogger(__name__)


class DecisionTraceService:
    """
    Service para registrar decisiones del bot en decision_trace.
    
    Características:
    - Mantiene input_data conciso (solo hashes/snapshots, no orderbooks completos)
    - Incluye decision_stage para reconstruir el pipeline
    - Registra configuración usada para cada decisión
    """
    
    def __init__(self):
        """Inicializa el servicio."""
        self._current_session_id: Optional[UUID] = None
    
    def set_session_id(self, session_id: UUID):
        """Establece el session_id actual para todos los traces."""
        self._current_session_id = session_id
    
    def _hash_large_data(self, data: Any) -> str:
        """
        Genera hash SHA256 de datos grandes.
        
        Útil para orderbooks, historiales, etc.
        """
        if isinstance(data, dict):
            data_str = json.dumps(data, sort_keys=True)
        elif isinstance(data, str):
            data_str = data
        else:
            data_str = str(data)
        
        return hashlib.sha256(data_str.encode()).hexdigest()
    
    def _make_input_data_concise(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hace input_data conciso según guidelines.
        
        - NO incluye orderbooks completos
        - NO incluye historiales extensos
        - SÍ incluye hashes, snapshots, métricas clave
        """
        concise = {}
        
        for key, value in input_data.items():
            # Si es un orderbook completo, reemplazar con hash
            if key in ["orderbook", "full_orderbook", "orderbook_data"]:
                concise[f"{key}_hash"] = self._hash_large_data(value)
                # Incluir solo resumen
                if isinstance(value, dict):
                    concise[f"{key}_summary"] = {
                        "best_ask": value.get("best_ask"),
                        "best_bid": value.get("best_bid"),
                        "spread": value.get("spread"),
                        "total_liquidity": value.get("total_liquidity"),
                    }
            # Si es un historial extenso, reemplazar con hash
            elif key in ["price_history", "history", "historical_data"] and isinstance(value, list) and len(value) > 10:
                concise[f"{key}_hash"] = self._hash_large_data(value)
                concise[f"{key}_count"] = len(value)
                # Incluir solo primeros y últimos elementos
                if len(value) > 0:
                    concise[f"{key}_first"] = value[0] if isinstance(value[0], (dict, list)) else str(value[0])
                    concise[f"{key}_last"] = value[-1] if isinstance(value[-1], (dict, list)) else str(value[-1])
            # Si es un array grande, limitar tamaño
            elif isinstance(value, list) and len(value) > 20:
                concise[key] = value[:10]  # Primeros 10
                concise[f"{key}_total_count"] = len(value)
                concise[f"{key}_hash"] = self._hash_large_data(value)
            # Si es un dict grande, incluir solo keys importantes
            elif isinstance(value, dict) and len(value) > 50:
                # Incluir solo keys importantes
                important_keys = ["best_ask", "best_bid", "spread", "liquidity", "volume", "status", "state"]
                concise[key] = {k: v for k, v in value.items() if k in important_keys}
                concise[f"{key}_hash"] = self._hash_large_data(value)
                concise[f"{key}_total_keys"] = len(value)
            else:
                # Datos pequeños, incluir directamente
                concise[key] = value
        
        return concise
    
    def _get_config_snapshot(self, component: str) -> Dict[str, Any]:
        """
        Obtiene snapshot de configuración para un componente.
        
        Args:
            component: "scanner", "strategy", "risk", "execution", "event_engine"
        """
        try:
            if component == "scanner":
                return config_service.get_scanner_config()
            elif component == "strategy":
                strategy_config = config_service.get_strategy_config()
                return strategy_config.dict() if hasattr(strategy_config, 'dict') else strategy_config
            elif component == "risk":
                risk_config = config_service.get_risk_engine_config()
                return risk_config.dict() if hasattr(risk_config, 'dict') else risk_config
            elif component == "execution":
                return config_service.get_execution_config()
            elif component == "event_engine":
                return config_service.get_event_engine_config()
            else:
                return {}
        except Exception as e:
            logger.warning(f"Error getting config snapshot for {component}: {e}")
            return {}
    
    def log_decision(
        self,
        trace_id: UUID,
        component: str,
        decision_stage: str,
        decision_type: str,
        decision: str,
        input_data: Dict[str, Any],
        output_data: Optional[Dict[str, Any]] = None,
        reason: Optional[str] = None,
        market_id: Optional[UUID] = None,
        event_id: Optional[UUID] = None,
        latency_ms: Optional[float] = None,
        confidence_score: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[UUID]:
        """
        Registra una decisión en decision_trace.
        
        Args:
            trace_id: ID único del trace (mismo para todas las etapas del pipeline)
            component: "scanner", "strategy", "risk", "execution"
            decision_stage: "SCAN", "EVENT_CONFIRMATION", "STRATEGY", "RISK", "EXECUTION"
            decision_type: "entry", "reject", "adjust", "cancel"
            decision: "APPROVED", "REJECTED", "ADJUSTED", "CANCELLED"
            input_data: Datos de entrada (será hecho conciso automáticamente)
            output_data: Datos de salida (opcional)
            reason: Razón de la decisión (opcional)
            market_id: ID del mercado (opcional)
            event_id: ID del evento (opcional)
            latency_ms: Latencia en milisegundos (opcional)
            confidence_score: Score de confianza (opcional)
            metadata: Metadata adicional (opcional)
        
        Returns:
            ID del registro creado o None si falló
        """
        try:
            # Hacer input_data conciso
            concise_input = self._make_input_data_concise(input_data)
            
            # Obtener snapshot de configuración
            config_snapshot = self._get_config_snapshot(component)
            
            # Crear registro
            db = SessionLocal()
            try:
                decision_trace = DecisionTrace(
                    id=uuid4(),
                    session_id=self._current_session_id,
                    trace_id=trace_id,
                    timestamp=datetime.utcnow(),
                    component=component,
                    decision_stage=decision_stage,
                    market_id=market_id,
                    event_id=event_id,
                    decision_type=decision_type,
                    decision=decision,
                    reason=reason,
                    input_data=concise_input,
                    output_data=output_data,
                    config_used=config_snapshot,
                    latency_ms=latency_ms,
                    confidence_score=confidence_score,
                    extra_metadata=metadata,  # Renamed from 'metadata' (reserved in SQLAlchemy)
                )
                
                db.add(decision_trace)
                db.commit()
                db.refresh(decision_trace)
                
                logger.debug(
                    f"Decision trace logged: {decision_stage} - {decision}",
                    extra={
                        "component": component,
                        "decision_stage": decision_stage,
                        "decision": decision,
                        "trace_id": str(trace_id),
                        "decision_trace_id": str(decision_trace.id)
                    }
                )
                
                return decision_trace.id
            except Exception as e:
                db.rollback()
                logger.error(f"Error creating decision trace: {e}", exc_info=True)
                return None
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Error in log_decision: {e}", exc_info=True)
            return None


# Global instance
decision_trace_service = DecisionTraceService()

