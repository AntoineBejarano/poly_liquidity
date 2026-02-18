"""
PS3838 API client - Lines API and Bets API.

- Auth: HTTP Basic (username, password).
- Lines API: Get Fixtures /v3/fixtures, Get Odds /v4/odds.
- Bets API: Place Bet with uniqueRequestId for idempotency.
- Rate limits: snapshot (no since) 1/60s per sport, delta (with since) 1/5s per sport.
"""
import logging
import uuid
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

# Default base URL for PS3838 API (configurable via connector_config)
DEFAULT_PS3838_BASE_URL = "https://api.ps3838.com"


class PS3838ClientError(Exception):
    """Error from PS3838 client."""
    pass


class PS3838Client:
    """
    Cliente HTTP para PS3838 Lines API y Bets API.
    """

    def __init__(
        self,
        username: str,
        password: str,
        base_url: Optional[str] = None,
        timeout_seconds: float = 30.0,
    ):
        self.username = username
        self.password = password
        self.base_url = (base_url or DEFAULT_PS3838_BASE_URL).rstrip("/")
        self.timeout = timeout_seconds

    def _auth_header(self) -> str:
        """HTTP Basic auth header value."""
        import base64
        credentials = f"{self.username}:{self.password}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"

    async def get_fixtures(
        self,
        sport_id: Optional[int] = None,
        since: Optional[str] = None,
        **params: Any,
    ) -> Dict[str, Any]:
        """
        Get Fixtures (Lines API) - lista de eventos ofrecidos.
        Rate: snapshot 1/60s por deporte, delta 1/5s por deporte.
        """
        url = f"{self.base_url}/v3/fixtures"
        query: Dict[str, Any] = dict(params)
        if sport_id is not None:
            query["sportId"] = sport_id
        if since is not None:
            query["since"] = since
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.get(
                url,
                params=query,
                headers={
                    "Authorization": self._auth_header(),
                    "Accept": "application/json",
                },
            )
            r.raise_for_status()
            return r.json()

    async def get_odds(
        self,
        sport_id: Optional[int] = None,
        since: Optional[str] = None,
        **params: Any,
    ) -> Dict[str, Any]:
        """
        Get Odds (Lines API) - cuotas ofrecidas.
        Rate: snapshot 1/60s por deporte, delta 1/5s por deporte.
        """
        url = f"{self.base_url}/v4/odds"
        query: Dict[str, Any] = dict(params)
        if sport_id is not None:
            query["sportId"] = sport_id
        if since is not None:
            query["since"] = since
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.get(
                url,
                params=query,
                headers={
                    "Authorization": self._auth_header(),
                    "Accept": "application/json",
                },
            )
            r.raise_for_status()
            return r.json()

    async def verify_credentials(self) -> None:
        """
        Verifica que las credenciales son válidas haciendo una llamada ligera a la API.
        Raises PS3838ClientError si las credenciales son incorrectas o la API no responde.
        """
        url = f"{self.base_url}/v3/fixtures"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.get(
                url,
                params={"sportId": 1},
                headers={
                    "Authorization": self._auth_header(),
                    "Accept": "application/json",
                },
            )
            if r.status_code == 401:
                raise PS3838ClientError("Usuario o contraseña API incorrectos. Revisa las credenciales en tu cuenta.")
            if r.status_code == 403:
                raise PS3838ClientError("Acceso denegado. Verifica que tu cuenta tenga acceso a la API.")
            r.raise_for_status()

    async def place_bet(
        self,
        payload: Dict[str, Any],
        unique_request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Place Bet (Bets API).
        unique_request_id: idempotency key (server keeps ~30 min). If not provided, one is generated.
        """
        url = f"{self.base_url}/v1/bets"
        request_id = unique_request_id or str(uuid.uuid4())
        headers = {
            "Authorization": self._auth_header(),
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Unique-Request-Id": request_id,
        }
        body = dict(payload)
        if "uniqueRequestId" not in body:
            body["uniqueRequestId"] = request_id
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.post(url, json=body, headers=headers)
            r.raise_for_status()
            return r.json()
