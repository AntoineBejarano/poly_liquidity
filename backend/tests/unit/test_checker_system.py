"""
Unit tests for Checker System.
"""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock
from app.core.checkers.base import BaseChecker, CheckerResult
from app.core.checkers.registry import CheckerRegistry, checker_registry
from app.core.checkers.runner import CheckerRunner
from app.core.checkers.implementations.mock_checker import MockChecker
from app.core.checkers.implementations.sports_checker import SportsChecker
from app.core.checkers.implementations.crypto_checker import CryptoChecker


@pytest.fixture
def checker_registry_instance():
    """Fixture para CheckerRegistry limpio."""
    return CheckerRegistry()


@pytest.fixture
def checker_runner():
    """Fixture para CheckerRunner."""
    return CheckerRunner()


@pytest.fixture
def mock_checker_instance():
    """Fixture para instancia de MockChecker."""
    return MockChecker()


@pytest.fixture
def sports_checker_instance():
    """Fixture para instancia de SportsChecker."""
    return SportsChecker()


class TestCheckerResult:
    """Tests para CheckerResult."""
    
    def test_checker_result_creation(self):
        """Test creación de CheckerResult."""
        result = CheckerResult(
            state="LIVE",
            confidence=0.9,
            source="test_checker",
            latency_ms=100.0
        )
        
        assert result.state == "LIVE"
        assert result.confidence == 0.9
        assert result.source == "test_checker"
        assert result.latency_ms == 100.0
        assert result.error is None
    
    def test_checker_result_with_error(self):
        """Test CheckerResult con error."""
        result = CheckerResult(
            state="UNKNOWN",
            confidence=0.0,
            source="test_checker",
            error="timeout",
            latency_ms=5000.0
        )
        
        assert result.state == "UNKNOWN"
        assert result.confidence == 0.0
        assert result.error == "timeout"
    
    def test_checker_result_finished(self):
        """Test CheckerResult con evento finalizado."""
        finished_at = datetime.utcnow()
        result = CheckerResult(
            state="FINISHED",
            confidence=0.95,
            source="test_checker",
            finished_at=finished_at
        )
        
        assert result.state == "FINISHED"
        assert result.finished_at == finished_at


class TestBaseChecker:
    """Tests para BaseChecker."""
    
    def test_base_checker_properties(self):
        """Test que BaseChecker tiene propiedades correctas."""
        # BaseChecker es abstracto, no se puede instanciar directamente
        # Pero podemos verificar que las propiedades están definidas
        assert hasattr(BaseChecker, 'name')
        assert hasattr(BaseChecker, 'event_types')
        assert hasattr(BaseChecker, 'weight')
        assert hasattr(BaseChecker, 'timeout_ms')
        assert hasattr(BaseChecker, 'max_retries')
        assert hasattr(BaseChecker, 'check')


class TestCheckerRegistry:
    """Tests para CheckerRegistry."""
    
    def test_register_checker(self, checker_registry_instance):
        """Test registro de checker."""
        checker_registry_instance.register("test_checker", MockChecker)
        
        assert "test_checker" in checker_registry_instance._checkers
        assert checker_registry_instance._checkers["test_checker"] == MockChecker
    
    def test_get_checker(self, checker_registry_instance):
        """Test obtención de checker."""
        checker_registry_instance.register("test_checker", MockChecker)
        
        checker_class = checker_registry_instance.get("test_checker")
        assert checker_class == MockChecker
    
    def test_get_checker_not_found(self, checker_registry_instance):
        """Test obtención de checker no registrado."""
        with pytest.raises(ValueError, match="not found"):
            checker_registry_instance.get("nonexistent")
    
    def test_list_all_checkers(self, checker_registry_instance):
        """Test listado de todos los checkers."""
        checker_registry_instance.register("checker1", MockChecker)
        checker_registry_instance.register("checker2", SportsChecker)
        
        all_checkers = checker_registry_instance.list_all()
        assert len(all_checkers) == 2
        assert "checker1" in all_checkers
        assert "checker2" in all_checkers
    
    def test_list_by_event_type(self, checker_registry_instance):
        """Test listado por tipo de evento."""
        checker_registry_instance.register("sports_checker", SportsChecker)
        checker_registry_instance.register("crypto_checker", CryptoChecker)
        
        sports_checkers = checker_registry_instance.list_by_event_type("sports")
        assert SportsChecker in sports_checkers
        assert CryptoChecker not in sports_checkers
        
        crypto_checkers = checker_registry_instance.list_by_event_type("crypto")
        assert CryptoChecker in crypto_checkers


class TestMockChecker:
    """Tests para MockChecker."""
    
    @pytest.mark.asyncio
    async def test_mock_checker_returns_live(self, mock_checker_instance):
        """Test que MockChecker retorna LIVE."""
        result = await mock_checker_instance.check("test_event_id")
        
        assert result.state == "LIVE"
        assert result.confidence == 0.5
        assert result.source == "mock_checker"
        assert result.error is None
    
    def test_mock_checker_properties(self, mock_checker_instance):
        """Test propiedades de MockChecker."""
        assert mock_checker_instance.name == "mock_checker"
        assert "sports" in mock_checker_instance.event_types
        assert mock_checker_instance.weight == 0.5
        assert mock_checker_instance.timeout_ms == 1000
        assert mock_checker_instance.max_retries == 0


