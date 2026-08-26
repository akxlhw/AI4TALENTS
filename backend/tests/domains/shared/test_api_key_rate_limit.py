"""Rate limiter keys open-api requests by api key, not IP."""

from __future__ import annotations

from app.middleware.rate_limit import RateLimiter


def test_limiter_accepts_apikey_prefixed_keys() -> None:
    limiter = RateLimiter(requests_per_minute=2)
    key = "apikey:abcd1234"
    assert limiter.is_allowed(key)[0] is True
    assert limiter.is_allowed(key)[0] is True
    assert limiter.is_allowed(key)[0] is False
