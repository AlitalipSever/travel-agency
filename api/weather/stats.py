"""Ad hoc cache counters for the operations status (N5.5): hits (served from the Redis cache,
fresh or stale) and misses (an upstream call was made). Kept for seven days, reset by TTL."""

from __future__ import annotations

from typing import Literal

from core import redis_client

KEYS = {"hit": "ops:adhoc:hit", "miss": "ops:adhoc:miss"}
TTL_S = 7 * 24 * 3600


def record_adhoc(kind: Literal["hit", "miss"]) -> None:
    r = redis_client.redis_connection()
    key = KEYS[kind]
    r.incr(key)
    r.expire(key, TTL_S)


def adhoc_snapshot() -> dict[str, object]:
    r = redis_client.redis_connection()
    hits = int(r.get(KEYS["hit"]) or 0)
    misses = int(r.get(KEYS["miss"]) or 0)
    total = hits + misses
    return {"hits": hits, "misses": misses, "hit_ratio": round(hits / total, 3) if total else None}