class TestSportsChecker:
    """Tests para SportsChecker."""
    
    def test_sports_checker_properties(self, sports_checker_instance):
        """Test propiedades de SportsChecker."""
        assert sports_checker_instance.name == "sports_checker"
        assert "sports" in sports_checker_instance.event_types
        assert sports_checker_instance.weight == 1.0
        assert sports_checker_instance.timeout_ms == 5000
        assert sports_checker_instance.max_retries == 2
    
    @pytest.mark.asyncio
    async def test_sports_checker_no_credentials(self, sports_checker_instance):
        """Test SportsChecker sin credenciales."""
        result = await sports_checker_instance.check("sports:nba:12345", credentials=None)
        
        assert result.state == "UNKNOWN"
        assert result.confidence == 0.0
        assert result.error == "authentication_error"
    
    @pytest.mark.asyncio
    async def test_sports_checker_with_credentials(self, sports_checker_instance):
        """Test SportsChecker con credenciales."""
        credentials = {"api_key": "test_key", "api_url": "https://api.test.com"}
        result = await sports_checker_instance.check("sports:nba:12345", credentials=credentials)
        
        # Por ahora retorna LIVE como placeholder
        assert result.state == "LIVE"
        assert result.confidence == 0.5
        assert result.source == "sports_checker"
        assert "external_event_id" in result.raw_payload


class TestCheckerRunner:
    """Tests para CheckerRunner."""
    
    @pytest.mark.asyncio
    async def test_run_checker_success(self, checker_runner, mock_checker_instance):
        """Test ejecución exitosa de checker."""
        result = await checker_runner.run_checker(
            mock_checker_instance,
            "test_event_id"
        )
        
        assert result.state == "LIVE"
        assert result.source == "mock_checker"
        assert result.error is None
    
    @pytest.mark.asyncio
    async def test_run_checker_timeout(self, checker_runner):
        """Test checker con timeout."""
        import asyncio
        
        # Crear checker mock que siempre hace timeout
        class TimeoutChecker(BaseChecker):
            name = "timeout_checker"
            event_types = ["test"]
            weight = 1.0
            timeout_ms = 100  # Timeout muy corto
            max_retries = 0
            
            async def check(self, external_event_id: str, credentials=None):
                await asyncio.sleep(1.0)  # Más largo que timeout
                return CheckerResult(
                    state="LIVE",
                    confidence=1.0,
                    source=self.name
                )
        
        timeout_checker = TimeoutChecker()
        result = await checker_runner.run_checker(timeout_checker, "test_event_id")
        
        assert result.state == "UNKNOWN"
        assert result.error == "timeout"
    
    @pytest.mark.asyncio
    async def test_run_checkers_parallel(self, checker_runner):
        """Test ejecución paralela de múltiples checkers."""
        checker1 = MockChecker()
        checker2 = MockChecker()
        
        results = await checker_runner.run_checkers_parallel(
            [checker1, checker2],
            "test_event_id"
        )
        
        assert len(results) == 2
        assert all(r.state == "LIVE" for r in results)
        assert all(r.source == "mock_checker" for r in results)
    
    @pytest.mark.asyncio
    async def test_run_checker_with_retries(self, checker_runner):
        """Test checker con retries."""
        attempt_count = []
        
        class RetryChecker(BaseChecker):
            name = "retry_checker"
            event_types = ["test"]
            weight = 1.0
            timeout_ms = 1000
            max_retries = 2
            
            async def check(self, external_event_id: str, credentials=None):
                attempt_count.append(1)
                if len(attempt_count) < 3:
                    raise Exception("Simulated error")
                return CheckerResult(
                    state="LIVE",
                    confidence=1.0,
                    source=self.name
                )
        
        retry_checker = RetryChecker()
        result = await checker_runner.run_checker(retry_checker, "test_event_id")
        
        # Debería haber intentado 3 veces (1 inicial + 2 retries)
        assert len(attempt_count) == 3
        assert result.state == "LIVE"


class TestCheckerIntegration:
    """Tests de integración del Checker System."""
    
    def test_checker_registry_global(self):
        """Test que el registro global funciona."""
        # Verificar que los checkers están registrados
        assert "mock_checker" in checker_registry.list_all()
        assert "sports_checker" in checker_registry.list_all()
        assert "crypto_checker" in checker_registry.list_all()
    
    @pytest.mark.asyncio
    async def test_full_checker_flow(self):
        """Test flujo completo: registry -> runner -> checker."""
        # Obtener checker del registry
        checker_class = checker_registry.get("mock_checker")
        checker_instance = checker_class()
        
        # Ejecutar con runner
        runner = CheckerRunner()
        result = await runner.run_checker(checker_instance, "test_event_id")
        
        assert result.state == "LIVE"
        assert result.source == "mock_checker"
