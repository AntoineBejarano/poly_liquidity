"""
Directory: capa de lectura cache-first para categories, tags, markets y events.

Phase 1 — Solo lectura desde DB (Redis opcional en fases posteriores).
Nunca llama a Gamma en la request; el Scanner es quien escribe en DB.
"""
from app.core.directory.service import DirectoryService

__all__ = ["DirectoryService"]
