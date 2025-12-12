"""
EIP-712 Signer - Firma de órdenes usando EIP-712.

Según especificación en docs/services/execution.md y docs/services/signatures_trazability.md
"""
import logging
import hashlib
from typing import Dict, Any, Optional
from eth_account import Account
from app.core.execution.models import ExecutionConfig

logger = logging.getLogger(__name__)


class EIP712Signer:
    """
    Signer EIP-712 para órdenes de Polymarket.
    
    Según especificación EIP-712.
    """
    
    def __init__(self, config: Optional[ExecutionConfig] = None):
        """Inicializa el EIP-712 Signer."""
        self._config = config or ExecutionConfig()
    
    def get_eip712_domain(self) -> Dict[str, Any]:
        """
        Obtiene el domain EIP-712 según configuración.
        
        Returns:
            Domain EIP-712 completo.
        """
        domain = {
            "name": self._config.eip712_domain_name,
            "version": self._config.eip712_domain_version,
            "chainId": self._config.eip712_chain_id,
        }
        
        if self._config.eip712_verifying_contract:
            domain["verifyingContract"] = self._config.eip712_verifying_contract
        
        return domain
    
    def get_eip712_types(self) -> Dict[str, Any]:
        """
        Obtiene los types EIP-712 para órdenes.
        
        Returns:
            Types EIP-712 completos.
        """
        return {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"},
            ],
            "Order": [
                {"name": "marketId", "type": "string"},
                {"name": "outcome", "type": "string"},
                {"name": "price", "type": "uint256"},
                {"name": "size", "type": "uint256"},
                {"name": "side", "type": "string"},
                {"name": "nonce", "type": "uint256"},
                {"name": "expiration", "type": "uint256"},
                {"name": "clientOrderId", "type": "string"},
            ]
        }
    
    def build_order_message(
        self,
        market_id: str,
        outcome: str,
        price: float,
        size: float,
        side: str,
        nonce: int,
        expiration: int,
        client_order_id: str
    ) -> Dict[str, Any]:
        """
        Construye el mensaje EIP-712 para una orden.
        
        Args:
            market_id: ID del mercado en Polymarket
            outcome: "YES" o "NO"
            price: Precio (se convertirá a wei)
            size: Tamaño (se convertirá a wei)
            side: "BUY" o "SELL"
            nonce: Nonce de la orden
            expiration: Timestamp de expiración
            client_order_id: ID de orden del cliente
        
        Returns:
            Mensaje EIP-712 completo.
        """
        # Convertir precio y tamaño a wei (18 decimales)
        # Por ahora, asumimos que price y size ya están en las unidades correctas
        # TODO: Ajustar según especificación real de Polymarket
        price_wei = int(price * 10**18) if price < 1.0 else int(price)
        size_wei = int(size * 10**18) if size < 1.0 else int(size)
        
        return {
            "marketId": market_id,
            "outcome": outcome,
            "price": price_wei,
            "size": size_wei,
            "side": side,
            "nonce": nonce,
            "expiration": expiration,
            "clientOrderId": client_order_id,
        }
    
    def sign(
        self,
        message: Dict[str, Any],
        private_key: str
    ) -> Dict[str, Any]:
        """
        Firma un mensaje EIP-712.
        
        Args:
            message: Mensaje EIP-712 a firmar
            private_key: Clave privada (hex string con o sin 0x)
        
        Returns:
            Dict con signature, domain_separator, message_hash, etc.
        """
        domain = self.get_eip712_domain()
        types = self.get_eip712_types()
        
        # Limpiar private_key (remover 0x si existe)
        if private_key.startswith("0x"):
            private_key = private_key[2:]
        
        try:
            # Firmar usando eth_account.sign_typed_data (método correcto para EIP-712)
            structured_data = {
                "types": types,
                "domain": domain,
                "primaryType": "Order",
                "message": message
            }
            
            # Firmar usando Account.sign_typed_data (método estático)
            signed_message = Account.sign_typed_data(
                private_key,
                structured_data
            )
            
            # Calcular hashes para trazabilidad
            domain_separator = self._calculate_domain_separator(domain, types)
            message_hash = self._calculate_message_hash(message, types)
            
            return {
                "signature": signed_message.signature.hex(),
                "domain_separator": domain_separator,
                "message_hash": message_hash,
                "domain_json": domain,
                "message_struct": message,
            }
        except Exception as e:
            logger.error(f"Error signing EIP-712 message: {e}")
            raise
    
    def _calculate_domain_separator(
        self,
        domain: Dict[str, Any],
        types: Dict[str, Any]
    ) -> str:
        """
        Calcula el hash del domain separator.
        
        Esto es para trazabilidad - eth_account lo calcula internamente.
        """
        # Por ahora, retornar un hash simple
        # TODO: Implementar cálculo real del domain separator según EIP-712
        domain_str = str(domain)
        return hashlib.sha256(domain_str.encode()).hexdigest()
    
    def _calculate_message_hash(
        self,
        message: Dict[str, Any],
        types: Dict[str, Any]
    ) -> str:
        """
        Calcula el hash del mensaje.
        
        Esto es para trazabilidad - eth_account lo calcula internamente.
        """
        # Por ahora, retornar un hash simple
        # TODO: Implementar cálculo real del message hash según EIP-712
        message_str = str(message)
        return hashlib.sha256(message_str.encode()).hexdigest()

