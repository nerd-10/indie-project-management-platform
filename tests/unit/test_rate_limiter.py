from uuid import UUID

import pytest

from app.core import rate_limiter
from app.core.rate_limiter import SlidingWindowRateLimiter


@pytest.fixture
def clock(monkeypatch):
    current_time = [1000.0]

    def fake_monotonic():
        return current_time[0]

    monkeypatch.setattr(
        rate_limiter.time,
        "monotonic",
        fake_monotonic,
    )

    def advance(seconds: float) -> None:
        current_time[0] += seconds

    return advance


def test_try_acquire_allows_attempts_below_limit(clock):
    limiter = SlidingWindowRateLimiter(
        max_attempts=5,
        window_seconds=900,
    )

    for _ in range(4):
        assert limiter.try_acquire("user@example.com") is not None

    assert limiter.try_acquire("user@example.com") is not None


def test_try_acquire_blocks_when_limit_is_reached(clock):
    limiter = SlidingWindowRateLimiter(
        max_attempts=3,
        window_seconds=900,
    )

    for _ in range(3):
        assert limiter.try_acquire("user@example.com") is not None

    assert limiter.try_acquire("user@example.com") is None


def test_expired_attempts_are_removed(clock):
    limiter = SlidingWindowRateLimiter(
        max_attempts=2,
        window_seconds=60,
    )

    assert limiter.try_acquire("user@example.com") is not None

    clock(30)

    assert limiter.try_acquire("user@example.com") is not None
    assert limiter.try_acquire("user@example.com") is None

    clock(31)

    assert limiter.try_acquire("user@example.com") is not None


def test_clear_resets_attempt_history(clock):
    limiter = SlidingWindowRateLimiter(
        max_attempts=2,
        window_seconds=900,
    )

    limiter.try_acquire("user@example.com")
    limiter.try_acquire("user@example.com")

    assert limiter.try_acquire("user@example.com") is None

    limiter.clear("user@example.com")

    assert limiter.try_acquire("user@example.com") is not None


def test_different_keys_have_independent_limits(clock):
    limiter = SlidingWindowRateLimiter(
        max_attempts=2,
        window_seconds=900,
    )

    limiter.try_acquire("user1@example.com")
    limiter.try_acquire("user1@example.com")

    assert limiter.try_acquire("user1@example.com") is None
    assert limiter.try_acquire("user2@example.com") is not None


def test_get_retry_after_returns_remaining_window(clock):
    limiter = SlidingWindowRateLimiter(
        max_attempts=2,
        window_seconds=60,
    )

    limiter.try_acquire("user@example.com")
    clock(15)
    limiter.try_acquire("user@example.com")

    assert limiter.get_retry_after("user@example.com") == 45

    clock(10)

    assert limiter.get_retry_after("user@example.com") == 35


def test_retry_after_is_zero_when_not_limited(clock):
    limiter = SlidingWindowRateLimiter(
        max_attempts=3,
        window_seconds=60,
    )

    limiter.try_acquire("user@example.com")

    assert limiter.get_retry_after("user@example.com") == 0


def test_cleanup_removes_expired_keys(clock):
    limiter = SlidingWindowRateLimiter(
        max_attempts=2,
        window_seconds=60,
    )

    limiter.try_acquire("user@example.com")
    clock(61)

    limiter.cleanup()

    assert "user@example.com" not in limiter._attempts


@pytest.mark.parametrize(
    ("max_attempts", "window_seconds"),
    [
        (0, 60),
        (-1, 60),
        (5, 0),
        (5, -1),
    ],
)
def test_rejects_invalid_configuration(max_attempts, window_seconds):
    with pytest.raises(ValueError):
        SlidingWindowRateLimiter(
            max_attempts=max_attempts,
            window_seconds=window_seconds,
        )


def test_release_removes_only_the_matching_reservation(clock):
    limiter = SlidingWindowRateLimiter(max_attempts=2, window_seconds=60)

    first = limiter.try_acquire("user@example.com")
    second = limiter.try_acquire("user@example.com")

    assert first is not None
    assert second is not None
    assert limiter.try_acquire("user@example.com") is None

    limiter.release("user@example.com", first)

    third = limiter.try_acquire("user@example.com")
    assert third is not None
    assert limiter.try_acquire("user@example.com") is None


def test_release_does_not_affect_another_key(clock):
    limiter = SlidingWindowRateLimiter(max_attempts=1, window_seconds=60)

    first = limiter.try_acquire("user1@example.com")
    second = limiter.try_acquire("user2@example.com")

    assert first is not None
    assert second is not None

    limiter.release("user1@example.com", first)

    assert limiter.try_acquire("user1@example.com") is not None
    assert limiter.try_acquire("user2@example.com") is None


def test_release_with_unknown_reservation_does_nothing(clock):
    limiter = SlidingWindowRateLimiter(max_attempts=1, window_seconds=60)

    reservation = limiter.try_acquire("user@example.com")
    assert reservation is not None

    limiter.release("user@example.com", UUID(int=0))

    assert limiter.try_acquire("user@example.com") is None


def test_release_does_not_remove_newer_reservation(clock):
    limiter = SlidingWindowRateLimiter(
        max_attempts=1,
        window_seconds=60,
    )

    old = limiter.try_acquire("user@example.com")
    assert old is not None

    clock(61)

    new = limiter.try_acquire("user@example.com")
    assert new is not None

    limiter.release("user@example.com", old)

    assert limiter.try_acquire("user@example.com") is None
