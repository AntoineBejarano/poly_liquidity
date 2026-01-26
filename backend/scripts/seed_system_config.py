"""
Script para poblar system_config con valores iniciales.
Ejecutar: python -m scripts.seed_system_config
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.system_config import SystemConfig
from sqlalchemy.exc import IntegrityError

def seed_system_config():
    """Poblar system_config con valores iniciales."""
    db = SessionLocal()
    
    try:
        # Lista de configuraciones iniciales
        configs = [
            # ===== SISTEMA =====
            {
                "key": "execution_mode",
                "value": "DRY_RUN",
                "value_type": "string",
                "category": "system",
                "description": "Modo de ejecución: DRY_RUN, PAPER, LIVE",
                "is_readonly": False,
                "requires_confirmation": True,
                "min_value": None,
                "max_value": None,
            },
            
            # ===== EVENT ENGINE =====
            {
                "key": "quorum_base",
                "value": "2",
                "value_type": "int",
                "category": "event_engine",
                "description": "Quorum base para confirmación de eventos",
                "is_readonly": False,
                "requires_confirmation": True,
                "min_value": "1",
                "max_value": "10",
            },
            {
                "key": "allow_single_checker",
                "value": "false",
                "value_type": "bool",
                "category": "event_engine",
                "description": "Permitir quorum de 1 si solo hay 1 checker disponible",
                "is_readonly": False,
                "requires_confirmation": False,
                "min_value": None,
                "max_value": None,
            },
            {
                "key": "allow_zero_checker",
                "value": "false",
                "value_type": "bool",
                "category": "event_engine",
                "description": "Permitir sistema operativo sin checkers (sin trading). Sistema sigue funcionando pero NUNCA confirma FINISHED y NUNCA hace trading",
                "is_readonly": False,
                "requires_confirmation": True,
                "min_value": None,
                "max_value": None,
            },
            {
                "key": "min_feed_confidence",
                "value": "0.8",
                "value_type": "float",
                "category": "event_engine",
                "description": "Confianza mínima requerida de checkers",
                "is_readonly": False,
                "requires_confirmation": True,
                "min_value": "0.0",
                "max_value": "1.0",
            },
            {
                "key": "checker_timeout_seconds",
                "value": "5.0",
                "value_type": "float",
                "category": "event_engine",
                "description": "Timeout en segundos para checkers",
                "is_readonly": False,
                "requires_confirmation": False,
                "min_value": "1.0",
                "max_value": "60.0",
            },
            {
                "key": "checker_health_window_seconds",
                "value": "300",
                "value_type": "int",
                "category": "event_engine",
                "description": "Ventana de tiempo en segundos para considerar checker saludable",
                "is_readonly": False,
                "requires_confirmation": False,
                "min_value": "60",
                "max_value": "3600",
            },
            {
                "key": "checker_max_failures",
                "value": "3",
                "value_type": "int",
                "category": "event_engine",
                "description": "Máximo de fallos consecutivos antes de considerar checker no saludable",
                "is_readonly": False,
                "requires_confirmation": False,
                "min_value": "1",
                "max_value": "10",
            },
            {
                "key": "default_category",
                "value": "sports",
                "value_type": "string",
                "category": "event_engine",
                "description": "Categoría por defecto para eventos",
                "is_readonly": False,
                "requires_confirmation": False,
                "min_value": None,
                "max_value": None,
            },
            
            # ===== STRATEGY =====
            {
                "key": "min_entry_price",
                "value": "0.98",
                "value_type": "float",
                "category": "strategy",
                "description": "Precio mínimo de entrada",
                "is_readonly": False,
                "requires_confirmation": False,
                "min_value": "0.0",
                "max_value": "1.0",
            },
            {
                "key": "safety_tick",
                "value": "0.0001",
                "value_type": "float",
                "category": "strategy",
                "description": "Tick de seguridad para precio",
                "is_readonly": False,
                "requires_confirmation": False,
                "min_value": "0.0",
                "max_value": "0.01",
            },
            {
                "key": "target_margin",
                "value": "0.001",
                "value_type": "float",
                "category": "strategy",
                "description": "Margen objetivo",
                "is_readonly": False,
                "requires_confirmation": False,
                "min_value": "0.0",
                "max_value": "0.1",
            },
            {
                "key": "max_entry_spread",
                "value": "0.02",
                "value_type": "float",
                "category": "strategy",
                "description": "Spread máximo de entrada",
                "is_readonly": False,
                "requires_confirmation": False,
                "min_value": "0.0",
                "max_value": "0.1",
            },
            {
                "key": "min_liquidity_required",
                "value": "1000.0",
                "value_type": "float",
                "category": "strategy",
                "description": "Liquidez mínima requerida",
                "is_readonly": False,
                "requires_confirmation": False,
                "min_value": "0.0",
                "max_value": "100000.0",
            },
            {
                "key": "safety_tick_multiplier_yellow",
                "value": "2.0",
                "value_type": "float",
                "category": "strategy",
                "description": "Multiplicador de safety_tick para latencia YELLOW",
                "is_readonly": False,
                "requires_confirmation": False,
                "min_value": "1.0",
                "max_value": "10.0",
            },
            {
                "key": "safety_tick_multiplier_red",
                "value": "3.0",
                "value_type": "float",
                "category": "strategy",
                "description": "Multiplicador de safety_tick para latencia RED",
                "is_readonly": False,
                "requires_confirmation": False,
                "min_value": "1.0",
                "max_value": "10.0",
            },
            {
                "key": "yellow_latency_size_factor",
                "value": "0.5",
                "value_type": "float",
                "category": "strategy",
                "description": "Factor de reducción de tamaño en latencia YELLOW",
                "is_readonly": False,
                "requires_confirmation": False,
                "min_value": "0.1",
                "max_value": "1.0",
            },
            {
                "key": "sports_old_event_minutes",
                "value": "10",
                "value_type": "int",
                "category": "strategy",
                "description": "Minutos después del final del evento para considerar 'viejo'",
                "is_readonly": False,
                "requires_confirmation": False,
                "min_value": "1",
                "max_value": "60",
            },
            {
                "key": "sports_old_event_size_factor",
                "value": "0.7",
                "value_type": "float",
                "category": "strategy",
                "description": "Factor de reducción de tamaño para eventos deportivos viejos",
                "is_readonly": False,
                "requires_confirmation": False,
                "min_value": "0.1",
                "max_value": "1.0",
            },
            {
                "key": "sports_multi_source_threshold",
                "value": "3",
                "value_type": "int",
                "category": "strategy",
                "description": "Número mínimo de fuentes que deben coincidir para aumentar tamaño",
                "is_readonly": False,
                "requires_confirmation": False,
                "min_value": "2",
                "max_value": "10",
            },
            {
                "key": "sports_multi_source_size_factor",
                "value": "1.1",
                "value_type": "float",
                "category": "strategy",
                "description": "Factor de aumento de tamaño cuando múltiples fuentes coinciden",
                "is_readonly": False,
                "requires_confirmation": False,
                "min_value": "1.0",
                "max_value": "2.0",
            },
            {
                "key": "default_orderbook_liquidity",
                "value": "10000.0",
                "value_type": "float",
                "category": "strategy",
                "description": "Liquidez por defecto del orderbook cuando no está disponible",
                "is_readonly": False,
                "requires_confirmation": False,
                "min_value": "0.0",
                "max_value": "100000.0",
            },
            
            # ===== RISK =====
            {
                "key": "max_exposure_per_market",
                "value": "50000.0",
                "value_type": "float",
                "category": "risk",
                "description": "Exposición máxima por mercado",
                "is_readonly": False,
                "requires_confirmation": False,
                "min_value": "0.0",
                "max_value": "1000000.0",
            },
            {
                "key": "max_global_exposure",
                "value": "500000.0",
                "value_type": "float",
                "category": "risk",
                "description": "Exposición global máxima",
                "is_readonly": False,
                "requires_confirmation": False,
                "min_value": "0.0",
                "max_value": "10000000.0",
            },
            {
                "key": "max_markets_active",
                "value": "30",
                "value_type": "int",
                "category": "risk",
                "description": "Máximo de mercados activos simultáneamente",
                "is_readonly": False,
                "requires_confirmation": False,
                "min_value": "1",
                "max_value": "100",
            },
            {
                "key": "max_order_size",
                "value": "10000.0",
                "value_type": "float",
                "category": "risk",
                "description": "Tamaño máximo de orden",
                "is_readonly": False,
                "requires_confirmation": False,
                "min_value": "0.0",
                "max_value": "100000.0",
            },
            {
                "key": "min_order_size",
                "value": "100.0",
                "value_type": "float",
                "category": "risk",
                "description": "Tamaño mínimo de orden",
                "is_readonly": False,
                "requires_confirmation": False,
                "min_value": "0.0",
                "max_value": "10000.0",
            },
            {
                "key": "latency_fail_mode",
                "value": "strict",
                "value_type": "string",
                "category": "risk",
                "description": "Modo de fail-safe por latencia: strict, moderate, lenient",
                "is_readonly": False,
                "requires_confirmation": True,
                "min_value": None,
                "max_value": None,
            },
            {
                "key": "reduce_size_in_yellow",
                "value": "true",
                "value_type": "bool",
                "category": "risk",
                "description": "Reducir tamaño de orden en latencia YELLOW",
                "is_readonly": False,
                "requires_confirmation": False,
                "min_value": None,
                "max_value": None,
            },
            {
                "key": "yellow_size_factor",
                "value": "0.5",
                "value_type": "float",
                "category": "risk",
                "description": "Factor de reducción de tamaño en latencia YELLOW",
                "is_readonly": False,
                "requires_confirmation": False,
                "min_value": "0.1",
                "max_value": "1.0",
            },
            {
                "key": "cancel_on_red",
                "value": "true",
                "value_type": "bool",
                "category": "risk",
                "description": "Cancelar órdenes cuando latencia está en RED",
                "is_readonly": False,
                "requires_confirmation": True,
                "min_value": None,
                "max_value": None,
            },
            {
                "key": "exposure_method",
                "value": "notional",
                "value_type": "string",
                "category": "risk",
                "description": "Método de cálculo de exposición: notional, delta",
                "is_readonly": False,
                "requires_confirmation": False,
                "min_value": None,
                "max_value": None,
            },
            {
                "key": "max_price_swing_pct",
                "value": "0.05",
                "value_type": "float",
                "category": "risk",
                "description": "Porcentaje máximo de swing de precio permitido",
                "is_readonly": False,
                "requires_confirmation": False,
                "min_value": "0.0",
                "max_value": "1.0",
            },
            {
                "key": "max_swing_time_seconds",
                "value": "10.0",
                "value_type": "float",
                "category": "risk",
                "description": "Tiempo máximo en segundos para detectar swing de precio",
                "is_readonly": False,
                "requires_confirmation": False,
                "min_value": "1.0",
                "max_value": "60.0",
            },
            {
                "key": "min_realistic_spread",
                "value": "0.001",
                "value_type": "float",
                "category": "risk",
                "description": "Spread mínimo realista",
                "is_readonly": False,
                "requires_confirmation": False,
                "min_value": "0.0",
                "max_value": "0.1",
            },
            {
                "key": "price_history_window_seconds",
                "value": "60",
                "value_type": "int",
                "category": "risk",
                "description": "Ventana de tiempo en segundos para mantener historial de precios",
                "is_readonly": False,
                "requires_confirmation": False,
                "min_value": "10",
                "max_value": "300",
            },
            
            # ===== SCANNER =====
            {
                "key": "min_price_threshold",
                "value": "0.97",
                "value_type": "float",
                "category": "scanner",
                "description": "Precio mínimo para considerar mercado candidato",
                "is_readonly": False,
                "requires_confirmation": False,
                "min_value": "0.0",
                "max_value": "1.0",
            },
            {
                "key": "allowed_categories",
                "value": '["sports"]',
                "value_type": "json",
                "category": "scanner",
                "description": "Categorías permitidas (JSON array)",
                "is_readonly": False,
                "requires_confirmation": False,
                "min_value": None,
                "max_value": None,
            },
            {
                "key": "allowed_subcategories",
                "value": "[]",
                "value_type": "json",
                "category": "scanner",
                "description": "Subcategorías permitidas (JSON array)",
                "is_readonly": False,
                "requires_confirmation": False,
                "min_value": None,
                "max_value": None,
            },
            {
                "key": "scan_interval_seconds",
                "value": "30.0",
                "value_type": "float",
                "category": "scanner",
                "description": "Intervalo de escaneo en segundos",
                "is_readonly": False,
                "requires_confirmation": False,
                "min_value": "1.0",
                "max_value": "3600.0",
            },
            {
                "key": "scanner_http_timeout_seconds",
                "value": "30.0",
                "value_type": "float",
                "category": "scanner",
                "description": "Timeout HTTP para requests del scanner",
                "is_readonly": False,
                "requires_confirmation": False,
                "min_value": "5.0",
                "max_value": "120.0",
            },
            {
                "key": "scanner_cache_ttl_seconds",
                "value": "5",
                "value_type": "int",
                "category": "scanner",
                "description": "TTL del cache de mercados en segundos",
                "is_readonly": False,
                "requires_confirmation": False,
                "min_value": "1",
                "max_value": "60",
            },
            {
                "key": "scanner_pagination_limit",
                "value": "100",
                "value_type": "int",
                "category": "scanner",
                "description": "Límite de resultados por página en paginación",
                "is_readonly": False,
                "requires_confirmation": False,
                "min_value": "10",
                "max_value": "500",
            },
            {
                "key": "scanner_max_pages",
                "value": "10",
                "value_type": "int",
                "category": "scanner",
                "description": "Máximo número de páginas a escanear (safety limit)",
                "is_readonly": False,
                "requires_confirmation": False,
                "min_value": "1",
                "max_value": "50",
            },
            {
                "key": "scanner_max_event_days_ahead",
                "value": "7",
                "value_type": "int",
                "category": "scanner",
                "description": "Máximo número de días en el futuro para filtrar eventos",
                "is_readonly": False,
                "requires_confirmation": False,
                "min_value": "1",
                "max_value": "365",
            },
            {
                "key": "min_volume_24h",
                "value": "10000.0",
                "value_type": "float",
                "category": "scanner",
                "description": "Volumen mínimo en 24h para considerar mercado",
                "is_readonly": False,
                "requires_confirmation": False,
                "min_value": "0.0",
                "max_value": "1000000.0",
            },
            {
                "key": "min_liquidity",
                "value": "5000.0",
                "value_type": "float",
                "category": "scanner",
                "description": "Liquidez mínima requerida",
                "is_readonly": False,
                "requires_confirmation": False,
                "min_value": "0.0",
                "max_value": "100000.0",
            },
            
            # ===== EXECUTION =====
            {
                "key": "max_poll_attempts",
                "value": "720",
                "value_type": "int",
                "category": "execution",
                "description": "Máximo de intentos de polling para estado de orden",
                "is_readonly": False,
                "requires_confirmation": False,
                "min_value": "1",
                "max_value": "10000",
            },
            {
                "key": "poll_interval_seconds",
                "value": "5.0",
                "value_type": "float",
                "category": "execution",
                "description": "Intervalo de polling en segundos",
                "is_readonly": False,
                "requires_confirmation": False,
                "min_value": "1.0",
                "max_value": "60.0",
            },
            {
                "key": "order_timeout_seconds",
                "value": "3600.0",
                "value_type": "float",
                "category": "execution",
                "description": "Timeout de orden en segundos",
                "is_readonly": False,
                "requires_confirmation": False,
                "min_value": "60.0",
                "max_value": "86400.0",
            },
            {
                "key": "retry_on_failure",
                "value": "true",
                "value_type": "bool",
                "category": "execution",
                "description": "Reintentar en caso de fallo",
                "is_readonly": False,
                "requires_confirmation": False,
                "min_value": None,
                "max_value": None,
            },
            {
                "key": "max_retries",
                "value": "3",
                "value_type": "int",
                "category": "execution",
                "description": "Máximo de reintentos",
                "is_readonly": False,
                "requires_confirmation": False,
                "min_value": "0",
                "max_value": "10",
            },
            {
                "key": "execution_max_retries",
                "value": "3",
                "value_type": "int",
                "category": "execution",
                "description": "Máximo de reintentos para ejecución de órdenes",
                "is_readonly": False,
                "requires_confirmation": False,
                "min_value": "0",
                "max_value": "10",
            },
            {
                "key": "execution_retry_delay_seconds",
                "value": "1.0",
                "value_type": "float",
                "category": "execution",
                "description": "Delay entre reintentos en segundos",
                "is_readonly": False,
                "requires_confirmation": False,
                "min_value": "0.1",
                "max_value": "10.0",
            },
            {
                "key": "execution_http_timeout_seconds",
                "value": "30.0",
                "value_type": "float",
                "category": "execution",
                "description": "Timeout HTTP para requests de ejecución",
                "is_readonly": False,
                "requires_confirmation": False,
                "min_value": "5.0",
                "max_value": "120.0",
            },
            
            # ===== BET SIZE CONFIGURATION =====
            {
                "key": "bet_size_mode",
                "value": "fixed_range",
                "value_type": "string",
                "category": "strategy",
                "description": "Modo de cálculo de tamaño de apuesta: 'percentage' (porcentaje del bank) o 'fixed_range' (rango fijo en USDC)",
                "is_readonly": False,
                "requires_confirmation": False,
                "min_value": None,
                "max_value": None,
            },
            {
                "key": "bet_size_min",
                "value": "10.0",
                "value_type": "float",
                "category": "strategy",
                "description": "Tamaño mínimo de apuesta en USDC (solo cuando bet_size_mode = 'fixed_range')",
                "is_readonly": False,
                "requires_confirmation": False,
                "min_value": "0.01",
                "max_value": "100000.0",
            },
            {
                "key": "bet_size_max",
                "value": "50.0",
                "value_type": "float",
                "category": "strategy",
                "description": "Tamaño máximo de apuesta en USDC (solo cuando bet_size_mode = 'fixed_range')",
                "is_readonly": False,
                "requires_confirmation": False,
                "min_value": "0.01",
                "max_value": "100000.0",
            },
        ]
        
        inserted = 0
        skipped = 0
        
        for config_data in configs:
            try:
                # Verificar si ya existe
                existing = db.query(SystemConfig).filter(SystemConfig.key == config_data["key"]).first()
                if existing:
                    # Actualizar campos faltantes
                    updated = False
                    for field in ["is_readonly", "requires_confirmation", "min_value", "max_value", "execution_mode"]:
                        if hasattr(SystemConfig, field) and field in config_data:
                            current_value = getattr(existing, field, None)
                            new_value = config_data[field]
                            if current_value != new_value:
                                setattr(existing, field, new_value)
                                updated = True
                    
                    if updated:
                        db.commit()
                        print(f"[UPDATE] Actualizado {config_data['key']}")
                        inserted += 1
                    else:
                        print(f"[SKIP] Saltando {config_data['key']} (ya existe y está actualizado)")
                        skipped += 1
                    continue
                
                # Crear nuevo registro
                config = SystemConfig(**config_data)
                db.add(config)
                db.commit()
                print(f"[OK] Insertado {config_data['key']} = {config_data['value']} ({config_data['category']})")
                inserted += 1
            except IntegrityError:
                db.rollback()
                print(f"[WARN] Error de integridad en {config_data['key']} (probablemente ya existe)")
                skipped += 1
            except Exception as e:
                db.rollback()
                print(f"[ERROR] Error insertando {config_data['key']}: {e}")
                skipped += 1
        
        print(f"\n[RESUMEN] {inserted} insertados, {skipped} saltados")
        
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Error general: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("Poblando system_config con valores iniciales...\n")
    seed_system_config()
    print("\nCompletado!")

