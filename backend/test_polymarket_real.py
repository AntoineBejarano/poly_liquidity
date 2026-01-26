"""
Script de prueba para verificar que el scanner funciona con datos reales de Polymarket.

Ejecutar con: python -m test_polymarket_real
"""
import asyncio
import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import SessionLocal
from app.core.scanner.scanner import Scanner
from app.models.series import Series
from app.models.market import Market
from app.models.event import Event
from app.models.tag import Tag
from app.models.market_tag import MarketTag
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_scanner_real():
    """Prueba el scanner con datos reales de Polymarket."""
    logger.info("=" * 80)
    logger.info("TEST: Scanner con datos reales de Polymarket")
    logger.info("=" * 80)
    
    scanner = Scanner()
    
    try:
        # Ejecutar un tick del scanner
        logger.info("Ejecutando scanner.tick()...")
        await scanner.tick()
        logger.info("✓ Scanner tick completado")
        
        # Verificar datos en DB
        db = SessionLocal()
        try:
            # Contar Series
            series_count = db.query(Series).count()
            logger.info(f"✓ Series en DB: {series_count}")
            
            if series_count > 0:
                # Mostrar algunas Series
                series_list = db.query(Series).limit(5).all()
                logger.info("\nPrimeras Series:")
                for s in series_list:
                    logger.info(f"  - {s.name} (ID: {s.polymarket_series_id})")
            
            # Contar Markets
            markets_count = db.query(Market).count()
            logger.info(f"✓ Markets en DB: {markets_count}")
            
            if markets_count > 0:
                # Mostrar algunos Markets
                markets_list = db.query(Market).limit(5).all()
                logger.info("\nPrimeros Markets:")
                for m in markets_list:
                    series_name = m.series.name if m.series else "Sin Serie"
                    logger.info(f"  - {m.name} (ID: {m.polymarket_id}, Serie: {series_name}, Enabled: {m.enabled})")
            
            # Contar Events
            events_count = db.query(Event).count()
            logger.info(f"✓ Events en DB: {events_count}")
            
            if events_count > 0:
                # Mostrar algunos Events
                events_list = db.query(Event).limit(5).all()
                logger.info("\nPrimeros Events:")
                for e in events_list:
                    market_name = e.market.name if e.market else "Sin Market"
                    logger.info(f"  - Event {e.polymarket_event_id[:20]}... (Market: {market_name}, State: {e.state})")
                    logger.info(f"    Start: {e.start_time}, End: {e.end_time}")
            
            # Contar Tags
            tags_count = db.query(Tag).count()
            logger.info(f"✓ Tags en DB: {tags_count}")
            
            if tags_count > 0:
                # Mostrar algunos Tags
                tags_list = db.query(Tag).limit(5).all()
                logger.info("\nPrimeros Tags:")
                for t in tags_list:
                    logger.info(f"  - {t.name} (ID: {t.polymarket_tag_id})")
            
            # Verificar Markets habilitados
            enabled_markets = db.query(Market).filter(Market.enabled == True).count()
            logger.info(f"✓ Markets habilitados: {enabled_markets}")
            
            # Verificar Events por estado
            events_upcoming = db.query(Event).filter(Event.state == "UPCOMING").count()
            events_active = db.query(Event).filter(Event.state == "ACTIVE").count()
            events_finished = db.query(Event).filter(Event.state == "FINISHED").count()
            logger.info(f"✓ Events UPCOMING: {events_upcoming}")
            logger.info(f"✓ Events ACTIVE: {events_active}")
            logger.info(f"✓ Events FINISHED: {events_finished}")
            
            logger.info("\n" + "=" * 80)
            logger.info("RESUMEN:")
            logger.info(f"  Series: {series_count}")
            logger.info(f"  Markets: {markets_count} (habilitados: {enabled_markets})")
            logger.info(f"  Events: {events_count} (UPCOMING: {events_upcoming}, ACTIVE: {events_active}, FINISHED: {events_finished})")
            logger.info(f"  Tags: {tags_count}")
            logger.info("=" * 80)
            
            if series_count == 0 and markets_count == 0 and events_count == 0:
                logger.warning("⚠️  No se encontraron datos. Verificar:")
                logger.warning("  1. Conexión a internet")
                logger.warning("  2. URL de Polymarket Gamma API correcta")
                logger.warning("  3. Rate limiting no está bloqueando requests")
                return False
            
            return True
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"❌ Error durante el test: {e}", exc_info=True)
        return False
    finally:
        # Cerrar cliente HTTP si existe
        if scanner._client:
            await scanner._client.aclose()


async def main():
    """Función principal."""
    success = await test_scanner_real()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())














