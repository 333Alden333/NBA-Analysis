"""Tests for RateLimiter."""

import time
import pytest

from hermes.data.ingestion.rate_limiter import RateLimiter


class TestRateLimiterWait:
    """RateLimiter.wait() enforces minimum delay between calls."""

    def test_wait_enforces_delay(self):
        limiter = RateLimiter(min_delay=0.05, max_delay=0.1)
        limiter.wait()  # first call sets timestamp
        start = time.monotonic()
        limiter.wait()  # second call should wait
        elapsed = time.monotonic() - start
        assert elapsed >= 0.04  # allow small tolerance

    def test_no_wait_if_enough_time_passed(self):
        limiter = RateLimiter(min_delay=0.01, max_delay=0.02)
        limiter.wait()
        time.sleep(0.05)  # wait longer than max_delay
        start = time.monotonic()
        limiter.wait()
        elapsed = time.monotonic() - start
        assert elapsed < 0.03  # should not add significant delay


class TestRateLimiterRetry:
    """RateLimiter.call_with_retry() handles 429 errors."""

    def test_successful_call(self):
        limiter = RateLimiter(min_delay=0.01, max_delay=0.02)
        result = limiter.call_with_retry(lambda: 42, max_retries=3)
        assert result == 42

    def test_retries_on_429(self):
        limiter = RateLimiter(min_delay=0.01, max_delay=0.02)
        call_count = 0

        def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("429 Too Many Requests")
            return "success"

        # Use very short backoff for testing
        result = limiter.call_with_retry(flaky_func, max_retries=3)
        assert result == "success"
        assert call_count == 3

    def test_raises_after_max_retries(self):
        limiter = RateLimiter(min_delay=0.01, max_delay=0.02)

        def always_429():
            raise Exception("429 Too Many Requests")

        with pytest.raises(RuntimeError, match="Max retries"):
            limiter.call_with_retry(always_429, max_retries=2)

    def test_does_not_retry_non_429(self):
        limiter = RateLimiter(min_delay=0.01, max_delay=0.02)
        call_count = 0

        def bad_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("Something else broke")

        with pytest.raises(ValueError, match="Something else broke"):
            limiter.call_with_retry(bad_func, max_retries=3)
        assert call_count == 1  # should NOT retry
