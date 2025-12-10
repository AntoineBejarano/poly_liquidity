"""
System configuration service - loads and manages configuration from DB.
"""
from typing import Optional, Dict, Any
from app.database import SessionLocal
from app.models.system_config import SystemConfig
from app.core.state import RiskConfig
import json


class SystemConfigService:
    """
    Service for loading and managing system configuration from system_config table.
    Loads all configuration on startup, caches in memory for fast access.
    Invalidates cache when updated from frontend.
    """
    
    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._risk_config: Optional[RiskConfig] = None
    
    def load_from_db(self):
        """Load all configuration from database."""
        db = SessionLocal()
        try:
            configs = db.query(SystemConfig).all()
            self._cache = {}
            
            for config in configs:
                # Parse value based on type
                if config.value_type == "float":
                    value = float(config.value)
                elif config.value_type == "int":
                    value = int(config.value)
                elif config.value_type == "bool":
                    value = config.value.lower() in ("true", "1", "yes")
                else:  # string
                    value = config.value
                
                self._cache[config.key] = value
            
            # Build RiskConfig from cache
            self._risk_config = RiskConfig()
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
            
        finally:
            db.close()
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by key."""
        return self._cache.get(key, default)
    
    def get_risk_config(self) -> RiskConfig:
        """Get the risk configuration object."""
        if self._risk_config is None:
            self.load_from_db()
        return self._risk_config
    
    def invalidate_cache(self, key: Optional[str] = None):
        """
        Invalidate cache for a specific key or all keys.
        If key is None, reloads all configuration.
        """
        if key is None:
            self.load_from_db()
        else:
            # Reload specific key from DB
            db = SessionLocal()
            try:
                config = db.query(SystemConfig).filter(SystemConfig.key == key).first()
                if config:
                    if config.value_type == "float":
                        value = float(config.value)
                    elif config.value_type == "int":
                        value = int(config.value)
                    elif config.value_type == "bool":
                        value = config.value.lower() in ("true", "1", "yes")
                    else:
                        value = config.value
                    self._cache[key] = value
                    
                    # Rebuild RiskConfig if it's a risk config key
                    if config.category == "risk" or config.category == "system" or config.category == "scanner" or config.category == "event_engine":
                        self.load_from_db()  # Reload all to rebuild RiskConfig
            finally:
                db.close()


# Global config service instance
config_service = SystemConfigService()

