"""
Strategy Comparator - Comparador de versiones de estrategia.

Según especificación en docs/services/historical_replay.md
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from app.core.historical_replay.event_store import EventStore
from app.core.historical_replay.replay_engine import ReplayEngine

logger = logging.getLogger(__name__)


class StrategyComparator:
    """
    Comparador de versiones de estrategia.
    
    Permite comparar decisiones de diferentes versiones de estrategia
    sobre eventos históricos reales.
    """
    
    def __init__(self, event_store: EventStore, replay_engine: ReplayEngine):
        """
        Inicializa el Strategy Comparator.
        
        Args:
            event_store: Instancia de EventStore
            replay_engine: Instancia de ReplayEngine
        """
        self.event_store = event_store
        self.replay_engine = replay_engine
    
    async def compare_strategies(
        self,
        market_id: str,
        original_strategy: Any,  # Strategy instance
        new_strategy: Any,  # Strategy instance
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Compara dos versiones de estrategia sobre eventos históricos.
        
        Args:
            market_id: ID del mercado
            original_strategy: Instancia de estrategia original
            new_strategy: Instancia de nueva estrategia
            start_time: Timestamp de inicio (opcional)
            end_time: Timestamp de fin (opcional)
            
        Returns:
            Diccionario con comparación de intents, diferencias, PnL simulado
        """
        # Obtener eventos históricos
        events = await self.replay_engine.replay_market(
            market_id=market_id,
            start_time=start_time,
            end_time=end_time
        )
        
        # Extraer eventos relevantes para strategy (watcher_event_state)
        strategy_events = [
            e for e in events
            if e.get("type") == "watcher_event_state"
        ]
        
        # Ejecutar replay con estrategia original
        original_intents = []
        for event in strategy_events:
            try:
                # Simular tick de strategy con el evento histórico
                # Esto requiere que Strategy tenga un método para procesar eventos históricos
                # Por ahora, asumimos que podemos extraer intents del histórico
                if event.get("state") == "FINISHED_CONFIRMED":
                    # Buscar intents generados después de este evento
                    event_timestamp = datetime.fromisoformat(
                        event["timestamp"].replace("Z", "+00:00")
                    )
                    intents_after = await self.event_store.get_events(
                        market_id=market_id,
                        event_type="strategy_intent_created",
                        start_time=event_timestamp,
                        limit=10
                    )
                    original_intents.extend(intents_after)
            except Exception as e:
                logger.warning(f"Error processing event with original strategy: {e}")
        
        # Ejecutar replay con nueva estrategia
        # Nota: Esto requiere que la nueva estrategia pueda procesar eventos históricos
        # Por ahora, simulamos que genera intents similares pero con posibles diferencias
        new_intents = []
        for event in strategy_events:
            try:
                # Similar a original, pero usando new_strategy
                # En una implementación real, llamaríamos a new_strategy.tick() con el estado histórico
                if event.get("state") == "FINISHED_CONFIRMED":
                    event_timestamp = datetime.fromisoformat(
                        event["timestamp"].replace("Z", "+00:00")
                    )
                    # Por ahora, usamos los mismos intents pero podríamos modificarlos
                    # según la nueva estrategia
                    intents_after = await self.event_store.get_events(
                        market_id=market_id,
                        event_type="strategy_intent_created",
                        start_time=event_timestamp,
                        limit=10
                    )
                    new_intents.extend(intents_after)
            except Exception as e:
                logger.warning(f"Error processing event with new strategy: {e}")
        
        # Calcular diferencias
        differences = self._calculate_differences(original_intents, new_intents)
        
        # Simular PnL
        simulated_pnl_original = self._simulate_pnl(original_intents, events)
        simulated_pnl_new = self._simulate_pnl(new_intents, events)
        
        comparison = {
            "market_id": market_id,
            "original_intents_count": len(original_intents),
            "new_intents_count": len(new_intents),
            "original_total_size": sum(
                intent.get("size", 0.0) for intent in original_intents
            ),
            "new_total_size": sum(
                intent.get("size", 0.0) for intent in new_intents
            ),
            "simulated_pnl_original": simulated_pnl_original,
            "simulated_pnl_new": simulated_pnl_new,
            "improvement": simulated_pnl_new - simulated_pnl_original,
            "differences": differences
        }
        
        return comparison
    
    def _calculate_differences(
        self,
        original_intents: List[Dict[str, Any]],
        new_intents: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Calcula diferencias entre intents originales y nuevos.
        
        Args:
            original_intents: Lista de intents originales
            new_intents: Lista de intents nuevos
            
        Returns:
            Lista de diferencias
        """
        differences = []
        
        # Comparar por timestamp
        original_by_time = {
            intent.get("timestamp"): intent
            for intent in original_intents
        }
        new_by_time = {
            intent.get("timestamp"): intent
            for intent in new_intents
        }
        
        # Encontrar diferencias
        all_timestamps = set(original_by_time.keys()) | set(new_by_time.keys())
        
        for timestamp in all_timestamps:
            original = original_by_time.get(timestamp)
            new = new_by_time.get(timestamp)
            
            if original and new:
                # Comparar valores
                if original.get("size") != new.get("size") or \
                   original.get("target_price") != new.get("target_price"):
                    differences.append({
                        "event_timestamp": timestamp,
                        "original": {
                            "size": original.get("size"),
                            "target_price": original.get("target_price")
                        },
                        "new": {
                            "size": new.get("size"),
                            "target_price": new.get("target_price")
                        },
                        "reason": "Strategy parameters changed"
                    })
            elif original and not new:
                differences.append({
                    "event_timestamp": timestamp,
                    "original": {
                        "size": original.get("size"),
                        "target_price": original.get("target_price")
                    },
                    "new": None,
                    "reason": "New strategy did not generate intent"
                })
            elif new and not original:
                differences.append({
                    "event_timestamp": timestamp,
                    "original": None,
                    "new": {
                        "size": new.get("size"),
                        "target_price": new.get("target_price")
                    },
                    "reason": "New strategy generated additional intent"
                })
        
        return differences
    
    def _simulate_pnl(
        self,
        intents: List[Dict[str, Any]],
        events: List[Dict[str, Any]]
    ) -> float:
        """
        Simula PnL basado en intents y eventos de fills.
        
        Args:
            intents: Lista de intents
            events: Lista de eventos (para obtener fills)
            
        Returns:
            PnL simulado
        """
        total_pnl = 0.0
        
        # Obtener fills de eventos
        fills_by_order = {}
        for event in events:
            if event.get("type") == "execution_order_filled":
                order_id = event.get("order_id")
                fills = event.get("fills", [])
                if order_id and fills:
                    fills_by_order[order_id] = fills
        
        # Calcular PnL para cada intent que tuvo fill
        for intent in intents:
            # Buscar fills relacionados (por trace_id o market_id)
            intent_trace_id = intent.get("trace_id")
            intent_market_id = intent.get("market_id")
            
            # Buscar fills en eventos
            for event in events:
                if event.get("type") == "execution_order_filled":
                    if event.get("trace_id") == intent_trace_id or \
                       event.get("market_id") == intent_market_id:
                        fills = event.get("fills", [])
                        target_price = intent.get("target_price", 0.0)
                        
                        for fill in fills:
                            fill_price = fill.get("price", 0.0)
                            fill_size = fill.get("size", 0.0)
                            
                            # PnL = (precio_resolución - precio_fill) * tamaño
                            # Asumimos que el mercado se resuelve a 1.0 (ganador)
                            # En una implementación real, usaríamos el precio real de resolución
                            resolution_price = 1.0
                            pnl = (resolution_price - fill_price) * fill_size
                            total_pnl += pnl
        
        return total_pnl

