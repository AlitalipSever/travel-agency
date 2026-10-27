"""Weather tests run against an in-memory Redis (fakeredis) and the fixture mock client."""

import fakeredis
import pytest

from core import redis_client


@pytest.fixture(autouse=True)
def fake_redis(monkeypatch: pytest.MonkeyPatch) -> fakeredis.FakeRedis:
    server = fakeredis.FakeServer()
    conn = fakeredis.FakeRedis(server=server, decode_responses=True)
    redis_client.redis_connection.cache_clear()
    monkeypatch.setattr(redis_client, "redis_connection", lambda: conn)
    # modules imported `redis_connection` by name; patch those references too
    from weather import adhoc, forecast
    from weather.upstream import breaker, budget

    monkeypatch.setattr(budget, "redis_connection", lambda: conn)
    monkeypatch.setattr(breaker, "redis_connection", lambda: conn)
    monkeypatch.setattr(adhoc, "redis_connection", lambda: conn)
    monkeypatch.setattr(forecast, "redis_connection", lambda: conn)
    return conn
