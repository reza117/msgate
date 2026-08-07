"""requests HTTPAdapter bound to a prepared SSLContext."""

from __future__ import annotations

import ssl
from typing import Any

from requests.adapters import HTTPAdapter


def make_http_adapter_class(ssl_context: ssl.SSLContext) -> type[HTTPAdapter]:
    """Return an adapter *class* for exchangelib ``BaseProtocol.HTTP_ADAPTER_CLS``."""

    class MsgateSSLAdapter(HTTPAdapter):
        def init_poolmanager(
            self,
            connections: int,
            maxsize: int,
            block: bool = False,
            **kwargs: Any,
        ):
            kwargs["ssl_context"] = ssl_context
            return super().init_poolmanager(connections, maxsize, block=block, **kwargs)

        def proxy_manager_for(self, proxy: str, **kwargs: Any):
            kwargs["ssl_context"] = ssl_context
            return super().proxy_manager_for(proxy, **kwargs)

        def cert_verify(self, conn: Any, url: str, verify: Any, cert: Any) -> None:
            if ssl_context.verify_mode == ssl.CERT_NONE:
                conn.assert_hostname = False
                conn.cert_reqs = "CERT_NONE"
                return
            super().cert_verify(conn, url, verify, cert)

    MsgateSSLAdapter.__name__ = "MsgateSSLAdapter"
    MsgateSSLAdapter.__qualname__ = "MsgateSSLAdapter"
    return MsgateSSLAdapter
