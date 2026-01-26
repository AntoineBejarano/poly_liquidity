"""
Strategy Template Configuration Schemas.
These define the form fields and validation rules for each strategy template.
The user configures these via forms, and they compile to Decision Graphs.
"""
from typing import Dict, Any, List, Optional
from enum import Enum


class FieldType(str, Enum):
    """Types of form fields."""
    BOOLEAN = "boolean"
    NUMBER = "number"
    STRING = "string"
    SELECT = "select"
    RANGE = "range"
    MULTI_SELECT = "multi_select"


class StrategyTemplateConfig:
    """Configuration schema for a strategy template."""
    
    def __init__(
        self,
        template_id: str,
        name: str,
        description: str,
        category: str,
        fields: List[Dict[str, Any]],
        compiler: str,  # Function name that compiles config to Decision Graph
    ):
        self.template_id = template_id
        self.name = name
        self.description = description
        self.category = category
        self.fields = fields
        self.compiler = compiler


# Template Config: Near-Resolution Liquidity Provider
LIQUIDITY_NEAR_END_CONFIG = StrategyTemplateConfig(
    template_id="liquidity_near_end",
    name="Near-Resolution Liquidity Provider",
    description="Provee liquidez cuando un evento ya terminó pero aún no ha sido resuelto por Polymarket. Captura el diferencial con riesgo casi nulo.",
    category="liquidity",
    fields=[
        {
            "key": "event_finished",
            "label": "Evento ya finalizado",
            "type": FieldType.BOOLEAN,
            "default": True,
            "required": True,
            "description": "Solo entrar si el evento ya terminó en el mundo real",
            "section": "Condiciones de Entrada"
        },
        {
            "key": "external_confirmation_required",
            "label": "Confirmación externa requerida",
            "type": FieldType.BOOLEAN,
            "default": True,
            "required": True,
            "description": "Requiere confirmación de fuente externa antes de entrar",
            "section": "Condiciones de Entrada"
        },
        {
            "key": "allow_ambiguity",
            "label": "Permitir ambigüedad",
            "type": FieldType.BOOLEAN,
            "default": False,
            "required": False,
            "description": "Permitir entrada si el resultado es ambiguo",
            "section": "Condiciones de Entrada"
        },
        {
            "key": "price_min",
            "label": "Precio mínimo",
            "type": FieldType.NUMBER,
            "default": 0.95,
            "min": 0.0,
            "max": 1.0,
            "step": 0.01,
            "required": True,
            "description": "Precio mínimo para entrar (ej: 0.95)",
            "section": "Rango de Precio"
        },
        {
            "key": "price_max",
            "label": "Precio máximo",
            "type": FieldType.NUMBER,
            "default": 0.98,
            "min": 0.0,
            "max": 1.0,
            "step": 0.01,
            "required": True,
            "description": "Precio máximo para entrar (ej: 0.98)",
            "section": "Rango de Precio"
        },
        {
            "key": "max_size_per_event",
            "label": "Tamaño máximo por evento (USDC)",
            "type": FieldType.NUMBER,
            "default": 5000,
            "min": 100,
            "max": 100000,
            "step": 100,
            "required": True,
            "description": "Tamaño máximo de orden por evento",
            "section": "Gestión de Riesgo"
        },
        {
            "key": "volatility_scaling",
            "label": "Reducir tamaño si volatilidad alta",
            "type": FieldType.BOOLEAN,
            "default": True,
            "required": False,
            "description": "Ajustar tamaño de orden según volatilidad del mercado",
            "section": "Gestión de Riesgo"
        },
        {
            "key": "min_liquidity",
            "label": "Liquidez mínima requerida (USDC)",
            "type": FieldType.NUMBER,
            "default": 2000,
            "min": 0,
            "max": 100000,
            "step": 100,
            "required": False,
            "description": "Solo entrar si hay suficiente liquidez en el mercado",
            "section": "Condiciones de Mercado"
        },
        {
            "key": "min_spread",
            "label": "Spread mínimo requerido (%)",
            "type": FieldType.NUMBER,
            "default": 1.5,
            "min": 0,
            "max": 10,
            "step": 0.1,
            "required": False,
            "description": "Solo entrar si el spread es suficientemente amplio",
            "section": "Condiciones de Mercado"
        },
        {
            "key": "external_source_id",
            "label": "Fuente externa de confirmación",
            "type": FieldType.SELECT,
            "required": True,
            "description": "Selecciona la fuente externa que confirma resultados de eventos",
            "section": "Fuentes de Datos",
            "options_source": "external_data_sources",  # Dynamic options from API
        }
    ],
    compiler="compile_liquidity_near_end"
)


# Template Config: Surebet Polymarket-Pinnacle
SURBET_POLYMARKET_PINNACLE_CONFIG = StrategyTemplateConfig(
    template_id="surebet_polymarket_pinnacle",
    name="Surebet Polymarket-Pinnacle",
    description="Detecta y ejecuta surebets entre Polymarket y Pinnacle. Compra en el mercado más barato y vende en el más caro.",
    category="arbitrage",
    fields=[
        {
            "key": "min_profit_percentage",
            "label": "Profit mínimo requerido (%)",
            "type": FieldType.NUMBER,
            "default": 2.0,
            "min": 0.1,
            "max": 10.0,
            "step": 0.1,
            "required": True,
            "description": "Porcentaje mínimo de profit para ejecutar el surebet",
            "section": "Condiciones de Entrada"
        },
        {
            "key": "max_size_per_event",
            "label": "Tamaño máximo por evento (USDC)",
            "type": FieldType.NUMBER,
            "default": 2000,
            "min": 100,
            "max": 50000,
            "step": 100,
            "required": True,
            "description": "Tamaño máximo de orden por evento",
            "section": "Gestión de Riesgo"
        },
        {
            "key": "pinnacle_source_id",
            "label": "Fuente de odds de Pinnacle",
            "type": FieldType.SELECT,
            "required": True,
            "description": "Selecciona la fuente externa que proporciona odds de Pinnacle",
            "section": "Fuentes de Datos",
            "options_source": "external_data_sources",
        },
        {
            "key": "polling_interval_seconds",
            "label": "Intervalo de polling (segundos)",
            "type": FieldType.NUMBER,
            "default": 10,
            "min": 5,
            "max": 60,
            "step": 5,
            "required": True,
            "description": "Cada cuántos segundos verificar nuevas oportunidades",
            "section": "Configuración"
        }
    ],
    compiler="compile_surebet_polymarket_pinnacle"
)


# All template configs
TEMPLATE_CONFIGS = {
    "liquidity_near_end": LIQUIDITY_NEAR_END_CONFIG,
    "surebet_polymarket_pinnacle": SURBET_POLYMARKET_PINNACLE_CONFIG,
}


def get_template_config(template_id: str) -> Optional[StrategyTemplateConfig]:
    """Get template config by ID."""
    return TEMPLATE_CONFIGS.get(template_id)


def list_template_configs() -> List[Dict[str, Any]]:
    """List all available template configs."""
    return [
        {
            "id": config.template_id,
            "name": config.name,
            "description": config.description,
            "category": config.category,
        }
        for config in TEMPLATE_CONFIGS.values()
    ]

