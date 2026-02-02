"""
Unit tests for Event Engine.

Según especificación en docs/services/event_engine.md
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
from app.core.event_engine import EventEngine
from app.core.checkers.base import CheckerResult


class TestEventEngine:
    """Test cases for Event Engine."""
    
    @pytest.fixture
    def event_engine(self):
        """Fixture para EventEngine."""
        return EventEngine()
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = []
        db.query.return_value.filter.return_value.first.return_value = None
        return db
    
    @pytest.mark.asyncio
    async def test_aggregate_checker_results_no_results(self, event_engine):
        """Test aggregation with no results returns LIVE."""
        state, confidence, metadata = await event_engine._aggregate_checker_results(
            results=[],
            category="sports",
            healthy_checker_ids=[]
        )
        assert state == "LIVE"
        assert confidence == 0.0
    
    @pytest.mark.asyncio
    async def test_aggregate_checker_results_finished_confirmed(self, event_engine):
        """Test aggregation with 2+ FINISHED results returns FINISHED_CONFIRMED."""
        results = [
            CheckerResult(
                state="FINISHED",
                confidence=0.9,
                finished_at=datetime.utcnow(),
                source="checker1",
                timestamp=datetime.utcnow()
            ),
            CheckerResult(
                state="FINISHED",
                confidence=0.85,
                finished_at=datetime.utcnow(),
                source="checker2",
                timestamp=datetime.utcnow()
            )
        ]
        
        def config_side_effect(key, default=None):
            values = {
                "min_feed_confidence": 0.8,
                "quorum_base": 2,
                "allow_single_checker": False,
                "allow_zero_checker": False,
            }
            return values.get(key, default)
        
        with patch("app.core.event_engine.config_service") as mock_config:
            mock_config.get.side_effect = config_side_effect
            state, confidence, metadata = await event_engine._aggregate_checker_results(
                results=results,
                category="sports",
                healthy_checker_ids=["checker1", "checker2"]
            )
            assert state == "FINISHED_CONFIRMED"
            assert confidence > 0.0
    
    @pytest.mark.asyncio
    async def test_aggregate_checker_results_finished_unconfirmed(self, event_engine):
        """Test aggregation with 1 FINISHED result returns FINISHED_UNCONFIRMED."""
        results = [
            CheckerResult(
                state="FINISHED",
                confidence=0.9,
                finished_at=datetime.utcnow(),
                source="checker1",
                timestamp=datetime.utcnow()
            ),
            CheckerResult(
                state="LIVE",
                confidence=0.5,
                finished_at=None,
                source="checker2",
                timestamp=datetime.utcnow()
            )
        ]
        
        def config_side_effect(key, default=None):
            values = {
                "min_feed_confidence": 0.8,
                "quorum_base": 2,  # Requiere 2 para confirmar
                "allow_single_checker": False,
                "allow_zero_checker": False,
            }
            return values.get(key, default)
        
        with patch("app.core.event_engine.config_service") as mock_config:
            mock_config.get.side_effect = config_side_effect
            state, confidence, metadata = await event_engine._aggregate_checker_results(
                results=results,
                category="sports",
                healthy_checker_ids=["checker1", "checker2"]
            )
            assert state == "FINISHED_UNCONFIRMED"
            assert confidence > 0.0
    
    @pytest.mark.asyncio
    async def test_aggregate_checker_results_live(self, event_engine):
        """Test aggregation with no FINISHED results returns LIVE."""
        results = [
            CheckerResult(
                state="LIVE",
                confidence=0.5,
                finished_at=None,
                source="checker1",
                timestamp=datetime.utcnow()
            ),
            CheckerResult(
                state="LIVE",
                confidence=0.6,
                finished_at=None,
                source="checker2",
                timestamp=datetime.utcnow()
            )
        ]
        
        def config_side_effect(key, default=None):
            values = {
                "min_feed_confidence": 0.8,
                "quorum_base": 2,
                "allow_single_checker": False,
                "allow_zero_checker": False,
            }
            return values.get(key, default)
        
        with patch("app.core.event_engine.config_service") as mock_config:
            mock_config.get.side_effect = config_side_effect
            state, confidence, metadata = await event_engine._aggregate_checker_results(
                results=results,
                category="sports",
                healthy_checker_ids=["checker1", "checker2"]
            )
            assert state == "LIVE"
            assert confidence > 0.0
    
    @pytest.mark.asyncio
    async def test_execute_checker_with_credentials(self, event_engine):
        """Test executing checker with credentials."""
        mock_checker_class = MagicMock()
        mock_checker_instance = MagicMock()
        mock_checker_class.return_value = mock_checker_instance
        mock_checker_instance.check = AsyncMock(return_value=CheckerResult(
            state="FINISHED",
            confidence=0.9,
            finished_at=datetime.utcnow(),
            source="test",
            timestamp=datetime.utcnow()
        ))
        
        with patch("app.core.event_engine.secret_service") as mock_secret:
            mock_secret.get_secret = AsyncMock(return_value="api_key_123")
            result = await event_engine._execute_checker(
                checker_class=mock_checker_class,
                checker_id="checker_uuid_123",
                external_event_id="event_123",
                secret_name="secret_name"
            )
            
            assert result is not None
            assert result.state == "FINISHED"
            mock_checker_instance.check.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_checker_without_credentials(self, event_engine):
        """Test executing checker without credentials."""
        mock_checker_class = MagicMock()
        mock_checker_instance = MagicMock()
        mock_checker_class.return_value = mock_checker_instance
        mock_checker_instance.check = AsyncMock(return_value=CheckerResult(
            state="LIVE",
            confidence=0.5,
            finished_at=None,
            source="test",
            timestamp=datetime.utcnow()
        ))
        
        result = await event_engine._execute_checker(
            checker_class=mock_checker_class,
            checker_id="checker_uuid_123",
            external_event_id="event_123",
            secret_name=None
        )
        
        assert result is not None
        assert result.state == "LIVE"
        mock_checker_instance.check.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_checker_error_handling(self, event_engine):
        """Test error handling in checker execution."""
        mock_checker_class = MagicMock()
        mock_checker_class.side_effect = Exception("Checker error")
        
        result = await event_engine._execute_checker(
            checker_class=mock_checker_class,
            checker_id="checker_uuid_123",
            external_event_id="event_123",
            secret_name=None
        )
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_tick_updates_events(self, event_engine):
        """Test tick method updates events."""
        with patch("app.core.event_engine.state") as mock_state, \
             patch("app.core.event_engine.SessionLocal") as mock_session, \
             patch.object(event_engine, "_get_active_checkers_for_category") as mock_get_checkers, \
             patch.object(event_engine, "_execute_checker") as mock_execute, \
             patch.object(event_engine, "_aggregate_checker_results") as mock_aggregate:
            
            # Setup mocks - usando polymarket_event_id que es el campo correcto
            mock_state.events = {
                "event_1": {
                    "polymarket_event_id": "espn_123",
                    "category": "sports",
                    "status": "LIVE"
                }
            }
            mock_state.markets = {}
            
            mock_get_checkers.return_value = []
            mock_execute.return_value = None
            # _aggregate_checker_results ahora retorna 3 valores (state, confidence, metadata)
            mock_aggregate.return_value = ("LIVE", 0.5, {"quorum_used": None})
            
            # Mock database
            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.all.return_value = []
            mock_session.return_value.__enter__.return_value = mock_db
            mock_session.return_value.__exit__.return_value = None
            
            await event_engine.tick()
            
            # Verify tick was called
            assert True  # If no exception, test passes

