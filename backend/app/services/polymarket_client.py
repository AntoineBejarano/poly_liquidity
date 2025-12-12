"""
Polymarket API client for fetching market data.
"""
import httpx
from typing import Dict, Any, Optional
from app.settings import settings
import logging

logger = logging.getLogger(__name__)


class PolymarketClient:
    """Client for Polymarket API interactions."""
    
    def __init__(self):
        self.base_url = settings.polymarket_api_url
        self.api_key = settings.polymarket_api_key
        self.timeout = 10.0
    
    async def get_market(self, market_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch market data from Polymarket API.
        
        Args:
            market_id: The market ID to fetch
            
        Returns:
            Market data dictionary or None if error
        """
        try:
            url = f"{self.base_url}/markets/{market_id}"
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Error fetching Polymarket market {market_id}: {e}")
            return None
    
    async def get_market_state(self, market_id: str) -> Optional[str]:
        """
        Get the current state of a market (e.g., 'active', 'closed', 'resolved').
        
        Args:
            market_id: The market ID
            
        Returns:
            Market state string or None if error
        """
        market_data = await self.get_market(market_id)
        if not market_data:
            return None
        
        # Extract state from market data
        # Adjust this based on actual Polymarket API response structure
        return market_data.get("state") or market_data.get("status") or "unknown"


# Global instance
polymarket_client = PolymarketClient()

