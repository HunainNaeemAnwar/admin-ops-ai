"""Simple TTL cache for frequently accessed DB data.

Reduces repeated DB reads for workers, products, and rate info.
"""

import time
from functools import wraps
from typing import Any, Callable

_TTL = 120  # 2 minute default


class TTLCache:
    def __init__(self, ttl: float = _TTL):
        self._ttl = ttl
        self._store: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any | None:
        data = self._store.get(key)
        if data is None:
            return None
        ts, val = data
        if time.time() - ts > self._ttl:
            del self._store[key]
            return None
        return val

    def set(self, key: str, value: Any):
        self._store[key] = (time.time(), value)

    def invalidate(self, key: str | None = None):
        if key:
            self._store.pop(key, None)
        else:
            self._store.clear()


_worker_cache = TTLCache()
_product_cache = TTLCache()


def cached_workers(fn: Callable):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        cached = _worker_cache.get("workers")
        if cached is not None:
            return cached
        result = fn(*args, **kwargs)
        _worker_cache.set("workers", result)
        return result
    return wrapper


def cached_products(fn: Callable):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        cached = _product_cache.get("products")
        if cached is not None:
            return cached
        result = fn(*args, **kwargs)
        _product_cache.set("products", result)
        return result
    return wrapper


def invalidate_worker_cache():
    _worker_cache.invalidate()


def invalidate_product_cache():
    _product_cache.invalidate()


def invalidate_all():
    _worker_cache.invalidate()
    _product_cache.invalidate()
