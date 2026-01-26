"""
Calculate Indicators Node - Calcula indicadores avanzados (signals).

Este nodo calcula todos los indicadores usando el proveedor apropiado
según el strategy_type y los inyecta en context.signals.
También guarda las señales en DecisionTrace para trazabilidad.
"""
import logging
from typing import Dict, Any

from app.core.strategy_engine.nodes.base import GraphNode, SuccessResult
from app.core.strategy_engine.indicators.factory import create_signal_provider
from app.core.decision_trace.decision_trace_service import DecisionTraceService

logger = logging.getLogger(__name__)


class CalculateIndicatorsNode(GraphNode):
    """
    Nodo que calcula indicadores avanzados (signals).
    
    Config:
        strategy_type: str - Tipo de estrategia ("liquidity", "surebet_arbitrage", etc.)
            Si no se especifica, se lee de context.strategy_type o context.strategy.config
    
    Output:
        context.signals: Dict[str, Optional[float]] - Diccionario con todos los indicadores
    """
    
    async def execute(self) -> SuccessResult:
        """
        Calcula indicadores e inyecta en context.signals.
        
        Si hay un error, inyecta señales vacías (None) pero no falla el nodo.
        """
        # Obtener strategy_type desde config o contexto
        strategy_type = self.config.get("strategy_type")
        if not strategy_type:
            # Intentar leer desde contexto
            strategy_type = getattr(self.context, "strategy_type", None)
            if not strategy_type:
                # Leer desde strategy config si está disponible
                if hasattr(self.context, "strategy") and self.context.strategy:
                    # Si strategy es un objeto, intentar acceder a sus atributos
                    if hasattr(self.context.strategy, "strategy_type"):
                        strategy_type = self.context.strategy.strategy_type
                    elif isinstance(self.context.strategy, dict):
                        strategy_type = self.context.strategy.get("strategy_type", "liquidity")
                    else:
                        strategy_type = "liquidity"  # Default
                else:
                    strategy_type = "liquidity"  # Default
        
        try:
            # Crear proveedor
            provider = create_signal_provider(strategy_type, self.context)
            
            # Calcular indicadores
            signals = provider.calculate_all()
            
            # Inyectar en contexto
            if not hasattr(self.context, "signals"):
                self.context.signals = {}
            self.context.signals.update(signals)
            
            # Contar señales calculadas (no None)
            signals_count = len([v for v in signals.values() if v is not None])
            
            logger.debug(
                f"Calculated {signals_count}/{len(signals)} indicators for strategy_type={strategy_type}",
                extra={"strategy_type": strategy_type, "signals_count": signals_count, "total_signals": len(signals)}
            )
            
            # Guardar en DecisionTrace para trazabilidad
            trace_id = getattr(self.context, "trace_id", None)
            if trace_id:
                try:
                    trace_service = DecisionTraceService()
                    trace_service.log_decision(
                        trace_id=trace_id,
                        component="strategy",
                        decision_stage="SIGNALS_CALCULATION",
                        decision_type="calculation",
                        decision="COMPLETED",
                        input_data={
                            "strategy_type": strategy_type,
                            "market_state_available": self.context.collected_state.get("market_state") is not None if hasattr(self.context, "collected_state") and self.context.collected_state else False,
                            "event_state_available": self.context.collected_state.get("event_state") is not None if hasattr(self.context, "collected_state") and self.context.collected_state else False,
                            "external_data_available": self.context.collected_state.get("external_data") is not None if hasattr(self.context, "collected_state") and self.context.collected_state else False,
                            "risk_state_available": self.context.collected_state.get("risk_state") is not None if hasattr(self.context, "collected_state") and self.context.collected_state else False,
                        },
                        output_data={
                            "signals": signals,
                            "signals_count": signals_count,
                            "total_signals": len(signals),
                            "unreliable": signals.get("unreliable") == 1.0 if isinstance(signals, dict) else False,
                        },
                        reason=f"Calculated {signals_count}/{len(signals)} indicators for {strategy_type} strategy",
                        event_id=getattr(self.context, "event_id", None),
                        market_id=getattr(self.context, "market_id", None),
                    )
                except Exception as trace_error:
                    # No fallar el nodo si hay error al guardar trace
                    logger.warning(
                        f"Error saving signals to DecisionTrace: {trace_error}",
                        exc_info=True
                    )
            
            return SuccessResult()
        except Exception as e:
            logger.error(
                f"Error calculating indicators for strategy_type={strategy_type}: {e}",
                exc_info=True,
                extra={"strategy_type": strategy_type}
            )
            # En caso de error, inyectar señales vacías (None)
            # No fallar el nodo, solo retornar señales vacías
            if not hasattr(self.context, "signals"):
                self.context.signals = {}
            
            # Intentar guardar error en DecisionTrace
            trace_id = getattr(self.context, "trace_id", None)
            if trace_id:
                try:
                    trace_service = DecisionTraceService()
                    trace_service.log_decision(
                        trace_id=trace_id,
                        component="strategy",
                        decision_stage="SIGNALS_CALCULATION",
                        decision_type="calculation",
                        decision="FAILED",
                        input_data={
                            "strategy_type": strategy_type,
                            "error": str(e),
                        },
                        output_data={
                            "signals": {},
                            "signals_count": 0,
                            "error": str(e),
                        },
                        reason=f"Error calculating indicators: {e}",
                        event_id=getattr(self.context, "event_id", None),
                        market_id=getattr(self.context, "market_id", None),
                    )
                except Exception as trace_error:
                    logger.warning(f"Error saving error trace: {trace_error}")
            
            return SuccessResult()

