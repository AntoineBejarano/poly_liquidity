"""
Event Mapping Layer - asociación entre mercados de Polymarket y eventos reales.
"""
from app.core.event_mapping_layer.mapper import EventMappingLayer
from app.core.event_mapping_layer.models import EventDescriptor, EventType

__all__ = [
    "EventMappingLayer",
    "EventDescriptor",
    "EventType",
]

