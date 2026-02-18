"""
Worker/entrypoint para el listener Telethon por estrategia.

Modos:
  - Un listener: --strategy-id <UUID> --telegram-source-id <UUID>
  - Descubrir y arrancar todos: --discover (estrategias activas con fuente Telegram)

Uso:
  cd backend && python -m app.workers.telegram_listener_worker --strategy-id X --telegram-source-id Y
  cd backend && python -m app.workers.telegram_listener_worker --discover
"""
import argparse
import logging
import subprocess
import sys
from typing import List, Tuple
from uuid import UUID

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.strategy import Strategy

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def get_telegram_listener_strategies(db: Session) -> List[Tuple[UUID, UUID]]:
    """
    Devuelve (strategy_id, telegram_source_id) de estrategias que tienen
    support_graph con telegram_listener y source_id configurado.
    Por defecto solo estrategias activas.
    """
    out: List[Tuple[UUID, UUID]] = []
    strategies = db.query(Strategy).filter(Strategy.is_active.is_(True)).all()
    for s in strategies:
        for graph in (s.support_graphs or []):
            if not isinstance(graph, dict):
                continue
            if graph.get("name") != "telegram_listener":
                continue
            nodes = graph.get("nodes") or {}
            for node in nodes.values():
                if not isinstance(node, dict) or node.get("type") != "telegram_listener":
                    continue
                source_id = (node.get("config") or {}).get("source_id")
                if not source_id:
                    continue
                try:
                    tid = UUID(str(source_id))
                    out.append((s.id, tid))
                    break
                except (ValueError, TypeError):
                    pass
            break
    return out


def run_single_listener(strategy_id: UUID, telegram_source_id: UUID) -> None:
    """Ejecuta un solo listener (bloquea hasta que se cancele)."""
    from app.core.telegram.listener import run_telegram_listener_sync
    run_telegram_listener_sync(str(strategy_id), str(telegram_source_id))


def run_discover() -> None:
    """
    Descubre estrategias con Telegram y arranca un proceso por cada una.
    El proceso actual lanza subprocesos y los espera; si uno cae, se puede reiniciar (por simplicidad solo esperamos).
    """
    db = SessionLocal()
    try:
        pairs = get_telegram_listener_strategies(db)
    finally:
        db.close()

    if not pairs:
        logger.info("No hay estrategias activas con listener Telegram configurado.")
        return

    logger.info("Estrategias con Telegram: %d. Arrancando un proceso por cada una.", len(pairs))
    # Un proceso por (strategy_id, source_id) para no mezclar asyncio loops
    procs = []
    for strategy_id, source_id in pairs:
        cmd = [
            sys.executable,
            "-m",
            "app.workers.telegram_listener_worker",
            "--strategy-id", str(strategy_id),
            "--telegram-source-id", str(source_id),
        ]
        p = subprocess.Popen(cmd)
        procs.append((strategy_id, source_id, p))
        logger.info("Listener arrancado: strategy=%s source=%s pid=%s", strategy_id, source_id, p.pid)

    # Esperar a que cualquiera termine (en producción usarías un supervisor que reinicie)
    try:
        for strategy_id, source_id, p in procs:
            p.wait()
            if p.returncode != 0:
                logger.warning("Listener strategy=%s source=%s salió con código %s", strategy_id, source_id, p.returncode)
    except KeyboardInterrupt:
        logger.info("Interrumpido; terminando procesos hijos...")
        for _, _, p in procs:
            p.terminate()
        for _, _, p in procs:
            p.wait(timeout=10)


def main() -> None:
    parser = argparse.ArgumentParser(description="Listener Telegram por estrategia")
    parser.add_argument("--strategy-id", type=str, help="UUID de la estrategia")
    parser.add_argument("--telegram-source-id", type=str, help="UUID de la fuente Telegram (ExternalDataSource)")
    parser.add_argument("--discover", action="store_true", help="Descubrir estrategias activas con Telegram y arrancar listeners")
    args = parser.parse_args()

    if args.discover:
        run_discover()
        return

    if not args.strategy_id or not args.telegram_source_id:
        parser.error("Indica --strategy-id y --telegram-source-id, o --discover")
        return

    try:
        sid = UUID(args.strategy_id)
        tid = UUID(args.telegram_source_id)
    except ValueError as e:
        logger.error("UUIDs inválidos: %s", e)
        sys.exit(1)

    logger.info("Arrancando listener strategy=%s telegram_source=%s", sid, tid)
    try:
        run_single_listener(sid, tid)
    except KeyboardInterrupt:
        logger.info("Listener detenido por el usuario")
    except Exception as e:
        logger.exception("Error en listener: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
