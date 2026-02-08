"""
OrderbookWSRouter - Conecta WebSocket callbacks con OrderbookOrchestrator.
"""
import logging
from typing import Dict, Any
from .orchestrator import OrderbookOrchestrator
from .ws_parser import parse_ws_book_payload
from .publisher import OrderbookPublisher
from .features import (
    compute_spread_bps,
    compute_mid,
    compute_depth_usdc_at_bps_buy,
    compute_impact_bps_for_usdc_buy,
    compute_concentration_top3_pct_buy,
)
from .models import OrderbookState
from app.core.discovery.volatility import get_volatility_store, VOL_SOURCE_MID
import time

logger = logging.getLogger(__name__)


class OrderbookWSRouter:
    """
    Router que conecta WebSocket callbacks con OrderbookOrchestrator.
    
    Responsabilidades:
    - Recibir mensajes WS de book updates
    - Parsear payload
    - Ingresar a orchestrator
    - Calcular features
    - Publicar a State Cache
    """
    
    def __init__(
        self,
        orchestrator: OrderbookOrchestrator,
        publisher: OrderbookPublisher
    ):
        """
        Args:
            orchestrator: OrderbookOrchestrator
            publisher: OrderbookPublisher
        """
        self.orchestrator = orchestrator
        self.publisher = publisher
        self.update_timestamps: Dict[str, list] = {}  # asset_id -> list of timestamps
    
    async def handle_book_update(self, book_msg: Dict[str, Any]) -> None:
        """
        Maneja mensaje WS de book update.
        
        Args:
            book_msg: Mensaje WS con estructura:
                {
                    "event_type": "book",
                    "asset_id": "...",
                    "market": "...",
                    "bids": [{"price": ".48", "size": "30"}, ...],
                    "asks": [{"price": ".52", "size": "25"}, ...],
                    "timestamp": "123456789000"
                }
        """
        try:
            asset_id = book_msg.get("asset_id")
            if not asset_id:
                logger.warning("Book update message missing asset_id")
                return
            
            # Parsear payload
            bids, asks, ts_ms, hash_value = parse_ws_book_payload(book_msg)
            
            # Ingresar a orchestrator
            self.orchestrator.ingest_book_msg(asset_id, bids, asks, ts_ms)
            
            # Obtener book actualizado
            book = self.orchestrator.get_book(asset_id)
            if not book:
                return
            
            # Calcular BBO
            best_bid_price, best_ask_price, mid, spread_bps = book.compute_bbo()
            
            if best_bid_price is None or best_ask_price is None:
                logger.debug(f"No BBO available for asset_id={asset_id}")
                return
            
            # Obtener bids/asks
            bids_list = book.get_bids()
            asks_list = book.get_asks()
            
            # Calcular features (BUY side only)
            depth_25bps = compute_depth_usdc_at_bps_buy(asks_list, best_ask_price, 25)
            depth_50bps = compute_depth_usdc_at_bps_buy(asks_list, best_ask_price, 50)
            depth_100bps = compute_depth_usdc_at_bps_buy(asks_list, best_ask_price, 100)
            
            impact_100 = compute_impact_bps_for_usdc_buy(asks_list, best_ask_price, 100.0)
            impact_500 = compute_impact_bps_for_usdc_buy(asks_list, best_ask_price, 500.0)
            impact_1000 = compute_impact_bps_for_usdc_buy(asks_list, best_ask_price, 1000.0)
            impact_5000 = compute_impact_bps_for_usdc_buy(asks_list, best_ask_price, 5000.0)
            
            concentration = compute_concentration_top3_pct_buy(asks_list)
            
            # Update rate (tracking timestamps)
            if asset_id not in self.update_timestamps:
                self.update_timestamps[asset_id] = []
            self.update_timestamps[asset_id].append(ts_ms)
            # Mantener solo últimos 100 timestamps
            if len(self.update_timestamps[asset_id]) > 100:
                self.update_timestamps[asset_id] = self.update_timestamps[asset_id][-100:]
            
            # Calcular update rate (simplificado, usar últimos 10s)
            from .features import compute_update_rate_hz
            update_rate = compute_update_rate_hz(self.update_timestamps[asset_id], window_seconds=10)
            
            # Staleness (tiempo desde último update)
            now_ms = int(time.time() * 1000)
            staleness_ms = now_ms - ts_ms
            
            # Crear OrderbookState (incluye hash en integrity si está disponible)
            orderbook_state = OrderbookState(
                asset_id=asset_id,
                ts_ms=ts_ms,
                best_bid_price=best_bid_price,
                best_bid_size=bids_list[0].size if bids_list else None,
                best_ask_price=best_ask_price,
                best_ask_size=asks_list[0].size if asks_list else None,
                spread_bps=spread_bps,
                mid=mid,
                bids=bids_list,
                asks=asks_list,
                depth_usdc_at_25bps=depth_25bps,
                depth_usdc_at_50bps=depth_50bps,
                depth_usdc_at_100bps=depth_100bps,
                impact_bps_for_usdc_100=impact_100,
                impact_bps_for_usdc_500=impact_500,
                impact_bps_for_usdc_1000=impact_1000,
                impact_bps_for_usdc_5000=impact_5000,
                concentration_top3_pct=concentration,
                update_rate_hz=update_rate,
                replenishment_score=0.0,  # TODO: Implementar heurística
                staleness_ms=staleness_ms,
                integrity={
                    "resync_count": 0,
                    "last_snapshot_ts_ms": ts_ms,
                    "parse_errors": 0,
                    "hash": hash_value,  # Hash del mensaje WS (opcional)
                }
            )
            
            # Volatilidad rolling (5m/15m) y publicar a State Cache
            ts_sec = ts_ms / 1000.0
            vol_metrics = get_volatility_store().update(asset_id, ts_sec, mid, VOL_SOURCE_MID)
            await self.publisher.publish(asset_id, orderbook_state, extra_metrics=vol_metrics)
            
        except Exception as e:
            logger.error(
                f"Error handling book update: {e}",
                exc_info=True,
                extra={
                    "component": "orderbook",
                    "event": "handle_book_update_error",
                    "book_msg": book_msg
                }
            )



