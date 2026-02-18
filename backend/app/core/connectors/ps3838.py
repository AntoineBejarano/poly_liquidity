"""
PS3838 Connector - Conector para Lines API y Bets API de PS3838.

Config: username, password (o password_encrypted si se desencripta antes),
base_url (opcional), timeout_seconds.
"""
import logging
from typing import Any, Dict, Optional

from app.core.connectors.base import BaseConnector, ConnectorError
from app.core.ps3838.client import PS3838Client

logger = logging.getLogger(__name__)


class Ps3838Connector(BaseConnector):
    """
    Conector para PS3838 (Lines API + Bets API).
    Auth: HTTP Basic con username/password del connector_config.
    """

    async def fetch(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        method: str = "GET",
    ) -> Dict[str, Any]:
        """
        Llama a la API PS3838.
        endpoint: "/v3/fixtures", "/v4/odds", o "/v1/bets" (POST para place bet).
        params: query para GET; body para POST.
        """
        username = self.config.get("username")
        password = self.config.get("password")
        if not username or not password:
            raise ConnectorError("PS3838 connector requires username and password")
        base_url = self.config.get("base_url")
        timeout = self.get_timeout()
        client = PS3838Client(
            username=username,
            password=password,
            base_url=base_url,
            timeout_seconds=timeout,
        )
        params = params or {}
        if method.upper() == "GET":
            if "/v3/fixtures" in endpoint or endpoint == "/v3/fixtures":
                return await client.get_fixtures(**params)
            if "/v4/odds" in endpoint or endpoint == "/v4/odds":
                return await client.get_odds(**params)
            raise ConnectorError(f"Unknown GET endpoint for PS3838: {endpoint}")
        if method.upper() == "POST" and ("/v1/bets" in endpoint or endpoint == "/v1/bets"):
            return await client.place_bet(
                payload=params,
                unique_request_id=params.get("uniqueRequestId"),
            )
        raise ConnectorError(f"Unsupported endpoint/method for PS3838: {method} {endpoint}")

    async def health_check(self) -> Dict[str, Any]:
        """Verifica conectividad con Get Fixtures (sin since, snapshot)."""
        try:
            await self.fetch("/v3/fixtures", params={})
            return {"status": "healthy", "message": "PS3838 API reachable"}
        except ConnectorError as e:
            return {"status": "unhealthy", "message": str(e)}
        except Exception as e:
            return {"status": "unhealthy", "message": str(e)}
