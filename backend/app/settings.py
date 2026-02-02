"""
Configuration settings using pydantic-settings.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Stack Auth (required for production, optional for development)
    stack_secret_server_key: str = "dev-secret-key-change-in-production"
    
    # Database (required for production, optional for development)
    database_url: str = "sqlite:///./poly_liquidity.db"
    data_api_endpoint: Optional[str] = None
    
    # Polymarket - Credenciales esenciales
    # PRIVATE_KEY: Clave privada de wallet (hex string con "0x")
    private_key: Optional[str] = None
    
    # FUNDER_ADDRESS o POLYMARKET_PROXY_ADDRESS: Dirección de proxy wallet (visible en polymarket.com/settings)
    funder_address: Optional[str] = None
    polymarket_proxy_address: Optional[str] = None
    
    # Credenciales API L2 (Polymarket) - OPCIONALES
    # Estas se generan automáticamente si no se proporcionan
    # Solo necesarias si quieres usar credenciales pre-generadas
    polymarket_api_key: Optional[str] = None
    polymarket_api_secret: Optional[str] = None
    polymarket_api_passphrase: Optional[str] = None
    
    # Configuración de red
    chain_id: int = 137  # Polygon mainnet
    rpc_url: Optional[str] = None  # URL de proveedor RPC de Polygon
    
    # Builders (opcional)
    builder_api_key: Optional[str] = None
    builder_secret: Optional[str] = None
    builder_passphrase: Optional[str] = None
    
    # URLs de API
    polymarket_api_url: str = "https://api.polymarket.com"
    polymarket_data_api_url: str = "https://data-api.polymarket.com"
    polymarket_gamma_api_url: str = "https://gamma-api.polymarket.com"  # Para obtener mercados/eventos
    polymarket_trading_api_url: str = "https://clob.polymarket.com"
    
    # Server
    environment: str = "development"
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: str = "http://localhost:3000"
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    
    # Feature flags
    use_graph_strategies: bool = False  # Activar sistema de estrategias basado en grafos
    scenario_runner_enabled: bool = False  # Activar scenario runner (solo para staging/internal, NO en prod)
    
    # Wallet - clave para cifrado de claves privadas en DB (requerida en producción)
    # Generar con: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    wallet_encryption_key: Optional[str] = None

    # Redis - Opcional, para cache distribuido
    # Soporta tanto REST API (Upstash) como TCP nativo
    # Para TCP: redis://default:password@host:port
    # Para REST API (legacy): usar upstash_redis_rest_url y upstash_redis_rest_token
    redis_url: Optional[str] = None  # URL de conexión TCP (preferido)
    upstash_redis_rest_url: Optional[str] = None  # Legacy: REST API URL
    upstash_redis_rest_token: Optional[str] = None  # Legacy: REST API Token
    
    # Latency Monitor Configuration
    latency_cache_ttl_seconds: int = 30  # TTL del cache fresco (SWR: retorna inmediatamente)
    latency_stale_ttl_seconds: int = 60  # TTL del cache stale (SWR: retorna stale + revalida en background)
    latency_lock_ttl_seconds: int = 10  # TTL del lock distribuido (anti-thundering herd)
    latency_min_interval_seconds: int = 10  # Intervalo mínimo entre requests al mismo endpoint
    latency_backoff_max_seconds: int = 60  # Backoff máximo en segundos
    latency_collector_interval_seconds: int = 60  # Intervalo para MetricsCollector
    
    # Latency Thresholds (ms)
    latency_backend_green_threshold: int = 100
    latency_backend_yellow_threshold: int = 200
    latency_polymarket_data_green_threshold: int = 150
    latency_polymarket_data_yellow_threshold: int = 300
    latency_polymarket_trading_green_threshold: int = 150
    latency_polymarket_trading_yellow_threshold: int = 300
    latency_execution_green_threshold: int = 250
    latency_execution_yellow_threshold: int = 500


# Global settings instance
settings = Settings()

