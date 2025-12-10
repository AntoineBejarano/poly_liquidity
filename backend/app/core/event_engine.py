"""
Event engine - determines when events are actually finished using dynamic checkers.
"""
from typing import List, Dict, Any
from datetime import datetime
from app.core.state import state
from app.core.config_service import config_service
from app.core.secrets import secret_service
from app.core.checkers.registry import checker_registry
from app.core.checkers.base import BaseChecker, CheckerResult
from app.database import SessionLocal
from app.models.event import Event
from app.models.market import Market
from app.models.event_checker import EventChecker
from app.models.checker_config import CheckerConfig


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
        external_event_id: str,
        secret_name: str | None
    ) -> CheckerResult | None:
        """
        Execute a checker with its credentials.
        """
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
            return result
        except Exception as e:
            print(f"Error executing checker: {e}")
            return None
    
    async def _aggregate_checker_results(self, results: List[CheckerResult]) -> tuple[str, float]:
        """
        Aggregate checker results using quorum rules.
        Returns (state, confidence) tuple.
        """
        if not results:
            return ("LIVE", 0.0)
        
        min_confidence = config_service.get("min_feed_confidence", 0.8)
        
        # Count FINISHED results with sufficient confidence
        finished_count = sum(
            1 for r in results
            if r.state == "FINISHED" and r.confidence >= min_confidence
        )
        
        # Calculate average confidence
        avg_confidence = sum(r.confidence for r in results) / len(results) if results else 0.0
        
        # Quorum rule: >= 2 checkers with FINISHED and confidence >= min
        if finished_count >= 2:
            return ("FINISHED_CONFIRMED", avg_confidence)
        elif finished_count == 1:
            return ("FINISHED_UNCONFIRMED", avg_confidence)
        else:
            return ("LIVE", avg_confidence)
    
    async def _update_event_state(self, market_id, new_state: str, confidence: float, finished_at: datetime | None):
        """Update event state in memory and DB."""
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
                Market.status == "OPEN",
                Event.external_event_id.isnot(None)
            ).all()
            
            for market in markets:
                event = db.query(Event).filter(Event.market_id == market.id).first()
                if not event or not event.external_event_id:
                    continue
                
                # Determine category (this should come from market metadata)
                # For now, we'll need to add category to Market model or use a default
                category = "sports"  # TODO: Get from market metadata
                
                # Get active checkers for this category
                checker_configs = await self._get_active_checkers_for_category(category)
                
                if not checker_configs:
                    # No checkers active, keep state as LIVE
                    continue
                
                # Execute all checkers
                results: List[CheckerResult] = []
                for item in checker_configs:
                    checker = item["checker"]
                    config = item["config"]
                    
                    try:
                        # Get checker class from registry
                        checker_class = checker_registry.get(checker.implementation_key)
                        
                        # Execute checker
                        result = await self._execute_checker(
                            checker_class,
                            event.external_event_id,
                            config.secret_name
                        )
                        
                        if result:
                            # Apply weight
                            result.confidence *= config.weight
                            results.append(result)
                    except ValueError:
                        # Checker implementation not found
                        print(f"Checker implementation '{checker.implementation_key}' not found")
                        continue
                    except Exception as e:
                        print(f"Error executing checker {checker.implementation_key}: {e}")
                        continue
                
                # Aggregate results
                new_state, confidence = await self._aggregate_checker_results(results)
                
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
                
                # Update state
                await self._update_event_state(
                    market.id,
                    new_state,
                    confidence,
                    finished_at
                )
        finally:
            db.close()
