"""redis-py must accept the CERT_NONE form already used by the Celery broker URL."""

from __future__ import annotations

import pytest
from redis.connection import SSLConnection, parse_url
from redis.exceptions import RedisError

from app.core.redis_url import normalize_redis_url, redis_from_url

_RENDER_URL = "rediss://:s3cret@red-abc.oregon.render.com:6379/0?ssl_cert_reqs=CERT_NONE"


def test_cert_none_is_normalised_without_touching_credentials() -> None:
    normalised = normalize_redis_url(_RENDER_URL)
    assert "ssl_cert_reqs=none" in normalised
    assert "ssl_cert_reqs=CERT_NONE" not in normalised
    assert "s3cret" in normalised
    assert normalised.startswith("rediss://")


def test_already_valid_and_plain_urls_are_unchanged() -> None:
    plain = "redis://localhost:6379/0"
    assert normalize_redis_url(plain) == plain
    ready = "rediss://localhost:6379/0?ssl_cert_reqs=none"
    assert normalize_redis_url(ready) == ready
    optional = "rediss://localhost:6379/0?ssl_cert_reqs=CERT_OPTIONAL"
    assert normalize_redis_url(optional).endswith("ssl_cert_reqs=optional")


def test_redis_py_accepts_normalised_cert_none() -> None:
    raw_opts = parse_url(_RENDER_URL)
    raw_opts.pop("connection_class", None)
    with pytest.raises(RedisError, match="CERT_NONE"):
        SSLConnection(**raw_opts)

    client = redis_from_url(_RENDER_URL, decode_responses=True, socket_connect_timeout=0.05)
    assert client.connection_pool.connection_kwargs["ssl_cert_reqs"] == "none"

    normalised_opts = parse_url(normalize_redis_url(_RENDER_URL))
    normalised_opts.pop("connection_class", None)
    connection = SSLConnection(**normalised_opts)
    assert connection.cert_reqs == 0  # ssl.CERT_NONE
