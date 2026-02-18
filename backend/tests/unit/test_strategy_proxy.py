"""
Tests unitarios para proxy_id y connection_proxies en Strategy.
"""
import pytest
from uuid import uuid4

from app.models.strategy import Strategy
from app.models.proxy import Proxy
from app.core.proxy_service import VALID_CONNECTION_KEYS


class TestStrategyProxyFields:
    """Tests para campos proxy en Strategy."""

    def test_strategy_with_proxy_id(self, db_session):
        """Strategy puede tener proxy_id."""
        proxy = Proxy(
            name="Test Proxy",
            proxy_type="SOCKS5",
            proxy_host="127.0.0.1",
            proxy_port=1080,
            created_by="user-1",
        )
        db_session.add(proxy)
        db_session.commit()
        db_session.refresh(proxy)

        strategy = Strategy(
            name="Test Strategy",
            decision_graph={"entry_node": "n", "nodes": {"n": {"type": "noop"}}},
            support_graphs=[],
            proxy_id=proxy.id,
            connection_proxies={},
        )
        db_session.add(strategy)
        db_session.commit()
        db_session.refresh(strategy)

        assert strategy.proxy_id == proxy.id
        assert strategy.connection_proxies == {}

    def test_strategy_with_connection_proxies(self, db_session):
        """Strategy puede tener connection_proxies."""
        p1 = Proxy(
            name="Proxy 1",
            proxy_type="SOCKS5",
            proxy_host="1.2.3.4",
            proxy_port=1080,
            created_by="user-1",
        )
        p2 = Proxy(
            name="Proxy 2",
            proxy_type="HTTP",
            proxy_host="5.6.7.8",
            proxy_port=8080,
            created_by="user-1",
        )
        db_session.add_all([p1, p2])
        db_session.commit()
        db_session.refresh(p1)
        db_session.refresh(p2)

        strategy = Strategy(
            name="Multi-connection Strategy",
            decision_graph={"entry_node": "n", "nodes": {"n": {"type": "noop"}}},
            support_graphs=[],
            proxy_id=None,
            connection_proxies={
                "telegram": str(p1.id),
                "ps3838": str(p2.id),
            },
        )
        db_session.add(strategy)
        db_session.commit()
        db_session.refresh(strategy)

        assert strategy.proxy_id is None
        assert strategy.connection_proxies["telegram"] == str(p1.id)
        assert strategy.connection_proxies["ps3838"] == str(p2.id)

    def test_connection_proxies_default_empty(self, db_session):
        """connection_proxies se normaliza a {} cuando es None."""
        strategy = Strategy(
            name="Strategy sin proxy",
            decision_graph={"entry_node": "n", "nodes": {"n": {"type": "noop"}}},
            support_graphs=[],
            proxy_id=None,
        )
        db_session.add(strategy)
        db_session.commit()
        db_session.refresh(strategy)

        assert strategy.connection_proxies is not None
        assert strategy.connection_proxies == {} or strategy.connection_proxies == dict()
