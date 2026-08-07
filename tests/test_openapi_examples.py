"""OpenAPI docs must use fictional example content only."""

from __future__ import annotations

import json

from conftest import make_test_client

# Site-specific strings must never appear in published schema examples.
_FORBIDDEN = (
    "WDC",
    "wigner",
    "hun-ren",
    "internal.wdc",
    "datacenter.wigner",
)


def test_openapi_examples_are_generic() -> None:
    client = make_test_client(authenticated=True)
    r = client.get("/openapi.json")
    assert r.status_code == 200
    blob = json.dumps(r.json())
    for needle in _FORBIDDEN:
        assert needle not in blob, f"OpenAPI still contains site-specific example: {needle}"
    assert "DOMAIN\\\\svc.msgate" in blob or "DOMAIN\\svc.msgate" in blob
    assert "example.com" in blob
