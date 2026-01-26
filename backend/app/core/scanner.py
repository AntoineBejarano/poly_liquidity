"""
Market scanner - discovers and updates Polymarket candidate markets.

Este módulo ha sido refactorizado. La nueva implementación está en:
- app.core.scanner.scanner (Scanner principal)
- app.core.scanner.models (Modelos de datos)
- app.core.scanner.filters (Filtros)
- app.core.scanner.normalizer (Normalización)

Este archivo mantiene compatibilidad hacia atrás.
"""
from app.core.scanner.scanner import Scanner

__all__ = ["Scanner"]
