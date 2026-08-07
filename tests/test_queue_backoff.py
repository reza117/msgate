"""Queue backoff and retriable error tests."""

from msgate.queue.backoff import backoff_seconds, is_retriable_error


def test_retriable_503() -> None:
    assert is_retriable_error(Exception("HTTP 503 Service Unavailable"))


def test_not_retriable_auth() -> None:
    assert not is_retriable_error(Exception("401 Unauthorized"))


def test_backoff_exponential() -> None:
    assert backoff_seconds(1) == 5.0
    assert backoff_seconds(2) == 10.0
    assert backoff_seconds(10) == 300.0
