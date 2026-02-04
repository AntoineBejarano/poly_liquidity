"""
Directory service: lectura de categories, tags, markets y events desde DB.

Phase 1 — Cache-first (DB-only). No realiza llamadas a Gamma.
Contrato de respuesta: last_scanned_at, freshness, source, data_age_seconds.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.market import Market
from app.models.event import Event
from app.models.tag import Tag
from app.models.market_tag import MarketTag
from app.models.market_enabled_state import MarketEnabledState

logger = logging.getLogger(__name__)

# Freshness: considerar "fresh" si el último scan fue hace menos de 5 minutos
FRESHNESS_THRESHOLD_SECONDS = 300


class DirectoryService:
    """
    Servicio de lectura del Directory (categories, tags, markets, events).
    Solo lee de DB; no llama a Gamma.
    """

    @staticmethod
    def get_meta(scanner: Any) -> Dict[str, Any]:
        """
        Meta del Directory: last_scanned_at, freshness, source, data_age_seconds.
        scanner: instancia con get_stats() o None.
        """
        last_scanned_at = None
        source = "db"
        data_age_seconds: Optional[float] = None
        freshness = "stale"

        if scanner is not None and hasattr(scanner, "get_stats"):
            try:
                stats = scanner.get_stats()
                last_scan = stats.get("last_scan")
                if last_scan:
                    if isinstance(last_scan, str):
                        try:
                            last_scanned_at = last_scan
                            dt = datetime.fromisoformat(last_scan.replace("Z", "+00:00"))
                        except ValueError:
                            dt = None
                        if dt:
                            age = (datetime.now(timezone.utc) - dt).total_seconds()
                            data_age_seconds = max(0, age)
                            freshness = "fresh" if data_age_seconds < FRESHNESS_THRESHOLD_SECONDS else "stale"
                    else:
                        last_scanned_at = last_scan.isoformat() if hasattr(last_scan, "isoformat") else str(last_scan)
            except Exception as e:
                logger.debug("Directory get_meta from scanner: %s", e)

        return {
            "last_scanned_at": last_scanned_at,
            "freshness": freshness,
            "source": source,
            "data_age_seconds": data_age_seconds,
        }

    @staticmethod
    def get_categories(db: Session) -> List[Dict[str, Any]]:
        """Lista categorías distintas desde Market (solo DB)."""
        rows = (
            db.query(Market.category)
            .filter(Market.category.isnot(None), Market.category != "")
            .distinct()
            .order_by(Market.category)
            .all()
        )
        return [{"category": r[0]} for r in rows]

    @staticmethod
    def get_tags(db: Session, limit: int = 200, offset: int = 0) -> tuple[List[Dict[str, Any]], int]:
        """Lista tags desde DB con paginación."""
        query = db.query(Tag).order_by(Tag.name)
        total = query.count()
        tags = query.offset(offset).limit(limit).all()
        return (
            [
                {
                    "tag_id": str(t.id),
                    "polymarket_tag_id": t.polymarket_tag_id,
                    "name": t.name,
                    "slug": t.slug,
                    "label": t.label,
                }
                for t in tags
            ],
            total,
        )

    @staticmethod
    def get_markets(
        db: Session,
        category: Optional[str] = None,
        tag_id: Optional[Union[str, UUID]] = None,
        search: Optional[str] = None,
        enabled: Optional[bool] = None,
        state: Optional[str] = None,
        next_days: Optional[int] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[List[Dict[str, Any]], int]:
        """
        Lista markets desde DB con filtros y paginación.
        enabled se resuelve vía MarketEnabledState; si no existe fila, se usa Market.enabled.
        state y next_days se aplican vía eventos del market (si state/next_days se pasan, filtramos markets que tengan al menos un event que cumpla).
        """
        base = db.query(Market).outerjoin(
            MarketEnabledState,
            Market.polymarket_id == MarketEnabledState.polymarket_market_id,
        )

        if category is not None:
            base = base.filter(Market.category == category)
        if search:
            base = base.filter(Market.name.ilike(f"%{search}%"))
        if tag_id is not None:
            tid = UUID(str(tag_id)) if isinstance(tag_id, str) else tag_id
            base = base.join(MarketTag).filter(MarketTag.tag_id == tid)

        if enabled is not None:
            base = base.filter(
                or_(
                    and_(
                        MarketEnabledState.polymarket_market_id.isnot(None),
                        MarketEnabledState.enabled == enabled,
                    ),
                    and_(
                        MarketEnabledState.polymarket_market_id.is_(None),
                        Market.enabled == enabled,
                    ),
                )
            )

        if state is not None or next_days is not None:
            subq = db.query(Event.market_id)
            if state is not None:
                subq = subq.filter(Event.state == state)
            if next_days is not None:
                from datetime import timedelta
                threshold = datetime.utcnow() + timedelta(days=next_days)
                subq = subq.filter(Event.end_time <= threshold)
            subq = subq.distinct().subquery()
            base = base.filter(Market.id.in_(subq))

        total = base.count()
        markets = base.order_by(Market.name).offset(offset).limit(limit).all()

        # Resolver enabled por market
        enabled_map = {r.polymarket_market_id: r.enabled for r in db.query(MarketEnabledState).all()}

        result = []
        for m in markets:
            is_enabled = enabled_map.get(m.polymarket_id, m.enabled)
            result.append({
                "market_id": str(m.id),
                "polymarket_id": m.polymarket_id,
                "name": m.name,
                "category": m.category,
                "enabled": is_enabled,
                "series_id": str(m.series_id) if m.series_id else None,
                "created_at": m.created_at.isoformat() if m.created_at else None,
                "updated_at": m.updated_at.isoformat() if m.updated_at else None,
            })
        return result, total

    @staticmethod
    def get_events(
        db: Session,
        market_id: Optional[Union[str, UUID]] = None,
        state: Optional[str] = None,
        category: Optional[str] = None,
        tag_id: Optional[Union[str, UUID]] = None,
        next_days: Optional[int] = None,
        max_time_to_resolution_minutes: Optional[int] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[List[Dict[str, Any]], int]:
        """
        Lista events desde DB con filtros y paginación.
        next_days: eventos con end_time dentro de los próximos N días.
        max_time_to_resolution_minutes: eventos con (end_time - now) <= N minutos.
        """
        base = db.query(Event).join(Market, Event.market_id == Market.id)

        if market_id is not None:
            mid = UUID(str(market_id)) if isinstance(market_id, str) else market_id
            base = base.filter(Event.market_id == mid)
        if state is not None:
            base = base.filter(Event.state == state)
        if category is not None:
            base = base.filter(Market.category == category)
        if tag_id is not None:
            tid = UUID(str(tag_id)) if isinstance(tag_id, str) else tag_id
            base = base.join(MarketTag).filter(MarketTag.market_id == Market.id, MarketTag.tag_id == tid)
        if next_days is not None:
            from datetime import timedelta
            threshold = datetime.utcnow() + timedelta(days=next_days)
            base = base.filter(Event.end_time <= threshold)
        if max_time_to_resolution_minutes is not None:
            from datetime import timedelta
            threshold = datetime.utcnow() + timedelta(minutes=max_time_to_resolution_minutes)
            base = base.filter(Event.end_time <= threshold)

        total = base.count()
        events = base.order_by(Event.start_time.desc()).offset(offset).limit(limit).all()

        result = []
        for e in events:
            result.append({
                "event_id": str(e.id),
                "polymarket_event_id": e.polymarket_event_id,
                "market_id": str(e.market_id),
                "market_name": e.market.name if e.market else None,
                "start_time": e.start_time.isoformat() if e.start_time else None,
                "end_time": e.end_time.isoformat() if e.end_time else None,
                "state": e.state,
                "created_at": e.created_at.isoformat() if e.created_at else None,
                "updated_at": e.updated_at.isoformat() if e.updated_at else None,
            })
        return result, total

    @staticmethod
    def get_events_eligible_for_universe(
        db: Session,
        universe_config: Dict[str, Any],
        limit: int = 100,
    ) -> List[Event]:
        """
        Eventos elegibles para auto-attach según universe_config (Phase 4).

        Precedencia: enabled global → deny_list → selectores (categories/tags, markets[], events[]) + time_filter.
        Solo devuelve eventos cuyo market está enabled global.
        No llama a Gamma; solo lee de DB.
        """
        categories = list(universe_config.get("categories") or [])
        tags = list(universe_config.get("tags") or [])
        markets = list(universe_config.get("markets") or [])
        events_explicit = list(universe_config.get("events") or [])
        deny_list = list(universe_config.get("deny_list") or [])
        time_filter = universe_config.get("time_filter") or {}

        # Enabled global: solo markets con MarketEnabledState.enabled=True o Market.enabled=True
        base = (
            db.query(Event)
            .join(Market, Event.market_id == Market.id)
            .outerjoin(
                MarketEnabledState,
                Market.polymarket_id == MarketEnabledState.polymarket_market_id,
            )
        )
        base = base.filter(
            or_(
                and_(
                    MarketEnabledState.polymarket_market_id.isnot(None),
                    MarketEnabledState.enabled == True,
                ),
                and_(
                    MarketEnabledState.polymarket_market_id.is_(None),
                    Market.enabled == True,
                ),
            )
        )

        # deny_list: excluir por event_id (nuestro UUID) o polymarket_event_id o market polymarket_id
        if deny_list:
            try:
                deny_uuids = [UUID(x) for x in deny_list if _is_uuid(x)]
            except (ValueError, TypeError):
                deny_uuids = []
            deny_conds = []
            if deny_uuids:
                deny_conds.append(~Event.id.in_(deny_uuids))
            deny_conds.append(~Event.polymarket_event_id.in_(deny_list))
            deny_conds.append(~Market.polymarket_id.in_(deny_list))
            base = base.filter(and_(*deny_conds))

        # time_filter: state
        window = time_filter.get("window")
        next_days = time_filter.get("next_days")
        max_ttr_min = time_filter.get("max_time_to_resolution_minutes")
        now = datetime.utcnow()
        if window and str(window).upper() != "ANY":
            state_filter = str(window).upper()
            if state_filter in ("UPCOMING", "ACTIVE"):
                base = base.filter(Event.state == state_filter)
        if next_days is not None:
            threshold = now + timedelta(days=next_days)
            base = base.filter(Event.end_time <= threshold)
        if max_ttr_min is not None:
            ttr_threshold = now + timedelta(minutes=max_ttr_min)
            base = base.filter(Event.end_time <= ttr_threshold)

        # Selectores: (categories AND tags) OR markets[] OR events[]
        from sqlalchemy import literal

        cond_cat_tag = and_()
        if categories:
            cond_cat_tag = and_(cond_cat_tag, Market.category.in_(categories))
        if tags:
            try:
                tag_uuids = [UUID(t) for t in tags if _is_uuid(t)]
            except (ValueError, TypeError):
                tag_uuids = []
            if tag_uuids:
                sub = (
                    db.query(MarketTag.market_id)
                    .filter(MarketTag.tag_id.in_(tag_uuids))
                    .distinct()
                    .subquery()
                )
                cond_cat_tag = and_(cond_cat_tag, Market.id.in_(sub))

        cond_markets = literal(False)
        if markets:
            cond_markets = Market.polymarket_id.in_(markets)
            try:
                market_uuids = [UUID(m) for m in markets if _is_uuid(m)]
                if market_uuids:
                    cond_markets = or_(cond_markets, Market.id.in_(market_uuids))
            except (ValueError, TypeError):
                pass
        cond_events = literal(False)
        if events_explicit:
            try:
                event_uuids = [UUID(e) for e in events_explicit if _is_uuid(e)]
                if event_uuids:
                    cond_events = Event.id.in_(event_uuids)
            except (ValueError, TypeError):
                pass

        if categories or tags:
            base = base.filter(or_(cond_cat_tag, cond_markets, cond_events))
        elif markets or events_explicit:
            base = base.filter(or_(cond_markets, cond_events))
        else:
            return []

        return base.order_by(Event.start_time.desc()).limit(limit).all()


def _is_uuid(s: Any) -> bool:
    if not isinstance(s, str):
        return False
    try:
        UUID(s)
        return True
    except (ValueError, TypeError):
        return False
