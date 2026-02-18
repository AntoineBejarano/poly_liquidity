"""
PS3838 API client and utilities.

Lines API: fixtures, odds.
Bets API: place bet.
Match resolution: tip parseado → eventId/lineId/odds.
Auth: HTTP Basic. Rate limits: snapshot 1/60s per sport, delta 1/5s per sport.
"""
from app.core.ps3838.client import PS3838Client
from app.core.ps3838.match_resolution import resolve_tip_to_ps3838

__all__ = ["PS3838Client", "resolve_tip_to_ps3838"]
