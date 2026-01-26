"""
Utilidades para interpretar eventos on-chain de Polymarket.

Este módulo proporciona funciones para interpretar eventos OrderFilled
y otros eventos relacionados con órdenes en la blockchain.
"""
import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class OrderFilledEvent:
    """
    Representa un evento OrderFilled on-chain de Polymarket.
    
    Según documentación de Polymarket CLOB API.
    """
    def __init__(
        self,
        order_hash: str,
        maker: str,
        taker: str,
        maker_asset_id: str,
        taker_asset_id: str,
        maker_amount_filled: str,
        taker_amount_filled: str,
        fee: str,
        block_number: Optional[int] = None,
        transaction_hash: Optional[str] = None,
        timestamp: Optional[datetime] = None
    ):
        self.order_hash = order_hash
        self.maker = maker
        self.taker = taker
        self.maker_asset_id = maker_asset_id
        self.taker_asset_id = taker_asset_id
        self.maker_amount_filled = maker_amount_filled
        self.taker_amount_filled = taker_amount_filled
        self.fee = fee
        self.block_number = block_number
        self.transaction_hash = transaction_hash
        self.timestamp = timestamp or datetime.utcnow()
    
    @property
    def is_buy_order(self) -> bool:
        """
        Determina si la orden es una compra (BUY).
        
        Según documentación:
        - Si makerAssetId == 0 → Orden es BUY (dando USDC por Outcome tokens)
        - Si makerAssetId != 0 → Orden es SELL (dando Outcome tokens por USDC)
        """
        return self.maker_asset_id == "0" or int(self.maker_asset_id, 16) == 0
    
    @property
    def is_sell_order(self) -> bool:
        """Determina si la orden es una venta (SELL)."""
        return not self.is_buy_order
    
    @property
    def side(self) -> str:
        """Retorna 'BUY' o 'SELL' según el tipo de orden."""
        return "BUY" if self.is_buy_order else "SELL"
    
    @property
    def fill_price(self) -> float:
        """
        Calcula el precio del fill.
        
        Para BUY: precio = makerAmountFilled / takerAmountFilled
        Para SELL: precio = takerAmountFilled / makerAmountFilled
        """
        try:
            maker_amount = float(self.maker_amount_filled)
            taker_amount = float(self.taker_amount_filled)
            
            if taker_amount == 0:
                return 0.0
            
            if self.is_buy_order:
                # BUY: dando USDC, recibiendo tokens
                # Precio = USDC dado / tokens recibidos
                return maker_amount / taker_amount
            else:
                # SELL: dando tokens, recibiendo USDC
                # Precio = USDC recibido / tokens dados
                return taker_amount / maker_amount
        except (ValueError, ZeroDivisionError) as e:
            logger.error(f"Error calculating fill price: {e}")
            return 0.0
    
    @property
    def fill_size(self) -> float:
        """
        Calcula el tamaño del fill en shares de outcome token.
        
        Para BUY: tamaño = takerAmountFilled (tokens recibidos)
        Para SELL: tamaño = makerAmountFilled (tokens dados)
        """
        try:
            if self.is_buy_order:
                # BUY: el tamaño es la cantidad de tokens recibidos
                return float(self.taker_amount_filled)
            else:
                # SELL: el tamaño es la cantidad de tokens dados
                return float(self.maker_amount_filled)
        except ValueError as e:
            logger.error(f"Error calculating fill size: {e}")
            return 0.0
    
    @property
    def usdc_amount(self) -> float:
        """
        Calcula la cantidad de USDC involucrada en el fill.
        
        Para BUY: USDC = makerAmountFilled (USDC dado)
        Para SELL: USDC = takerAmountFilled (USDC recibido)
        """
        try:
            if self.is_buy_order:
                return float(self.maker_amount_filled)
            else:
                return float(self.taker_amount_filled)
        except ValueError as e:
            logger.error(f"Error calculating USDC amount: {e}")
            return 0.0
    
    @property
    def fee_amount(self) -> float:
        """Retorna el fee pagado por el maker."""
        try:
            return float(self.fee)
        except ValueError:
            return 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte el evento a diccionario."""
        return {
            "order_hash": self.order_hash,
            "maker": self.maker,
            "taker": self.taker,
            "side": self.side,
            "fill_price": self.fill_price,
            "fill_size": self.fill_size,
            "usdc_amount": self.usdc_amount,
            "fee": self.fee_amount,
            "maker_asset_id": self.maker_asset_id,
            "taker_asset_id": self.taker_asset_id,
            "block_number": self.block_number,
            "transaction_hash": self.transaction_hash,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }


def parse_order_filled_event(event_data: Dict[str, Any]) -> Optional[OrderFilledEvent]:
    """
    Parsea un evento OrderFilled desde datos de blockchain.
    
    Args:
        event_data: Diccionario con datos del evento on-chain
    
    Returns:
        OrderFilledEvent parseado o None si hay error
    """
    try:
        return OrderFilledEvent(
            order_hash=event_data.get("orderHash") or event_data.get("order_hash", ""),
            maker=event_data.get("maker", ""),
            taker=event_data.get("taker", ""),
            maker_asset_id=str(event_data.get("makerAssetId") or event_data.get("maker_asset_id", "0")),
            taker_asset_id=str(event_data.get("takerAssetId") or event_data.get("taker_asset_id", "0")),
            maker_amount_filled=str(event_data.get("makerAmountFilled") or event_data.get("maker_amount_filled", "0")),
            taker_amount_filled=str(event_data.get("takerAmountFilled") or event_data.get("taker_amount_filled", "0")),
            fee=str(event_data.get("fee", "0")),
            block_number=event_data.get("blockNumber") or event_data.get("block_number"),
            transaction_hash=event_data.get("transactionHash") or event_data.get("transaction_hash"),
            timestamp=event_data.get("timestamp")
        )
    except Exception as e:
        logger.error(f"Error parsing OrderFilled event: {e}", exc_info=True)
        return None


def interpret_order_filled(
    order_hash: str,
    maker_asset_id: str,
    taker_asset_id: str,
    maker_amount_filled: str,
    taker_amount_filled: str
) -> Tuple[str, float, float]:
    """
    Interpreta un evento OrderFilled y retorna información útil.
    
    Args:
        order_hash: Hash de la orden
        maker_asset_id: ID del asset dado por el maker
        taker_asset_id: ID del asset recibido por el maker
        maker_amount_filled: Cantidad del asset dado
        taker_amount_filled: Cantidad del asset recibido
    
    Returns:
        Tuple de (side, fill_price, fill_size)
        - side: "BUY" o "SELL"
        - fill_price: Precio del fill
        - fill_size: Tamaño del fill en shares
    """
    event = OrderFilledEvent(
        order_hash=order_hash,
        maker="",
        taker="",
        maker_asset_id=maker_asset_id,
        taker_asset_id=taker_asset_id,
        maker_amount_filled=maker_amount_filled,
        taker_amount_filled=taker_amount_filled,
        fee="0"
    )
    
    return event.side, event.fill_price, event.fill_size

