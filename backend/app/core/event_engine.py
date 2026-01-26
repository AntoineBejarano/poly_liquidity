"""
Event engine - determines when events are actually finished using dynamic checkers.
"""
import logging
import time
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from app.core.state import state
from app.core.config_service import config_service
from app.core.decision_trace import decision_trace_service
from app.core.secrets import secret_service
from app.core.checkers.registry import checker_registry
from app.core.checkers.base import BaseChecker, CheckerResult
from app.core.checkers.health_service import checker_health_service
from app.database import SessionLocal
from app.models.event import Event
from app.models.market import Market
from app.models.event_checker import EventChecker
from app.models.checker_config import CheckerConfig

logger = logging.getLogger(__name__)


class EventEngine:
    """Event engine service with dynamic checkers."""
    
    async def _get_active_checkers_for_category(self, category: str) -> List[Dict[str, Any]]:
        """
        Get active checkers for a category.
        Returns list of checker configs with their implementations.
        """
        db = SessionLocal()
        try:
            # Get enabled checkers for this category
            checkers = db.query(EventChecker).filter(
                EventChecker.category == category,
                EventChecker.enabled == True
            ).all()
            
            result = []
            for checker in checkers:
                # Get configs for this checker
                configs = db.query(CheckerConfig).filter(
                    CheckerConfig.checker_id == checker.id,
                    CheckerConfig.enabled == True
                ).all()
                
                for config in configs:
                    result.append({
                        "checker": checker,
                        "config": config,
                    })
            
            return result
        finally:
            db.close()
    
    async def _execute_checker(
        self,
        checker_class: type[BaseChecker],
        checker_id: str,
        external_event_id: str,
        secret_name: str | None
    ) -> CheckerResult | None:
        """
        Execute a checker with its credentials and record health metrics.
        
        Args:
            checker_class: Clase del checker a ejecutar
            checker_id: UUID del checker (para health tracking)
            external_event_id: ID del evento externo
            secret_name: Nombre del secreto con credenciales
            
        Returns:
            CheckerResult o None si falla
        """
        from uuid import UUID
        
        start_time = time.time()
        success = False
        result = None
        
        try:
            # Load credentials if needed
            credentials = None
            if secret_name:
                secret_value = await secret_service.get_secret(secret_name)
                if secret_value:
                    credentials = {"api_key": secret_value}  # Adjust based on checker needs
            
            # Instantiate and execute checker
            checker_instance = checker_class()
            result = await checker_instance.check(external_event_id, credentials)
            success = result is not None
            return result
        except Exception as e:
            logger.error(f"Error executing checker {checker_id}: {e}", exc_info=True)
            success = False
            error_message = str(e)
        finally:
            # Registrar ejecución en health service
            latency_ms = (time.time() - start_time) * 1000
            try:
                from uuid import UUID
                checker_uuid = UUID(checker_id) if isinstance(checker_id, str) else checker_id
                checker_health_service.record_execution(
                    checker_id=checker_uuid,
                    success=success,
                    latency_ms=latency_ms,
                    error_message=error_message if not success else None
                )
            except Exception as health_error:
                logger.warning(f"Error recording checker health: {health_error}")
    
    def _calculate_effective_quorum(
        self,
        quorum_base: int,
        available_checkers: int,
        allow_single_checker: bool,
        allow_zero_checker: bool
    ) -> Tuple[Optional[int], str, bool]:
        """
        Calcula el quorum efectivo basado en checkers disponibles.
        
        Args:
            quorum_base: Quorum base configurado
            available_checkers: Número de checkers saludables disponibles
            allow_single_checker: Permitir quorum de 1
            allow_zero_checker: Permitir sistema sin checkers (sin trading)
            
        Returns:
            Tupla (quorum_efectivo, razon, trading_permitido)
        """
        # 🔴 REGLA CRÍTICA: Con 0 checkers, NUNCA confirmar FINISHED
        if available_checkers == 0:
            if allow_zero_checker:
                return (None, "no_checkers_available_allow_zero", False)
            else:
                return (None, "no_checkers_available_system_degraded", False)
        
        # Con 1 checker disponible
        if available_checkers == 1:
            if allow_single_checker:
                return (1, "single_checker_allowed", True)
            else:
                # Quorum base puede ser 1, pero con advertencia
                effective = min(quorum_base, 1)
                return (effective, "single_checker_available_quorum_base_applied", True)
        
        # Con 2+ checkers disponibles
        effective = min(quorum_base, available_checkers)
        return (effective, "quorum_base_applied", True)
    
    async def _aggregate_checker_results(
        self,
        results: List[CheckerResult],
        category: str,
        healthy_checker_ids: List[str]
    ) -> Tuple[str, float, Dict[str, Any]]:
        """
        Agrega resultados de checkers usando reglas de quorum dinámicas.
        
        Args:
            results: Lista de resultados de checkers
            category: Categoría del evento
            healthy_checker_ids: Lista de IDs de checkers saludables que participaron
            
        Returns:
            Tupla (state, confidence, metadata) donde metadata incluye información de quorum
        """
        if not results:
            return ("LIVE", 0.0, {
                "quorum_used": None,
                "quorum_required": None,
                "checkers_available": 0,
                "checkers_used": 0,
                "quorum_reason": "no_checker_results",
                "trading_permitted": False
            })
        
        # Obtener configuración
        min_confidence = float(config_service.get("min_feed_confidence", 0.8))
        quorum_base = int(config_service.get("quorum_base", 2))
        allow_single_checker = config_service.get("allow_single_checker", False)
        allow_zero_checker = config_service.get("allow_zero_checker", False)
        
        # Contar checkers saludables disponibles
        available_count = len(healthy_checker_ids)
        
        # Calcular quorum efectivo
        quorum_effective, quorum_reason, trading_permitted = self._calculate_effective_quorum(
            quorum_base=quorum_base,
            available_checkers=available_count,
            allow_single_checker=allow_single_checker,
            allow_zero_checker=allow_zero_checker
        )
        
        # 🔴 REGLA CRÍTICA: Con 0 checkers, NUNCA confirmar FINISHED
        if available_count == 0 or quorum_effective is None:
            return ("UNKNOWN", 0.0, {
                "quorum_used": None,
                "quorum_required": quorum_base,
                "checkers_available": 0,
                "checkers_used": len(results),
                "quorum_reason": quorum_reason,
                "trading_permitted": False,
                "system_status": "OPERATIONAL_NO_TRADING" if allow_zero_checker else "DEGRADED"
            })
        
        # Contar resultados FINISHED con confianza suficiente
        finished_count = sum(
            1 for r in results
            if r.state == "FINISHED" and r.confidence >= min_confidence
        )
        
        # Calcular confianza promedio
        avg_confidence = sum(r.confidence for r in results) / len(results) if results else 0.0
        
        # Aplicar quorum dinámico
        metadata = {
            "quorum_used": quorum_effective,
            "quorum_required": quorum_base,
            "checkers_available": available_count,
            "checkers_used": finished_count,
            "quorum_reason": quorum_reason,
            "trading_permitted": trading_permitted
        }
        
        if finished_count >= quorum_effective:
            # Quorum cumplido: FINISHED_CONFIRMED
            return ("FINISHED_CONFIRMED", avg_confidence, metadata)
        elif finished_count == 1 and quorum_effective == 1:
            # Un solo checker con quorum de 1: FINISHED_UNCONFIRMED
            return ("FINISHED_UNCONFIRMED", avg_confidence, metadata)
        elif finished_count > 0:
            # Hay checkers que dicen FINISHED pero no cumplen quorum
            return ("FINISHED_UNCONFIRMED", avg_confidence, {
                **metadata,
                "quorum_reason": f"insufficient_quorum_{finished_count}_of_{quorum_effective}"
            })
        else:
            # Ningún checker dice FINISHED
            return ("LIVE", avg_confidence, metadata)
    
    async def _update_event_state(
        self,
        market_id,
        new_state: str,
        confidence: float,
        finished_at: datetime | None,
        quorum_metadata: Dict[str, Any] | None = None
    ):
        """
        Update event state in memory and DB.
        
        Args:
            market_id: ID del mercado
            new_state: Nuevo estado del evento
            confidence: Confianza del estado
            finished_at: Timestamp de finalización (si aplica)
            quorum_metadata: Metadatos de quorum (quorum_used, checkers_available, etc.)
        """
        # Update in-memory state
        if market_id not in state.events:
            from app.core.state import EventState
            state.events[market_id] = EventState()
            state.events[market_id].market_id = market_id
        
        event_state = state.events[market_id]
        event_state.state = new_state
        event_state.confidence = confidence
        event_state.finished_at = finished_at
        event_state.updated_at = datetime.utcnow()
        
        # Actualizar información de quorum
        if quorum_metadata:
            event_state.quorum_used = quorum_metadata.get("quorum_used")
            event_state.quorum_required = quorum_metadata.get("quorum_required")
            event_state.checkers_available = quorum_metadata.get("checkers_available", 0)
            event_state.checkers_used = quorum_metadata.get("checkers_used", 0)
            event_state.quorum_reason = quorum_metadata.get("quorum_reason")
            event_state.trading_permitted = quorum_metadata.get("trading_permitted", False)
        
        # Update in DB
        db = SessionLocal()
        try:
            db_event = db.query(Event).filter(Event.market_id == market_id).first()
            if db_event:
                db_event.state = new_state
                db_event.confidence = confidence
                db_event.finished_at = finished_at
                db_event.updated_at = datetime.utcnow()
                
                # Update feed confirmations based on state
                if new_state == "FINISHED_CONFIRMED":
                    db_event.feed_a_confirmed = True
                    db_event.feed_b_confirmed = True
                elif new_state == "FINISHED_UNCONFIRMED":
                    db_event.feed_a_confirmed = True
                    db_event.feed_b_confirmed = False
                else:
                    db_event.feed_a_confirmed = False
                    db_event.feed_b_confirmed = False
                
                db.commit()
        except Exception as e:
            db.rollback()
            print(f"Error updating event state in DB: {e}")
        finally:
            db.close()
    
    async def tick(self):
        """
        Update external event states using dynamic checkers.
        
        Flow:
        1. For each market with external_event_id and category:
           - Load active checkers for that category
           - For each checker:
             - Load credentials dynamically (SecretService)
             - Call external API (checkers use their own APIs, not Polymarket)
             - Produce Finished / Not Finished signal
        2. Aggregate signals (quorum rules)
        3. Set EventState (LIVE / FINISHED_CONFIRMED)
        
        Note: If EventEngine needs to fetch market data from Polymarket Data API:
        - Batch requests: Group markets by category and fetch in batches
        - Use caching: Cache market data with appropriate TTL (see api_cache)
        - Rate limiting: Use rate_limiter with EndpointType.DATA_API (200 req/10s)
        - Example batching pattern:
          ```
          # Group markets by category
          markets_by_category = {}
          for market in markets:
              category = market.category
              if category not in markets_by_category:
                  markets_by_category[category] = []
              markets_by_category[category].append(market)
          
          # Fetch data in batches (max 10 markets per batch to stay within limits)
          for category, category_markets in markets_by_category.items():
              for i in range(0, len(category_markets), 10):
                  batch = category_markets[i:i+10]
                  # Wait for rate limit capacity
                  await rate_limiter.wait_for_capacity(EndpointType.DATA_API)
                  # Fetch batch data
                  # ...
          ```
        """
        db = SessionLocal()
        try:
            # Get all markets with external_event_id
            markets = db.query(Market).join(Event).filter(
                Market.enabled == True,
                Event.external_event_id.isnot(None)
            ).all()
            
            for market in markets:
                event = db.query(Event).filter(Event.market_id == market.id).first()
                if not event or not event.external_event_id:
                    continue
                
                # Determine category (from config or market metadata)
                category = config_service.get("default_category", "sports")
                
                # Get active checkers for this category
                checker_configs = await self._get_active_checkers_for_category(category)
                
                if not checker_configs:
                    # No checkers active, keep state as LIVE
                    continue
                
                # Obtener checkers saludables para esta categoría
                healthy_checkers = checker_health_service.get_healthy_checkers(category)
                healthy_checker_ids = [str(c.id) for c in healthy_checkers]
                
                # Execute all checkers (solo los saludables si hay disponibles)
                results: List[CheckerResult] = []
                executed_checker_ids: List[str] = []
                
                for item in checker_configs:
                    checker = item["checker"]
                    config = item["config"]
                    
                    # Solo ejecutar si el checker está saludable (o si no hay checkers saludables y allow_zero_checker)
                    checker_id_str = str(checker.id)
                    is_healthy = checker_health_service.is_checker_healthy(checker.id)
                    
                    if not is_healthy and healthy_checker_ids:
                        # Hay checkers saludables disponibles, saltar este
                        logger.debug(f"Skipping unhealthy checker {checker.name} (id: {checker.id})")
                        continue
                    
                    try:
                        # Get checker class from registry
                        checker_class = checker_registry.get(checker.implementation_key)
                        
                        # Execute checker
                        result = await self._execute_checker(
                            checker_class,
                            checker_id_str,
                            event.external_event_id,
                            config.secret_name
                        )
                        
                        if result:
                            # Apply weight
                            result.confidence *= config.weight
                            results.append(result)
                            executed_checker_ids.append(checker_id_str)
                    except ValueError:
                        # Checker implementation not found
                        logger.warning(f"Checker implementation '{checker.implementation_key}' not found")
                        continue
                    except Exception as e:
                        logger.error(f"Error executing checker {checker.implementation_key}: {e}", exc_info=True)
                        continue
                
                # Aggregate results con quorum dinámico
                new_state, confidence, quorum_metadata = await self._aggregate_checker_results(
                    results,
                    category,
                    healthy_checker_ids
                )
                
                # Determine finished_at
                finished_at = None
                if new_state in ("FINISHED_CONFIRMED", "FINISHED_UNCONFIRMED"):
                    # Get finished_at from first FINISHED result
                    for result in results:
                        if result.state == "FINISHED" and result.finished_at:
                            finished_at = result.finished_at
                            break
                    if not finished_at:
                        finished_at = datetime.utcnow()
                
                # Update state con información de quorum
                await self._update_event_state(
                    market.id,
                    new_state,
                    confidence,
                    finished_at,
                    quorum_metadata
                )
                
                # Log quorum decision
                logger.info(
                    f"Event state updated for market {market.id}: {new_state} "
                    f"(quorum: {quorum_metadata.get('quorum_used')}/{quorum_metadata.get('quorum_required')}, "
                    f"checkers: {quorum_metadata.get('checkers_used')}/{quorum_metadata.get('checkers_available')}, "
                    f"reason: {quorum_metadata.get('quorum_reason')})"
                )
                
                # Log decision trace para confirmación de evento
                from uuid import uuid4
                decision_trace_service.log_decision(
                    trace_id=uuid4(),  # Nuevo trace_id para esta decisión de evento
                    component="event_engine",
                    decision_stage="EVENT_CONFIRMATION",
                    decision_type="entry" if new_state == "FINISHED_CONFIRMED" else "reject",
                    decision="APPROVED" if new_state == "FINISHED_CONFIRMED" else "REJECTED",
                    input_data={
                        "market_id": str(market.id),
                        "checkers_available": quorum_metadata.get("checkers_available", 0) if quorum_metadata else 0,
                        "checkers_healthy": len(healthy_checkers),
                        "quorum_base": quorum_metadata.get("quorum_required", 0) if quorum_metadata else 0,
                        "quorum_effective": quorum_metadata.get("quorum_used", 0) if quorum_metadata else 0,
                        "checkers_used": quorum_metadata.get("checkers_used", 0) if quorum_metadata else 0,
                        "checker_results_count": len(results),
                    },
                    output_data={
                        "event_state": new_state,
                        "confidence": confidence,
                        "quorum_used": quorum_metadata.get("quorum_used") if quorum_metadata else None,
                        "trading_permitted": quorum_metadata.get("trading_permitted", False) if quorum_metadata else False,
                    },
                    reason=quorum_metadata.get("quorum_reason", "no_decision") if quorum_metadata else "no_decision",
                    market_id=market.id,
                    confidence_score=confidence,
                    metadata=quorum_metadata
                )
        finally:
            db.close()
