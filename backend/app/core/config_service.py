"""
System configuration service - loads and manages configuration from DB with hot reload.
"""
import asyncio
import logging
import threading
import time
from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy.exc import OperationalError
from app.database import SessionLocal
from app.models.system_config import SystemConfig
from app.core.state import RiskConfig as LegacyRiskConfig
import json

logger = logging.getLogger(__name__)


class SystemConfigService:
    """
    Service for loading and managing system configuration from system_config table.
    Features:
    - Hot reload: Polls DB every 5-10 seconds for changes
    - Component-specific methods: get_strategy_config(), get_risk_config(), etc.
    - Validation: Checks is_readonly and requires_confirmation
    - Execution mode support: DRY_RUN, PAPER, LIVE
    """
    
    def __init__(self, hot_reload_interval_seconds: int = 5):
        """
        Initialize config service.
        
        Args:
            hot_reload_interval_seconds: How often to poll DB for changes (default: 5)
        """
        self._cache: Dict[str, Any] = {}
        self._config_metadata: Dict[str, Dict[str, Any]] = {}  # key -> {is_readonly, requires_confirmation, etc.}
        self._risk_config: Optional[LegacyRiskConfig] = None
        self._strategy_config: Optional[Any] = None  # StrategyConfig (lazy import)
        self._risk_engine_config: Optional[Any] = None  # RiskEngineConfig (lazy import)
        self._last_reload: Optional[datetime] = None
        self._hot_reload_interval = hot_reload_interval_seconds
        self._hot_reload_active = False
        self._hot_reload_thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()  # Changed to RLock to allow reentrant locking
        self._logged_table_missing = False  # Log "no such table" only once
    
    def _parse_value(self, config: SystemConfig) -> Any:
        """Parse configuration value based on value_type."""
        if config.value_type == "float":
            return float(config.value)
        elif config.value_type == "int":
            return int(config.value)
        elif config.value_type == "bool":
            return config.value.lower() in ("true", "1", "yes")
        elif config.value_type == "json":
            try:
                return json.loads(config.value)
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON in config {config.key}: {config.value}")
                return config.value
        else:  # string
            return config.value
    
    def load_from_db(self):
        """Load all configuration from database."""
        with self._lock:
            db = SessionLocal()
            try:
                # Test connection first with a simple query
                try:
                    from sqlalchemy import text
                    db.execute(text("SELECT 1"))
                    db.commit()
                except Exception as conn_error:
                    logger.warning(f"Database connection test failed: {conn_error}. Using default configuration.")
                    db.rollback()
                    db.close()
                    return
                
                configs = db.query(SystemConfig).all()
                new_cache: Dict[str, Any] = {}
                new_metadata: Dict[str, Dict[str, Any]] = {}
                
                for config in configs:
                    value = self._parse_value(config)
                    new_cache[config.key] = value
                    new_metadata[config.key] = {
                        "is_readonly": config.is_readonly,
                        "requires_confirmation": config.requires_confirmation,
                        "category": config.category,
                        "execution_mode": config.execution_mode,
                        "min_value": config.min_value,
                        "max_value": config.max_value,
                        "validation_rule": config.validation_rule,
                        "updated_at": config.updated_at,
                    }
                
                self._cache = new_cache
                self._config_metadata = new_metadata
                self._last_reload = datetime.utcnow()
                
                # Rebuild component configs
                self._rebuild_component_configs()
                
                logger.debug(f"Loaded {len(self._cache)} configuration entries from DB")
                
            except OperationalError as e:
                # Tabla system_config no existe: migraciones no aplicadas o DATABASE_URL apunta a SQLite vacía
                if "no such table" in str(e).lower() and not self._logged_table_missing:
                    self._logged_table_missing = True
                    logger.warning(
                        "system_config table not found. Using default config. "
                        "Fix: set DATABASE_URL to PostgreSQL (e.g. in Railway) and redeploy, or run: alembic upgrade head"
                    )
                # Don't raise - allow server to start with default config
            except Exception as e:
                logger.error(f"Error loading configuration from DB: {e}", exc_info=True)
                # Don't raise - allow server to start with default config
            finally:
                db.close()
    
    def _rebuild_component_configs(self):
        """Rebuild component-specific config objects from cache."""
        # Build RiskConfig (legacy, from state.py)
        self._risk_config = LegacyRiskConfig()
        self._risk_config.max_exposure_per_market = self._cache.get("max_exposure_per_market", 50000.0)
        self._risk_config.max_global_exposure = self._cache.get("max_global_exposure", 500000.0)
        self._risk_config.max_markets_active = int(self._cache.get("max_markets_active", 30))
        self._risk_config.min_entry_price = self._cache.get("min_entry_price", 0.98)
        self._risk_config.target_margin = self._cache.get("target_margin", 0.001)
        self._risk_config.min_candidate_price = self._cache.get("min_candidate_price", 0.97)
        self._risk_config.safety_tick = self._cache.get("safety_tick", 0.0001)
        self._risk_config.max_single_order_size = self._cache.get("max_single_order_size", 10000.0)
        self._risk_config.tick_seconds = self._cache.get("tick_seconds", 1.0)
        self._risk_config.scan_interval_seconds = self._cache.get("scan_interval_seconds", 30.0)
        self._risk_config.min_feed_confidence = self._cache.get("min_feed_confidence", 0.8)
        self._risk_config.checker_timeout_seconds = self._cache.get("checker_timeout_seconds", 5.0)
        
        # Build StrategyConfig (lazy import to avoid circular dependency)
        from app.core.strategy.models import StrategyConfig
        self._strategy_config = StrategyConfig(
            min_entry_price=self._cache.get("min_entry_price", 0.97),
            max_entry_spread=self._cache.get("max_entry_spread", 0.02),
            safety_tick=self._cache.get("safety_tick", 0.001),
            target_edge=self._cache.get("target_margin", 0.01),
            max_order_size=self._cache.get("max_order_size", 5000.0),
            max_exposure_per_market=self._cache.get("max_exposure_per_market", 10000.0),
            max_global_exposure=self._cache.get("max_global_exposure", 200000.0),
            latency_mode=self._cache.get("latency_mode", "GREEN"),
            aggressive_mode=self._cache.get("aggressive_mode", False),
            min_liquidity_required=self._cache.get("min_liquidity_required", 1000.0),
            bet_size_mode=self._cache.get("bet_size_mode", "fixed_range"),
            bet_size_percentage=self._cache.get("bet_size_percentage"),
            bet_size_min=self._cache.get("bet_size_min"),
            bet_size_max=self._cache.get("bet_size_max"),
        )
        
        # Build RiskEngineConfig (lazy import to avoid circular dependency)
        from app.core.risk_engine.models import RiskConfig as RiskEngineConfig
        self._risk_engine_config = RiskEngineConfig(
            max_market_exposure=self._cache.get("max_market_exposure", 10000.0),
            max_global_exposure=self._cache.get("max_global_exposure", 200000.0),
            max_markets_active=int(self._cache.get("max_markets_active", 10)),
            max_order_size=self._cache.get("max_order_size", 5000.0),
            min_order_size=self._cache.get("min_order_size", 100.0),
            latency_fail_mode=self._cache.get("latency_fail_mode", "strict"),
            reduce_size_in_yellow=self._cache.get("reduce_size_in_yellow", True),
            yellow_size_factor=self._cache.get("yellow_size_factor", 0.5),
            cancel_on_red=self._cache.get("cancel_on_red", True),
            exposure_method=self._cache.get("exposure_method", "notional"),
            max_price_swing_pct=self._cache.get("max_price_swing_pct", 0.05),
            max_swing_time_seconds=self._cache.get("max_swing_time_seconds", 10.0),
            min_realistic_spread=self._cache.get("min_realistic_spread", 0.001),
        )
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value by key.
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        # #region agent log
        import json
        with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"config_service.py:166","message":"get() ENTRY","data":{"key":key},"timestamp":int(__import__('time').time()*1000)})+"\n")
        # #endregion
        logger.debug(f"get() - Adquiriendo lock para key: {key}")
        # #region agent log
        with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"config_service.py:177","message":"BEFORE acquiring lock in get()","data":{"key":key},"timestamp":int(__import__('time').time()*1000)})+"\n")
        # #endregion
        with self._lock:
            # #region agent log
            with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"config_service.py:178","message":"AFTER acquiring lock in get()","data":{"key":key},"timestamp":int(__import__('time').time()*1000)})+"\n")
            # #endregion
            result = self._cache.get(key, default)
            # #region agent log
            with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"config_service.py:179","message":"get() EXIT","data":{"key":key,"has_value":result is not None},"timestamp":int(__import__('time').time()*1000)})+"\n")
            # #endregion
            return result
    
    def get_metadata(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a configuration key (is_readonly, requires_confirmation, etc.).
        
        Args:
            key: Configuration key
            
        Returns:
            Metadata dict or None if key not found
        """
        with self._lock:
            return self._config_metadata.get(key)
    
    def is_readonly(self, key: str) -> bool:
        """Check if a configuration key is readonly."""
        metadata = self.get_metadata(key)
        return metadata.get("is_readonly", False) if metadata else False
    
    def requires_confirmation(self, key: str) -> bool:
        """Check if a configuration key requires confirmation before changing."""
        metadata = self.get_metadata(key)
        return metadata.get("requires_confirmation", False) if metadata else False
    
    def get_execution_mode(self) -> str:
        """
        Get current execution mode (DRY_RUN, PAPER, LIVE).
        
        Returns:
            Execution mode string, default "DRY_RUN"
        """
        # #region agent log
        import json
        with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"config_service.py:203","message":"get_execution_mode ENTRY","data":{},"timestamp":int(__import__('time').time()*1000)})+"\n")
        # #endregion
        result = self.get("execution_mode", "DRY_RUN")
        # #region agent log
        with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"config_service.py:210","message":"get_execution_mode EXIT","data":{"result":result},"timestamp":int(__import__('time').time()*1000)})+"\n")
        # #endregion
        return result
    
    def get_strategy_config(self):
        """
        Get Strategy configuration object.
        
        Returns:
            StrategyConfig with all strategy parameters
        """
        with self._lock:
            if self._strategy_config is None:
                self.load_from_db()
            return self._strategy_config
    
    def get_risk_config(self) -> LegacyRiskConfig:
        """
        Get Risk configuration object (legacy, from state.py).
        
        Returns:
            LegacyRiskConfig with all risk parameters
        """
        with self._lock:
            if self._risk_config is None:
                self.load_from_db()
            return self._risk_config
    
    def get_risk_engine_config(self):
        """
        Get Risk Engine configuration object.
        
        Returns:
            RiskEngineConfig with all risk engine parameters
        """
        with self._lock:
            if self._risk_engine_config is None:
                self.load_from_db()
            return self._risk_engine_config
    
    def get_scanner_config(self) -> Dict[str, Any]:
        """
        Get Scanner configuration as dict.
        
        Returns:
            Dict with scanner parameters
        """
        return {
            "min_price_threshold": self.get("min_price_threshold", 0.97),
            "allowed_categories": self.get("allowed_categories", ["sports"]),
            "allowed_subcategories": self.get("allowed_subcategories", []),
            "scan_interval_seconds": self.get("scan_interval_seconds", 30.0),
            "min_volume_24h": self.get("min_volume_24h", 0.0),
            "min_liquidity": self.get("min_liquidity", 0.0),
        }
    
    def get_event_engine_config(self) -> Dict[str, Any]:
        """
        Get Event Engine configuration as dict.
        
        Returns:
            Dict with event engine parameters
        """
        return {
            "min_feed_confidence": self.get("min_feed_confidence", 0.8),
            "quorum_base": self.get("quorum_base", 2),
            "allow_single_checker": self.get("allow_single_checker", False),
            "allow_zero_checker": self.get("allow_zero_checker", False),
            "checker_timeout_seconds": self.get("checker_timeout_seconds", 5.0),
            "checker_health_window_seconds": self.get("checker_health_window_seconds", 3600),
            "checker_max_failures": self.get("checker_max_failures", 5),
            "default_category": self.get("default_category", "sports"),
        }
    
    def get_execution_config(self) -> Dict[str, Any]:
        """
        Get Execution Engine configuration as dict.
        
        Returns:
            Dict with execution parameters
        """
        # #region agent log
        import json
        with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"config_service.py:282","message":"get_execution_config ENTRY","data":{},"timestamp":int(__import__('time').time()*1000)})+"\n")
        # #endregion
        logger.info("get_execution_config - Adquiriendo lock...")
        # #region agent log
        with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"config_service.py:289","message":"BEFORE acquiring lock","data":{},"timestamp":int(__import__('time').time()*1000)})+"\n")
        # #endregion
        with self._lock:
            # #region agent log
            with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"config_service.py:290","message":"AFTER acquiring lock","data":{},"timestamp":int(__import__('time').time()*1000)})+"\n")
            # #endregion
            logger.info("get_execution_config - Lock adquirido, llamando get_execution_mode()...")
            # #region agent log
            with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"config_service.py:291","message":"BEFORE get_execution_mode","data":{},"timestamp":int(__import__('time').time()*1000)})+"\n")
            # #endregion
            execution_mode = self.get_execution_mode()
            # #region agent log
            with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"config_service.py:293","message":"AFTER get_execution_mode","data":{"execution_mode":execution_mode},"timestamp":int(__import__('time').time()*1000)})+"\n")
            # #endregion
            logger.info(f"get_execution_config - Execution mode obtenido: {execution_mode}")
            result = {
                "execution_mode": execution_mode,
                "max_retries": self.get("execution_max_retries", 3),
                "retry_delay_seconds": self.get("execution_retry_delay_seconds", 1.0),
                "order_timeout_seconds": self.get("order_timeout_seconds", 3600.0),
                "fill_check_interval_seconds": self.get("poll_interval_seconds", 5.0),
                "http_timeout_seconds": self.get("execution_http_timeout_seconds", 30.0),
                "order_ttl_seconds": int(self.get("order_timeout_seconds", 3600.0)),
            }
            # #region agent log
            with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"config_service.py:301","message":"get_execution_config EXIT","data":{"result_keys":list(result.keys())},"timestamp":int(__import__('time').time()*1000)})+"\n")
            # #endregion
            return result
    
    def get_by_category(self, category: str) -> Dict[str, Any]:
        """
        Get all configuration keys for a specific category.
        
        Args:
            category: Category name (strategy, risk, scanner, event_engine, execution)
            
        Returns:
            Dict of key -> value for that category
        """
        with self._lock:
            result = {}
            for key, metadata in self._config_metadata.items():
                if metadata.get("category") == category:
                    result[key] = self._cache.get(key)
            return result
    
    def start_hot_reload(self):
        """Start hot reload thread that polls DB for changes."""
        if self._hot_reload_active:
            logger.warning("Hot reload already active")
            return
        
        self._hot_reload_active = True
        self._hot_reload_thread = threading.Thread(
            target=self._hot_reload_loop,
            daemon=True,
            name="ConfigServiceHotReload"
        )
        self._hot_reload_thread.start()
        logger.info(f"Started hot reload (interval: {self._hot_reload_interval}s)")
    
    def stop_hot_reload(self):
        """Stop hot reload thread."""
        self._hot_reload_active = False
        if self._hot_reload_thread:
            self._hot_reload_thread.join(timeout=2.0)
        logger.info("Stopped hot reload")
    
    def _hot_reload_loop(self):
        """Background thread that polls DB for configuration changes."""
        while self._hot_reload_active:
            try:
                time.sleep(self._hot_reload_interval)
                if self._hot_reload_active:
                    self.load_from_db()
            except Exception as e:
                logger.error(f"Error in hot reload loop: {e}", exc_info=True)
    
    def invalidate_cache(self, key: Optional[str] = None):
        """
        Invalidate cache for a specific key or all keys.
        If key is None, reloads all configuration.
        
        Note: Hot reload will automatically refresh, but this can be called
        manually for immediate refresh.
        """
        self.load_from_db()


# Global config service instance
config_service = SystemConfigService()

