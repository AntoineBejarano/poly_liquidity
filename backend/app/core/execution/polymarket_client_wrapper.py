"""
Wrapper para py-clob-client que integra con nuestro Execution Engine.

Este módulo encapsula el cliente oficial de Polymarket y proporciona
una interfaz consistente con nuestro sistema de trazabilidad y logging.
"""
import logging
from typing import Optional, Dict, Any, List
from uuid import UUID
import json
import time
import inspect

from app.settings import settings
from app.core.rate_limiter import rate_limiter, EndpointType

logger = logging.getLogger(__name__)

# Path del archivo de debug log
DEBUG_LOG_PATH = r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log'


def _log_http_error(exception: Exception, location: str, hypothesis_id: str = "A", context: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Helper para capturar y loguear errores HTTP de manera consistente.
    
    Returns:
        Dict con detalles del error para logging
    """
    error_details = {
        "error": str(exception),
        "error_type": type(exception).__name__,
    }
    
    if context:
        error_details.update(context)
    
    # Si es un error HTTP, capturar código de estado y mensaje
    if hasattr(exception, 'response'):
        try:
            response = exception.response
            error_details["http_status_code"] = response.status_code if hasattr(response, 'status_code') else None
            error_details["http_status_text"] = str(response.status) if hasattr(response, 'status') else None
            error_details["http_url"] = str(response.url) if hasattr(response, 'url') else None
            
            # Intentar obtener el cuerpo de la respuesta
            try:
                if hasattr(response, 'json'):
                    error_body = response.json()
                    error_details["error_body"] = error_body
                    error_details["error_message"] = error_body.get('message') if isinstance(error_body, dict) else None
                    error_details["error_detail"] = error_body.get('detail') if isinstance(error_body, dict) else None
                    error_details["error_code"] = error_body.get('code') if isinstance(error_body, dict) else None
            except:
                try:
                    if hasattr(response, 'text'):
                        error_details["error_text"] = response.text[:500]  # Limitar a 500 caracteres
                except:
                    pass
        except Exception as parse_error:
            error_details["parse_error"] = str(parse_error)
    
    # Log específico según el código de estado
    status_code = error_details.get("http_status_code")
    if status_code:
        if status_code == 401:
            logger.error(f"[{location}] UNAUTHORIZED (401): Credentials incorrect or expired. Error: {exception}")
        elif status_code == 404:
            logger.error(f"[{location}] NOT FOUND (404): Endpoint or resource not found. Error: {exception}")
        elif status_code == 400:
            logger.error(f"[{location}] BAD REQUEST (400): Invalid request parameters. Error: {exception}")
        elif status_code == 403:
            logger.error(f"[{location}] FORBIDDEN (403): Access denied. Error: {exception}")
        elif status_code == 429:
            logger.error(f"[{location}] RATE LIMIT (429): Too many requests. Error: {exception}")
        elif status_code >= 500:
            logger.error(f"[{location}] SERVER ERROR ({status_code}): Polymarket server error. Error: {exception}")
        else:
            logger.error(f"[{location}] HTTP ERROR ({status_code}): {exception}")
    else:
        logger.error(f"[{location}] Exception: {exception}", exc_info=True)
    
    # Escribir al log de debug
    try:
        with open(DEBUG_LOG_PATH, 'a') as f:
            f.write(json.dumps({
                "sessionId": "debug-session",
                "runId": "run1",
                "hypothesisId": hypothesis_id,
                "location": location,
                "message": "HTTP Error captured",
                "data": error_details,
                "timestamp": int(time.time() * 1000)
            }) + "\n")
    except Exception as log_error:
        logger.warning(f"Could not write to debug log: {log_error}")
    
    return error_details


class PolymarketCLOBWrapper:
    """
    Wrapper para py-clob-client que integra con nuestro Execution Engine.
    
    Proporciona una interfaz simplificada que:
    - Usa las credenciales desde settings
    - Mantiene compatibilidad con nuestro sistema de trazabilidad
    - Maneja errores y logging de forma consistente
    """
    
    def __init__(self):
        """Inicializa el wrapper del cliente de Polymarket."""
        # #region agent log
        import json
        with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"polymarket_client_wrapper.py:26","message":"PolymarketCLOBWrapper.__init__ ENTRY","data":{"has_private_key":bool(settings.private_key)},"timestamp":int(__import__('time').time()*1000)})+"\n")
        # #endregion
        logger.info("PolymarketCLOBWrapper.__init__ - Iniciando...")
        self._client = None
        self._initialized = False
        
        # Intentar inicializar si hay credenciales disponibles
        if settings.private_key:
            logger.info("PolymarketCLOBWrapper.__init__ - PRIVATE_KEY encontrado, inicializando cliente...")
            # #region agent log
            with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"polymarket_client_wrapper.py:34","message":"BEFORE _initialize_client","data":{},"timestamp":int(__import__('time').time()*1000)})+"\n")
            # #endregion
            try:
                self._initialize_client()
                # #region agent log
                with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"polymarket_client_wrapper.py:36","message":"AFTER _initialize_client","data":{"initialized":self._initialized},"timestamp":int(__import__('time').time()*1000)})+"\n")
                # #endregion
            except Exception as e:
                logger.warning(f"Could not initialize Polymarket CLOB client: {e}")
                # #region agent log
                with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"polymarket_client_wrapper.py:39","message":"EXCEPTION en _initialize_client","data":{"error":str(e)},"timestamp":int(__import__('time').time()*1000)})+"\n")
                # #endregion
        else:
            logger.info("PolymarketCLOBWrapper.__init__ - No hay PRIVATE_KEY, cliente no inicializado")
        # #region agent log
        with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"polymarket_client_wrapper.py:42","message":"PolymarketCLOBWrapper.__init__ EXIT","data":{},"timestamp":int(__import__('time').time()*1000)})+"\n")
        # #endregion
    
    def _initialize_client(self):
        """Inicializa el cliente de Polymarket con credenciales desde settings."""
        logger.info("Inicializando cliente Polymarket CLOB...")
        try:
            logger.info("  - Importando ClobClient y ApiCreds...")
            from py_clob_client.client import ClobClient
            from py_clob_client.clob_types import ApiCreds
            logger.info("  ✓ ClobClient y ApiCreds importados")
        except ImportError:
            logger.error("✗ py-clob-client no está instalado. Instala con: pip install py-clob-client")
            raise
        
        HOST = settings.polymarket_trading_api_url or "https://clob.polymarket.com"
        CHAIN_ID = settings.chain_id or 137
        PRIVATE_KEY = settings.private_key
        FUNDER = settings.funder_address or settings.polymarket_proxy_address
        
        logger.info(f"  - HOST: {HOST}")
        logger.info(f"  - CHAIN_ID: {CHAIN_ID}")
        logger.info(f"  - PRIVATE_KEY: {'✓ configurado' if PRIVATE_KEY else '✗ NO configurado'}")
        logger.info(f"  - FUNDER: {'✓ configurado' if FUNDER else '✗ NO configurado'}")
        
        if not FUNDER:
            # Intentar derivar address desde private_key
            logger.info("  - Intentando derivar FUNDER desde PRIVATE_KEY...")
            try:
                from eth_account import Account
                account = Account.from_key(PRIVATE_KEY)
                FUNDER = account.address
                logger.info(f"  ✓ Dirección derivada desde private key: {FUNDER}")
            except Exception as e:
                logger.error(f"  ✗ No se pudo derivar funder address: {e}")
                raise ValueError("FUNDER_ADDRESS or POLYMARKET_PROXY_ADDRESS required")
        
        # Determinar signature_type basado en si es proxy wallet
        # Por defecto asumimos proxy wallet (signature_type=1)
        # Si el usuario quiere EOA, debería configurarlo explícitamente
        signature_type = getattr(settings, 'signature_type', 1)  # 1 para email/Magic, 0 para EOA
        logger.info(f"  - signature_type: {signature_type}")
        
        logger.info("  - Creando ClobClient (solo con PRIVATE_KEY y FUNDER)...")
        # #region agent log
        import json
        with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"polymarket_client_wrapper.py:186","message":"BEFORE ClobClient constructor","data":{"HOST":HOST,"CHAIN_ID":CHAIN_ID,"has_key":bool(PRIVATE_KEY),"has_funder":bool(FUNDER)},"timestamp":int(__import__('time').time()*1000)})+"\n")
        # #endregion
        
        # Crear ClobClient solo con PRIVATE_KEY y FUNDER (sin creds inicialmente)
        self._client = ClobClient(
            HOST,
            key=PRIVATE_KEY,
            chain_id=CHAIN_ID,
            signature_type=signature_type,
            funder=FUNDER
        )
        logger.info("  ✓ ClobClient creado")
        
        # #region agent log
        with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"polymarket_client_wrapper.py:199","message":"AFTER ClobClient constructor","data":{"has_client":self._client is not None},"timestamp":int(__import__('time').time()*1000)})+"\n")
        # #endregion
        
        # Generar o derivar credenciales API
        # Intentar ambos métodos: create_or_derive_api_key() y create_or_derive_api_creds()
        logger.info("  - Generando/derivando credenciales API...")
        try:
            # #region agent log
            # Verificar qué métodos están disponibles
            client_methods = [m for m in dir(self._client) if 'api' in m.lower() and 'creds' in m.lower() or 'key' in m.lower()]
            with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"polymarket_client_wrapper.py:209","message":"Checking API methods","data":{"has_create_or_derive_api_key":hasattr(self._client, 'create_or_derive_api_key'),"has_create_or_derive_api_creds":hasattr(self._client, 'create_or_derive_api_creds'),"api_methods":client_methods},"timestamp":int(__import__('time').time()*1000)})+"\n")
            # #endregion
            
            api_creds_dict = None
            
            # Intentar create_or_derive_api_key() primero (método según documentación)
            if hasattr(self._client, 'create_or_derive_api_key'):
                # #region agent log
                with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"polymarket_client_wrapper.py:217","message":"Trying create_or_derive_api_key","data":{},"timestamp":int(__import__('time').time()*1000)})+"\n")
                # #endregion
                api_creds_dict = self._client.create_or_derive_api_key()
            # Si no existe, intentar create_or_derive_api_creds() (método alternativo)
            elif hasattr(self._client, 'create_or_derive_api_creds'):
                # #region agent log
                with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"polymarket_client_wrapper.py:223","message":"Trying create_or_derive_api_creds (fallback)","data":{},"timestamp":int(__import__('time').time()*1000)})+"\n")
                # #endregion
                api_creds_dict = self._client.create_or_derive_api_creds()
            else:
                raise AttributeError("Neither create_or_derive_api_key() nor create_or_derive_api_creds() found on ClobClient")
            
            # #region agent log
            with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"polymarket_client_wrapper.py:230","message":"AFTER create_or_derive_api","data":{"has_creds":api_creds_dict is not None,"creds_type":type(api_creds_dict).__name__,"creds_keys":list(api_creds_dict.keys()) if isinstance(api_creds_dict, dict) else None,"creds_attrs":dir(api_creds_dict)[:10] if not isinstance(api_creds_dict, dict) else None},"timestamp":int(__import__('time').time()*1000)})+"\n")
            # #endregion
            
            # Convertir el resultado a ApiCreds
            if isinstance(api_creds_dict, dict):
                api_creds = ApiCreds(
                    api_key=api_creds_dict.get('apiKey') or api_creds_dict.get('api_key'),
                    api_secret=api_creds_dict.get('secret') or api_creds_dict.get('api_secret'),
                    api_passphrase=api_creds_dict.get('passphrase') or api_creds_dict.get('api_passphrase')
                )
            elif hasattr(api_creds_dict, 'apiKey') or hasattr(api_creds_dict, 'api_key'):
                # Ya es un objeto ApiCreds o similar
                api_creds = api_creds_dict
            else:
                raise ValueError(f"Unexpected format from create_or_derive_api: {type(api_creds_dict)}")
            
            # Configurar las credenciales API en el cliente
            self._client.set_api_creds(api_creds)
            logger.info("  ✓ Credenciales API generadas y configuradas")
            
            # #region agent log
            with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"polymarket_client_wrapper.py:250","message":"ApiCreds configured","data":{"has_api_key":hasattr(api_creds, 'apiKey') or (isinstance(api_creds, dict) and 'apiKey' in api_creds)},"timestamp":int(__import__('time').time()*1000)})+"\n")
            # #endregion
        except Exception as e:
            error_details = _log_http_error(e, "polymarket_client_wrapper.py:253", "C", {"operation": "create_or_derive_api"})
            logger.error(f"  ✗ No se pudieron generar/derivar credenciales API: {e}")
            # No hacer raise - permitir que el cliente se inicialice sin creds API
            # Algunos métodos pueden funcionar sin creds API (solo lectura)
            logger.warning("  ⚠ Cliente inicializado sin credenciales API (algunos métodos pueden no funcionar)")
        
        # Marcar como inicializado incluso si las creds API fallaron
        # El cliente puede estar disponible para operaciones básicas
        self._initialized = True
        logger.info(f"✓ Cliente Polymarket CLOB inicializado para funder: {FUNDER}")
        
        # #region agent log
        with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"polymarket_client_wrapper.py:255","message":"Client initialization complete","data":{"initialized":self._initialized,"has_client":self._client is not None,"is_available":self.is_available()},"timestamp":int(__import__('time').time()*1000)})+"\n")
        # #endregion
    
    def is_available(self) -> bool:
        """Verifica si el cliente está disponible y inicializado."""
        return self._initialized and self._client is not None
    
    def get_client(self):
        """Obtiene el cliente de Polymarket."""
        if not self.is_available():
            raise RuntimeError("Polymarket CLOB client not initialized. Check PRIVATE_KEY and FUNDER_ADDRESS.")
        return self._client
    
    async def create_limit_order(
        self,
        token_id: str,
        price: float,
        size: float,
        side: str,
        order_type: str = "GTC"
    ) -> Dict[str, Any]:
        """
        Crea una limit order en Polymarket.
        
        Args:
            token_id: ID del token en Polymarket
            price: Precio de la orden
            size: Tamaño en shares
            side: "BUY" o "SELL"
            order_type: "GTC" (Good Till Cancel) o "FOK" (Fill or Kill)
        
        Returns:
            Respuesta de Polymarket con order_id y status
        """
        if not self.is_available():
            raise RuntimeError("Polymarket CLOB client not initialized")
        
        try:
            from py_clob_client.clob_types import OrderArgs, OrderType
            from py_clob_client.order_builder.constants import BUY, SELL
            
            client = self.get_client()
            
            # Convertir side string a constante
            order_side = BUY if side.upper() == "BUY" else SELL
            
            # Convertir order_type string a enum
            order_type_enum = OrderType.GTC if order_type.upper() == "GTC" else OrderType.FOK
            
            # Crear orden
            order = OrderArgs(
                token_id=token_id,
                price=price,
                size=size,
                side=order_side
            )
            
            # Firmar y enviar
            signed = client.create_order(order)
            
            # Wait for rate limit capacity (CLOB POST /order: 2400 req / 10s burst, 24000 req / 10min sustained)
            if not await rate_limiter.wait_for_capacity(EndpointType.CLOB_POST_ORDER, timeout=5.0):
                logger.warning("Rate limit timeout for CLOB_POST_ORDER")
                raise RuntimeError("Rate limit exceeded for CLOB POST /order endpoint")
            
            resp = client.post_order(signed, order_type_enum)
            
            logger.info(
                f"Limit order created: token_id={token_id}, price={price}, size={size}, side={side}",
                extra={
                    "component": "polymarket_client",
                    "event": "order_created",
                    "token_id": token_id,
                    "order_id": resp.get("id") if isinstance(resp, dict) else None
                }
            )
            
            return resp
        except Exception as e:
            _log_http_error(e, "polymarket_client_wrapper.py:294", "D", {"operation": "create_limit_order", "token_id": token_id})
            logger.error(f"Error creating limit order: {e}", exc_info=True)
            raise
    
    async def create_market_order(
        self,
        token_id: str,
        amount: float,
        side: str,
        order_type: str = "FOK"
    ) -> Dict[str, Any]:
        """
        Crea una market order en Polymarket.
        
        Args:
            token_id: ID del token en Polymarket
            amount: Monto en USD
            side: "BUY" o "SELL"
            order_type: "FOK" (Fill or Kill) o "IOC" (Immediate or Cancel)
        
        Returns:
            Respuesta de Polymarket con order_id y status
        """
        if not self.is_available():
            raise RuntimeError("Polymarket CLOB client not initialized")
        
        try:
            from py_clob_client.clob_types import MarketOrderArgs, OrderType
            from py_clob_client.order_builder.constants import BUY, SELL
            
            client = self.get_client()
            
            # Convertir side string a constante
            order_side = BUY if side.upper() == "BUY" else SELL
            
            # Convertir order_type string a enum
            if order_type.upper() == "FOK":
                order_type_enum = OrderType.FOK
            elif order_type.upper() == "IOC":
                order_type_enum = OrderType.IOC
            else:
                order_type_enum = OrderType.FOK  # Default
            
            # Crear market order
            mo = MarketOrderArgs(
                token_id=token_id,
                amount=amount,
                side=order_side,
                order_type=order_type_enum
            )
            
            # Firmar y enviar
            signed = client.create_market_order(mo)
            
            # Wait for rate limit capacity (CLOB POST /order: 2400 req / 10s burst, 24000 req / 10min sustained)
            if not await rate_limiter.wait_for_capacity(EndpointType.CLOB_POST_ORDER, timeout=5.0):
                logger.warning("Rate limit timeout for CLOB_POST_ORDER")
                raise RuntimeError("Rate limit exceeded for CLOB POST /order endpoint")
            
            resp = client.post_order(signed, order_type_enum)
            
            logger.info(
                f"Market order created: token_id={token_id}, amount={amount}, side={side}",
                extra={
                    "component": "polymarket_client",
                    "event": "market_order_created",
                    "token_id": token_id,
                    "order_id": resp.get("id") if isinstance(resp, dict) else None
                }
            )
            
            return resp
        except Exception as e:
            _log_http_error(e, "polymarket_client_wrapper.py:360", "E", {"operation": "create_market_order", "token_id": token_id})
            logger.error(f"Error creating market order: {e}", exc_info=True)
            raise
    
    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """
        Cancela una orden en Polymarket.
        
        Según documentación: DELETE /order con payload {"orderID": "..."}
        
        Args:
            order_id: ID de la orden a cancelar
        
        Returns:
            Respuesta de Polymarket con formato:
            {
                "canceled": [order_ids],
                "not_canceled": {order_id: reason}
            }
        """
        if not self.is_available():
            raise RuntimeError("Polymarket CLOB client not initialized")
        
        try:
            # Wait for rate limit capacity (CLOB DELETE /order: 2400 req / 10s burst, 24000 req / 10min sustained)
            if not await rate_limiter.wait_for_capacity(EndpointType.CLOB_DELETE_ORDER, timeout=5.0):
                logger.warning("Rate limit timeout for CLOB_DELETE_ORDER")
                raise RuntimeError("Rate limit exceeded for CLOB DELETE /order endpoint")
            
            client = self.get_client()
            resp = client.cancel(order_id=order_id)
            
            # La respuesta puede venir en diferentes formatos
            # Normalizar a formato estándar
            if isinstance(resp, dict):
                canceled = resp.get("canceled", [])
                not_canceled = resp.get("not_canceled", {})
                
                # Verificar si la orden fue cancelada
                if order_id in canceled or (isinstance(canceled, list) and order_id in canceled):
                    logger.info(
                        f"Order cancelled successfully: order_id={order_id}",
                        extra={
                            "component": "polymarket_client",
                            "event": "order_cancelled",
                            "order_id": order_id,
                            "status": "canceled"
                        }
                    )
                elif order_id in not_canceled:
                    reason = not_canceled[order_id]
                    logger.warning(
                        f"Order could not be cancelled: order_id={order_id}, reason={reason}",
                        extra={
                            "component": "polymarket_client",
                            "event": "order_cancel_failed",
                            "order_id": order_id,
                            "reason": reason
                        }
                    )
            else:
                # Si la respuesta no es dict, asumir éxito
                logger.info(
                    f"Order cancelled: order_id={order_id}",
                    extra={
                        "component": "polymarket_client",
                        "event": "order_cancelled",
                        "order_id": order_id
                    }
                )
            
            return resp if isinstance(resp, dict) else {"canceled": [order_id], "not_canceled": {}}
        except Exception as e:
            _log_http_error(e, "polymarket_client_wrapper.py:429", "F", {"operation": "cancel_order", "order_id": order_id})
            logger.error(f"Error cancelling order {order_id}: {e}", exc_info=True)
            raise
    
    def cancel_all_orders(self) -> Dict[str, Any]:
        """
        Cancela todas las órdenes abiertas.
        
        Según documentación: DELETE /orders (cancel all)
        
        Returns:
            Respuesta de Polymarket con formato:
            {
                "canceled": [order_ids],
                "not_canceled": {order_id: reason}
            }
        """
        if not self.is_available():
            raise RuntimeError("Polymarket CLOB client not initialized")
        
        try:
            client = self.get_client()
            resp = client.cancel_all()
            
            # Normalizar respuesta
            if isinstance(resp, dict):
                canceled = resp.get("canceled", [])
                not_canceled = resp.get("not_canceled", {})
                
                logger.info(
                    f"Cancel all orders: {len(canceled)} canceled, {len(not_canceled)} failed",
                    extra={
                        "component": "polymarket_client",
                        "event": "all_orders_cancelled",
                        "canceled_count": len(canceled) if isinstance(canceled, list) else 0,
                        "not_canceled_count": len(not_canceled) if isinstance(not_canceled, dict) else 0
                    }
                )
            else:
                logger.info(
                    "All orders cancelled",
                    extra={
                        "component": "polymarket_client",
                        "event": "all_orders_cancelled"
                    }
                )
            
            return resp if isinstance(resp, dict) else {"canceled": [], "not_canceled": {}}
        except Exception as e:
            _log_http_error(e, "polymarket_client_wrapper.py:477", "G", {"operation": "cancel_all_orders"})
            logger.error(f"Error cancelling all orders: {e}", exc_info=True)
            raise
    
    def get_open_orders(
        self, 
        order_id: Optional[str] = None,
        market: Optional[str] = None,
        asset_id: Optional[str] = None,
        token_id: Optional[str] = None  # Alias para asset_id por compatibilidad
    ) -> List[Dict[str, Any]]:
        """
        Obtiene órdenes abiertas con filtros opcionales.
        
        Según documentación: GET /data/orders
        
        Args:
            order_id: Opcional, ID de orden específica
            market: Opcional, condition_id del mercado
            asset_id: Opcional, ID del asset/token
            token_id: Opcional, alias para asset_id (por compatibilidad)
        
        Returns:
            Lista de órdenes abiertas (OpenOrder[])
        """
        if not self.is_available():
            raise RuntimeError("Polymarket CLOB client not initialized")
        
        try:
            from py_clob_client.clob_types import OpenOrderParams
            
            client = self.get_client()
            params = OpenOrderParams()
            
            # Aplicar filtros según documentación
            if order_id:
                params.id = order_id
            if market:
                params.market = market
            if asset_id:
                params.asset_id = asset_id
            elif token_id:
                # token_id es alias para asset_id (compatibilidad hacia atrás)
                params.asset_id = token_id
            
            orders = client.get_orders(params)
            
            logger.debug(
                f"Retrieved {len(orders) if isinstance(orders, list) else 0} open orders",
                extra={
                    "component": "polymarket_client",
                    "event": "orders_retrieved",
                    "filters": {
                        "order_id": order_id,
                        "market": market,
                        "asset_id": asset_id or token_id
                    }
                }
            )
            
            return orders if isinstance(orders, list) else []
        except Exception as e:
            _log_http_error(e, "polymarket_client_wrapper.py:536", "H", {"operation": "get_open_orders"})
            logger.error(f"Error getting open orders: {e}", exc_info=True)
            raise
    
    def get_order_book(self, token_id: str) -> Dict[str, Any]:
        """
        Obtiene el orderbook para un token.
        
        Args:
            token_id: ID del token
        
        Returns:
            Orderbook data
        """
        if not self.is_available():
            raise RuntimeError("Polymarket CLOB client not initialized")
        
        try:
            client = self.get_client()
            book = client.get_order_book(token_id)
            return book
        except Exception as e:
            logger.error(f"Error getting orderbook for {token_id}: {e}", exc_info=True)
            raise
    
    def get_price(self, token_id: str, side: str = "BUY") -> float:
        """
        Obtiene el precio para un token.
        
        Args:
            token_id: ID del token
            side: "BUY" o "SELL"
        
        Returns:
            Precio del token
        """
        if not self.is_available():
            raise RuntimeError("Polymarket CLOB client not initialized")
        
        try:
            client = self.get_client()
            price = client.get_price(token_id, side=side)
            return float(price) if price else 0.0
        except Exception as e:
            logger.error(f"Error getting price for {token_id}: {e}", exc_info=True)
            return 0.0
    
    def get_midpoint(self, token_id: str) -> float:
        """
        Obtiene el precio medio (midpoint) para un token.
        
        Args:
            token_id: ID del token
        
        Returns:
            Precio medio del token
        """
        if not self.is_available():
            raise RuntimeError("Polymarket CLOB client not initialized")
        
        try:
            client = self.get_client()
            mid = client.get_midpoint(token_id)
            return float(mid) if mid else 0.0
        except Exception as e:
            logger.error(f"Error getting midpoint for {token_id}: {e}", exc_info=True)
            return 0.0
    
    def get_order(self, order_hash: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene información de una orden específica por order_hash.
        
        Args:
            order_hash: Hash o ID de la orden
        
        Returns:
            Información de la orden (OpenOrder) o None si no existe
        """
        if not self.is_available():
            raise RuntimeError("Polymarket CLOB client not initialized")
        
        try:
            client = self.get_client()
            order = client.get_order(order_hash)
            
            logger.debug(
                f"Retrieved order: {order_hash}",
                extra={
                    "component": "polymarket_client",
                    "event": "order_retrieved",
                    "order_hash": order_hash,
                    "order_status": order.get("status") if isinstance(order, dict) else None
                }
            )
            
            return order if isinstance(order, dict) else None
        except Exception as e:
            logger.error(f"Error getting order {order_hash}: {e}", exc_info=True)
            return None
    
    def is_order_scoring(self, order_id: str) -> Optional[bool]:
        """
        Verifica si una orden está "scoring" (elegible para recompensas).
        
        Según documentación: GET /order-scoring?order_id={...}
        
        Args:
            order_id: ID de la orden a verificar
        
        Returns:
            True si la orden está scoring, False si no, None si hay error
        """
        if not self.is_available():
            raise RuntimeError("Polymarket CLOB client not initialized")
        
        try:
            from py_clob_client.clob_types import OrderScoringParams
            
            client = self.get_client()
            params = OrderScoringParams(orderId=order_id)
            result = client.is_order_scoring(params)
            
            # El resultado puede ser un dict con {"scoring": bool} o directamente bool
            if isinstance(result, dict):
                scoring = result.get("scoring", False)
            else:
                scoring = bool(result) if result is not None else False
            
            logger.debug(
                f"Order scoring check: {order_id} = {scoring}",
                extra={
                    "component": "polymarket_client",
                    "event": "order_scoring_check",
                    "order_id": order_id,
                    "scoring": scoring
                }
            )
            
            return scoring
        except Exception as e:
            logger.error(f"Error checking order scoring for {order_id}: {e}", exc_info=True)
            return None
    
    def are_orders_scoring(self, order_ids: List[str]) -> Dict[str, bool]:
        """
        Verifica si múltiples órdenes están "scoring" (elegibles para recompensas).
        
        Según documentación: POST /orders-scoring
        
        Args:
            order_ids: Lista de IDs de órdenes a verificar
        
        Returns:
            Dict con {order_id: scoring} para cada orden
        """
        if not self.is_available():
            raise RuntimeError("Polymarket CLOB client not initialized")
        
        try:
            from py_clob_client.clob_types import OrdersScoringParams
            
            client = self.get_client()
            params = OrdersScoringParams(orderIds=order_ids)
            result = client.are_orders_scoring(params)
            
            # El resultado debería ser un dict con {order_id: {"scoring": bool}} o {order_id: bool}
            scoring_dict = {}
            if isinstance(result, dict):
                for order_id, scoring_data in result.items():
                    if isinstance(scoring_data, dict):
                        scoring_dict[order_id] = scoring_data.get("scoring", False)
                    else:
                        scoring_dict[order_id] = bool(scoring_data) if scoring_data is not None else False
            else:
                # Si no es dict, crear dict vacío
                logger.warning(f"Unexpected result format from are_orders_scoring: {type(result)}")
            
            logger.debug(
                f"Checked scoring for {len(scoring_dict)} orders",
                extra={
                    "component": "polymarket_client",
                    "event": "orders_scoring_check",
                    "order_count": len(order_ids),
                    "scoring_count": sum(1 for v in scoring_dict.values() if v)
                }
            )
            
            return scoring_dict
        except Exception as e:
            logger.error(f"Error checking orders scoring: {e}", exc_info=True)
            return {}
    
    async def get_balance(self) -> Optional[float]:
        """
        Obtiene el balance USDC de la cuenta en Polymarket.
        
        Usa getBalanceAllowance() con AssetType.COLLATERAL para obtener el balance USDC.
        
        Returns:
            Balance en USDC o None si hay error o el cliente no está disponible
        """
        # #region agent log
        import json
        import time
        with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"polymarket_client_wrapper.py:648","message":"get_balance ENTRY","data":{"is_available":self.is_available()},"timestamp":int(time.time()*1000)})+"\n")
        # #endregion
        
        if not self.is_available():
            logger.warning("Polymarket CLOB client not initialized, cannot get balance")
            return None
        
        try:
            client = self.get_client()
            
            # #region agent log
            client_methods = [m for m in dir(client) if not m.startswith('_')]
            has_getBalanceAllowance = hasattr(client, 'getBalanceAllowance')
            has_get_balance_allowance = hasattr(client, 'get_balance_allowance')
            # Buscar métodos relacionados con balance
            balance_methods = [m for m in client_methods if 'balance' in m.lower() or 'allowance' in m.lower() or 'account' in m.lower() or 'user' in m.lower()]
            with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"polymarket_client_wrapper.py:815","message":"Client methods available","data":{"has_getBalanceAllowance":has_getBalanceAllowance,"has_get_balance_allowance":has_get_balance_allowance,"has_get_balance":hasattr(client, 'get_balance'),"has_get_user":hasattr(client, 'get_user'),"has_get_account":hasattr(client, 'get_account'),"methods_count":len(client_methods),"balance_related_methods":balance_methods,"all_methods":client_methods[:20]},"timestamp":int(time.time()*1000)})+"\n")
            # #endregion
            
            # Usar get_balance_allowance() (snake_case) - el método real en Python
            if has_get_balance_allowance:
                try:
                    # #region agent log
                    with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"polymarket_client_wrapper.py:825","message":"Trying get_balance_allowance()","data":{"asset_type":"COLLATERAL"},"timestamp":int(time.time()*1000)})+"\n")
                    # #endregion
                    
                    # Wait for rate limit capacity (CLOB GET Balance Allowance: 125 req / 10s)
                    if not await rate_limiter.wait_for_capacity(EndpointType.CLOB_BALANCE_ALLOWANCE_GET, timeout=5.0):
                        logger.warning("Rate limit timeout for CLOB_BALANCE_ALLOWANCE_GET")
                        # #region agent log
                        with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
                            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"polymarket_client_wrapper.py:830","message":"Rate limit timeout","data":{"endpoint":"CLOB_BALANCE_ALLOWANCE_GET"},"timestamp":int(time.time()*1000)})+"\n")
                        # #endregion
                        return None
                    
                    # Importar AssetType y BalanceAllowanceParams desde py_clob_client
                    try:
                        from py_clob_client.clob_types import AssetType, BalanceAllowanceParams
                    except ImportError:
                        # Si no está disponible, usar string directamente
                        AssetType = type('AssetType', (), {'COLLATERAL': 'COLLATERAL'})()
                        BalanceAllowanceParams = None
                    
                    # Crear parámetros para get_balance_allowance
                    if BalanceAllowanceParams:
                        # Usar el tipo BalanceAllowanceParams si está disponible
                        params = BalanceAllowanceParams(
                            asset_type=AssetType.COLLATERAL if hasattr(AssetType, 'COLLATERAL') else 'COLLATERAL'
                        )
                    else:
                        # Fallback: usar dict
                        params = {
                            'asset_type': AssetType.COLLATERAL if hasattr(AssetType, 'COLLATERAL') else 'COLLATERAL'
                        }
                    
                    # #region agent log
                    with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"polymarket_client_wrapper.py:848","message":"Calling get_balance_allowance","data":{"params_type":type(params).__name__,"params":str(params)},"timestamp":int(time.time()*1000)})+"\n")
                    # #endregion
                    
                    # Llamar a get_balance_allowance con AssetType.COLLATERAL para obtener balance USDC
                    # NOTA: get_balance_allowance() NO es async, devuelve un dict directamente
                    result = client.get_balance_allowance(params)
                    
                    # #region agent log
                    with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"polymarket_client_wrapper.py:843","message":"get_balance_allowance() result","data":{"result_type":type(result).__name__,"is_dict":isinstance(result, dict),"result_keys":list(result.keys()) if isinstance(result, dict) else None,"result":str(result) if not isinstance(result, dict) else None},"timestamp":int(time.time()*1000)})+"\n")
                    # #endregion
                    
                    # El resultado debería tener 'balance' como string
                    if isinstance(result, dict):
                        balance_str = result.get('balance')
                        # #region agent log
                        with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
                            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"polymarket_client_wrapper.py:893","message":"Raw balance_str from API","data":{"balance_str":balance_str,"balance_str_type":type(balance_str).__name__,"result_keys":list(result.keys()),"full_result":str(result)[:200]},"timestamp":int(time.time()*1000)})+"\n")
                        # #endregion
                        if balance_str:
                            # El balance puede venir como string con formato "27993114" (sin decimales) o "27.99" o "279931140000000000000000" (wei)
                            # Necesitamos verificar si viene en wei (18 decimales) o en unidades normales
                            try:
                                # Intentar parsear como float directamente
                                balance_raw = float(balance_str)
                                # #region agent log
                                with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
                                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"polymarket_client_wrapper.py:900","message":"Parsed balance_raw","data":{"balance_raw":balance_raw,"balance_str":balance_str},"timestamp":int(time.time()*1000)})+"\n")
                                # #endregion
                                
                                # USDC tiene 6 decimales. El balance viene como string en unidades más pequeñas.
                                # Por ejemplo, "27993114" representa 27.993114 USDC (dividir por 1e6)
                                # Si el balance es >= 1, probablemente está en unidades más pequeñas
                                # Dividir siempre por 1e6 para convertir a USDC
                                balance = balance_raw / 1_000_000
                                # #region agent log
                                with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
                                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"polymarket_client_wrapper.py:912","message":"Balance converted from raw units to USDC","data":{"balance_raw":balance_raw,"balance_usdc":balance},"timestamp":int(time.time()*1000)})+"\n")
                                # #endregion
                                
                                # #region agent log
                                with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
                                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"polymarket_client_wrapper.py:901","message":"Final balance returned","data":{"balance":balance,"balance_str":balance_str},"timestamp":int(time.time()*1000)})+"\n")
                                # #endregion
                                return balance
                            except (ValueError, TypeError) as e:
                                logger.error(f"Error parsing balance string '{balance_str}': {e}")
                                # #region agent log
                                with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
                                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"polymarket_client_wrapper.py:920","message":"Error parsing balance","data":{"balance_str":balance_str,"error":str(e)},"timestamp":int(time.time()*1000)})+"\n")
                                # #endregion
                                return None
                    elif hasattr(result, 'balance'):
                        balance_str = result.balance
                        if balance_str:
                            balance = float(balance_str)
                            return balance
                    
                    logger.warning(f"get_balance_allowance() returned unexpected format: {type(result)}")
                    # #region agent log
                    with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"polymarket_client_wrapper.py:864","message":"Unexpected result format","data":{"result_type":type(result).__name__},"timestamp":int(time.time()*1000)})+"\n")
                    # #endregion
                except Exception as e:
                    _log_http_error(e, "polymarket_client_wrapper.py:867", "B", {"operation": "get_balance_allowance", "asset_type": "COLLATERAL"})
            # También intentar getBalanceAllowance() (camelCase) por si acaso
            elif has_getBalanceAllowance:
                try:
                    # #region agent log
                    with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"polymarket_client_wrapper.py:669","message":"Trying getBalanceAllowance()","data":{"asset_type":"COLLATERAL"},"timestamp":int(time.time()*1000)})+"\n")
                    # #endregion
                    
                    # Importar AssetType desde py_clob_client
                    try:
                        from py_clob_client.clob_types import AssetType
                    except ImportError:
                        # Si no está disponible, usar string directamente
                        AssetType = type('AssetType', (), {'COLLATERAL': 'COLLATERAL'})()
                    
                    # Llamar a getBalanceAllowance con AssetType.COLLATERAL para obtener balance USDC
                    # NOTA: getBalanceAllowance() NO es async, devuelve un dict directamente
                    result = client.getBalanceAllowance({
                        'asset_type': AssetType.COLLATERAL if hasattr(AssetType, 'COLLATERAL') else 'COLLATERAL'
                    })
                    
                    # #region agent log
                    with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"polymarket_client_wrapper.py:683","message":"getBalanceAllowance() result","data":{"result_type":type(result).__name__,"is_dict":isinstance(result, dict),"result_keys":list(result.keys()) if isinstance(result, dict) else None,"result":str(result) if not isinstance(result, dict) else None},"timestamp":int(time.time()*1000)})+"\n")
                    # #endregion
                    
                    # El resultado debería tener 'balance' como string
                    if isinstance(result, dict):
                        balance_str = result.get('balance')
                        # #region agent log
                        with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
                            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"polymarket_client_wrapper.py:970","message":"Raw balance_str from getBalanceAllowance","data":{"balance_str":balance_str,"balance_str_type":type(balance_str).__name__,"result_keys":list(result.keys()),"full_result":str(result)[:200]},"timestamp":int(time.time()*1000)})+"\n")
                        # #endregion
                        if balance_str:
                            try:
                                balance_raw = float(balance_str)
                                # USDC tiene 6 decimales. Dividir siempre por 1e6 para convertir a USDC
                                balance = balance_raw / 1_000_000
                                # #region agent log
                                with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
                                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"polymarket_client_wrapper.py:978","message":"Balance converted from raw units to USDC (getBalanceAllowance)","data":{"balance_raw":balance_raw,"balance_usdc":balance},"timestamp":int(time.time()*1000)})+"\n")
                                # #endregion
                                return balance
                            except (ValueError, TypeError) as e:
                                logger.error(f"Error parsing balance string '{balance_str}': {e}")
                                return None
                    elif hasattr(result, 'balance'):
                        balance_str = result.balance
                        if balance_str:
                            try:
                                balance_raw = float(balance_str)
                                # USDC tiene 6 decimales. Dividir siempre por 1e6 para convertir a USDC
                                balance = balance_raw / 1_000_000
                                return balance
                            except (ValueError, TypeError) as e:
                                logger.error(f"Error parsing balance string '{balance_str}': {e}")
                                return None
                    
                    logger.warning(f"getBalanceAllowance() returned unexpected format: {type(result)}")
                    # #region agent log
                    with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"polymarket_client_wrapper.py:704","message":"Unexpected result format","data":{"result_type":type(result).__name__},"timestamp":int(time.time()*1000)})+"\n")
                    # #endregion
                except Exception as e:
                    _log_http_error(e, "polymarket_client_wrapper.py:809", "B", {"operation": "getBalanceAllowance", "asset_type": "COLLATERAL"})
            
            # Intentar métodos alternativos
            # #region agent log
            with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"polymarket_client_wrapper.py:815","message":"Trying alternative methods","data":{"balance_methods":balance_methods},"timestamp":int(time.time()*1000)})+"\n")
            # #endregion
            
            # Intentar llamar métodos relacionados con balance si existen
            for method_name in balance_methods:
                try:
                    method = getattr(client, method_name)
                    # #region agent log
                    with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"polymarket_client_wrapper.py:821","message":"Trying method","data":{"method_name":method_name},"timestamp":int(time.time()*1000)})+"\n")
                    # #endregion
                    
                    # Intentar llamar el método (puede ser sync o async)
                    if callable(method):
                        try:
                            # Intentar como async primero
                            if hasattr(method, '__call__'):
                                import inspect
                                if inspect.iscoroutinefunction(method):
                                    result = await method()
                                else:
                                    result = method()
                                
                                # #region agent log
                                with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
                                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"polymarket_client_wrapper.py:834","message":"Method result","data":{"method_name":method_name,"result_type":type(result).__name__,"is_dict":isinstance(result, dict),"result_keys":list(result.keys()) if isinstance(result, dict) else None},"timestamp":int(time.time()*1000)})+"\n")
                                # #endregion
                                
                                # Buscar balance en el resultado
                                if isinstance(result, dict):
                                    balance_str = result.get('balance') or result.get('usdc_balance') or result.get('available_balance') or result.get('availableUsdc')
                                    if balance_str:
                                        balance = float(balance_str)
                                        logger.info(f"Got balance using {method_name}: {balance}")
                                        return balance
                        except Exception as method_error:
                            # #region agent log
                            with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
                                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"polymarket_client_wrapper.py:847","message":"Method failed","data":{"method_name":method_name,"error":str(method_error)},"timestamp":int(time.time()*1000)})+"\n")
                            # #endregion
                            continue
                except Exception as e:
                    continue
            
            # Si no hay métodos directos, usar la API REST directamente
            # Intentar usar el cliente interno para hacer requests HTTP
            try:
                # #region agent log
                with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"polymarket_client_wrapper.py:858","message":"Trying API REST directly","data":{},"timestamp":int(time.time()*1000)})+"\n")
                # #endregion
                
                # El cliente CLOB debería tener un método para hacer requests HTTP autenticados
                # Intentar acceder al cliente HTTP interno
                if hasattr(client, '_get') or hasattr(client, 'get'):
                    import httpx
                    from app.settings import settings
                    
                    base_url = settings.polymarket_trading_api_url or "https://clob.polymarket.com"
                    
                    # Intentar diferentes endpoints posibles
                    endpoints_to_try = [
                        "/balance",
                        "/user/balance",
                        "/account/balance",
                        "/user",
                        "/account"
                    ]
                    
                    for endpoint in endpoints_to_try:
                        try:
                            url = f"{base_url}{endpoint}"
                            # #region agent log
                            with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
                                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"polymarket_client_wrapper.py:878","message":"Trying endpoint","data":{"endpoint":endpoint,"url":url},"timestamp":int(time.time()*1000)})+"\n")
                            # #endregion
                            
                            # Usar el método interno del cliente si está disponible
                            if hasattr(client, '_get'):
                                response = await client._get(endpoint) if inspect.iscoroutinefunction(client._get) else client._get(endpoint)
                            elif hasattr(client, 'get'):
                                response = await client.get(endpoint) if inspect.iscoroutinefunction(client.get) else client.get(endpoint)
                            else:
                                # Hacer request directo con httpx usando credenciales del cliente
                                headers = {}
                                if hasattr(client, 'api_creds') and client.api_creds:
                                    if hasattr(client.api_creds, 'apiKey'):
                                        headers['Authorization'] = f"Bearer {client.api_creds.apiKey}"
                                
                                if headers:
                                    async with httpx.AsyncClient() as http_client:
                                        response = await http_client.get(url, headers=headers, timeout=10.0)
                                        response.raise_for_status()
                                        response = response.json()
                                else:
                                    continue
                            
                            # #region agent log
                            with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
                                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"polymarket_client_wrapper.py:900","message":"Endpoint response","data":{"endpoint":endpoint,"response_type":type(response).__name__,"is_dict":isinstance(response, dict),"response_keys":list(response.keys()) if isinstance(response, dict) else None},"timestamp":int(time.time()*1000)})+"\n")
                            # #endregion
                            
                            # Buscar balance en la respuesta
                            if isinstance(response, dict):
                                balance_str = response.get('balance') or response.get('usdc_balance') or response.get('available_balance') or response.get('availableUsdc') or response.get('available_usdc')
                                if balance_str:
                                    balance = float(balance_str)
                                    logger.info(f"Got balance from {endpoint}: {balance}")
                                    return balance
                        except Exception as endpoint_error:
                            _log_http_error(endpoint_error, f"polymarket_client_wrapper.py:endpoint_{endpoint}", "D", {"endpoint": endpoint})
                            continue
            except Exception as api_error:
                _log_http_error(api_error, "polymarket_client_wrapper.py:858", "D", {"operation": "API_REST_direct"})
            
            logger.warning("get_balance_allowance() method not available on ClobClient and no alternative methods found")
            # #region agent log
            with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"F","location":"polymarket_client_wrapper.py:1038","message":"get_balance FAILED - no methods found","data":{"balance_methods":balance_methods,"has_get_balance_allowance":has_get_balance_allowance},"timestamp":int(time.time()*1000)})+"\n")
            # #endregion
            return None
        except Exception as e:
            _log_http_error(e, "polymarket_client_wrapper.py:855", "F", {"operation": "get_balance"})
            logger.error(f"Error getting balance from Polymarket: {e}", exc_info=True)
            return None
    
    async def get_trades(
        self,
        trade_id: Optional[str] = None,
        taker: Optional[str] = None,
        maker: Optional[str] = None,
        market: Optional[str] = None,
        before: Optional[str] = None,
        after: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Obtiene trades históricos con filtros opcionales.
        
        Según documentación: GET /data/trades
        
        Un trade puede estar en varios estados:
        - MATCHED: trade ha sido matcheado y enviado al executor service
        - MINED: trade observado en la blockchain, sin finalidad establecida
        - CONFIRMED: trade ha alcanzado finalidad probabilística fuerte (terminal)
        - RETRYING: transacción falló y está siendo reintentada
        - FAILED: trade falló y no se está reintentando (terminal)
        
        Nota: En algunos casos, un trade puede ser dividido en múltiples transacciones
        debido a limitaciones de gas. Estos trades pueden ser reconciliados usando
        market_order_id, match_time y bucket_index.
        
        Args:
            trade_id: Opcional, ID del trade específico
            taker: Opcional, address del taker para filtrar trades donde es taker
            maker: Opcional, address del maker para filtrar trades donde es maker
            market: Opcional, condition ID del mercado
            before: Opcional, unix timestamp (string) - trades antes de este tiempo
            after: Opcional, unix timestamp (string) - trades después de este tiempo
        
        Returns:
            Lista de trades (Trade[]) con formato:
            {
                "id": str,
                "taker_order_id": str,
                "market": str (condition_id),
                "asset_id": str (token_id),
                "side": str ("buy" o "sell"),
                "size": str,
                "fee_rate_bps": str,
                "price": str,
                "status": str (MATCHED, MINED, CONFIRMED, RETRYING, FAILED),
                "match_time": str,
                "last_update": str,
                "outcome": str,
                "maker_address": str,
                "owner": str,
                "transaction_hash": str,
                "bucket_index": int,
                "maker_orders": [MakerOrder],
                "type": str ("TAKER" o "MAKER")
            }
        """
        if not self.is_available():
            raise RuntimeError("Polymarket CLOB client not initialized")
        
        try:
            # Wait for rate limit capacity (CLOB Ledger /data/trades: 150 req / 10s)
            if not await rate_limiter.wait_for_capacity(EndpointType.CLOB_LEDGER_DATA_TRADES, timeout=5.0):
                logger.warning("Rate limit timeout for CLOB_LEDGER_DATA_TRADES")
                raise RuntimeError("Rate limit exceeded for CLOB trades endpoint")
            
            from py_clob_client.clob_types import TradeParams
            
            client = self.get_client()
            params = TradeParams()
            
            # Aplicar filtros según documentación
            if trade_id:
                params.id = trade_id
            if taker:
                params.taker = taker
            if maker:
                params.maker = maker
            if market:
                params.market = market
            if before:
                params.before = before
            if after:
                params.after = after
            
            trades = client.get_trades(params)
            
            logger.debug(
                f"Retrieved {len(trades) if isinstance(trades, list) else 0} trades",
                extra={
                    "component": "polymarket_client",
                    "event": "trades_retrieved",
                    "filters": {
                        "trade_id": trade_id,
                        "taker": taker,
                        "maker": maker,
                        "market": market,
                        "before": before,
                        "after": after
                    },
                    "trade_count": len(trades) if isinstance(trades, list) else 0
                }
            )
            
            return trades if isinstance(trades, list) else []
        except Exception as e:
            _log_http_error(e, "polymarket_client_wrapper.py:962", "I", {"operation": "get_trades"})
            logger.error(f"Error getting trades: {e}", exc_info=True)
            raise


# Instancia global del wrapper
_polymarket_client_wrapper: Optional[PolymarketCLOBWrapper] = None


def get_polymarket_client() -> PolymarketCLOBWrapper:
    """
    Obtiene la instancia global del wrapper del cliente de Polymarket.
    
    Returns:
        Instancia de PolymarketCLOBWrapper
    """
    global _polymarket_client_wrapper
    # #region agent log
    import json
    with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"polymarket_client_wrapper.py:709","message":"get_polymarket_client ENTRY","data":{"instance_exists":_polymarket_client_wrapper is not None},"timestamp":int(__import__('time').time()*1000)})+"\n")
    # #endregion
    if _polymarket_client_wrapper is None:
        logger.info("get_polymarket_client - Creando nueva instancia de PolymarketCLOBWrapper...")
        # #region agent log
        with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"polymarket_client_wrapper.py:718","message":"BEFORE PolymarketCLOBWrapper()","data":{},"timestamp":int(__import__('time').time()*1000)})+"\n")
        # #endregion
        _polymarket_client_wrapper = PolymarketCLOBWrapper()
        # #region agent log
        with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"polymarket_client_wrapper.py:719","message":"AFTER PolymarketCLOBWrapper()","data":{},"timestamp":int(__import__('time').time()*1000)})+"\n")
        # #endregion
    # #region agent log
    with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"polymarket_client_wrapper.py:720","message":"get_polymarket_client EXIT","data":{},"timestamp":int(__import__('time').time()*1000)})+"\n")
    # #endregion
    return _polymarket_client_wrapper

