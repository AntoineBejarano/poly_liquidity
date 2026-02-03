"""
Tests unitarios para seed_system_config.
"""
import pytest
from unittest.mock import patch
from app.database import SessionLocal
from app.models.system_config import SystemConfig
from scripts.seed_system_config import seed_system_config


def test_seed_system_config_creates_required_configs(db_session):
    """Test que seed_system_config crea todas las configuraciones requeridas."""
    # Usar db_session (tablas ya creadas por conftest) en lugar de SessionLocal
    with patch("scripts.seed_system_config.SessionLocal", lambda: db_session):
        # Limpiar configuraciones de prueba
        db_session.query(SystemConfig).delete()
        db_session.commit()
        
        # Ejecutar seed (usará db_session por el patch)
        seed_system_config()
        
        db_session.commit()
    
    db = db_session
    # Verificar que existen configuraciones críticas
    critical_configs = [
        "execution_mode",
        "quorum_base",
        "allow_zero_checker",
        "min_feed_confidence",
        "min_entry_price",
        "safety_tick",
        "target_margin",
        "max_exposure_per_market",
        "max_global_exposure",
    ]
    for key in critical_configs:
        config = db.query(SystemConfig).filter(SystemConfig.key == key).first()
        assert config is not None, f"Configuración {key} no encontrada"
        assert config.value is not None, f"Configuración {key} no tiene valor"
        assert config.category is not None, f"Configuración {key} no tiene categoría"

    # Verificar que execution_mode tiene requires_confirmation = True
    execution_mode = db.query(SystemConfig).filter(SystemConfig.key == "execution_mode").first()
    assert execution_mode.requires_confirmation is True, "execution_mode debe requerir confirmación"
    
    # Verificar que allow_zero_checker tiene requires_confirmation = True
    allow_zero = db.query(SystemConfig).filter(SystemConfig.key == "allow_zero_checker").first()
    assert allow_zero.requires_confirmation is True, "allow_zero_checker debe requerir confirmación"


def test_seed_system_config_protected_params(db_session):
    """Test que los parámetros protegidos tienen las protecciones correctas."""
    with patch("scripts.seed_system_config.SessionLocal", lambda: db_session):
        seed_system_config()
        db_session.commit()
    
    db = db_session
    # Parámetros que deben tener requires_confirmation = True
    protected_params = [
        "execution_mode",
        "allow_zero_checker",
        "quorum_base",
        "min_feed_confidence",
        "latency_fail_mode",
        "cancel_on_red",
    ]
    for key in protected_params:
        config = db.query(SystemConfig).filter(SystemConfig.key == key).first()
        if config:
            assert config.requires_confirmation is True, f"{key} debe requerir confirmación"


def test_seed_system_config_values_are_valid(db_session):
    """Test que los valores de configuración son válidos."""
    with patch("scripts.seed_system_config.SessionLocal", lambda: db_session):
        seed_system_config()
        db_session.commit()
    
    db = db_session
    # Verificar tipos de valores
    configs = db.query(SystemConfig).all()
    for config in configs:
        if config.value_type == "float":
            try:
                float(config.value)
            except ValueError:
                pytest.fail(f"Valor de {config.key} no es un float válido: {config.value}")
        elif config.value_type == "int":
            try:
                int(config.value)
            except ValueError:
                pytest.fail(f"Valor de {config.key} no es un int válido: {config.value}")
        elif config.value_type == "bool":
            assert config.value.lower() in ("true", "false", "1", "0", "yes", "no"), \
                f"Valor de {config.key} no es un bool válido: {config.value}"

