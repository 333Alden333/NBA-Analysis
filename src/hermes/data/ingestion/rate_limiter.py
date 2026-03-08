"""Rate limiting and retry logic for API calls."""

import time
import random
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter with exponential backoff for 429 errors."""

    def __init__(self, min_delay: float = 1.0, max_delay: float = 2.0):
        self.min_delay = min_delay
        self.max_delay = max_delay
        self._last_request_time = 0.0

    def wait(self):
        """Wait appropriate time before next request."""
        elapsed = time.monotonic() - self._last_request_time
        delay = random.uniform(self.min_delay, self.max_delay)
        if elapsed < delay:
            time.sleep(delay - elapsed)
        self._last_request_time = time.monotonic()

    def call_with_retry(self, func, *args, max_retries: int = 3, **kwargs):
        """Call function with rate limiting and exponential backoff on 429.

        Retries on 429/Too Many Requests errors with exponential backoff.
        Re-raises non-429 exceptions immediately.
        Raises RuntimeError after max_retries exceeded.
        """
        for attempt in range(max_retries):
            self.wait()
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if "429" in str(e) or "Too Many Requests" in str(e):
                    if attempt < max_retries - 1:
                        backoff = (2 ** attempt) * 0.01 + random.uniform(0, 0.01)
                        logger.warning(
                            f"Rate limited (attempt {attempt + 1}/{max_retries}), "
                            f"backing off {backoff:.3f}s"
                        )
                        time.sleep(backoff)
                    else:
                        raise RuntimeError(
                            f"Max retries ({max_retries}) exceeded for {func.__name__}"
                        ) from e
                else:
                    raise
        raise RuntimeError(f"Max retries ({max_retries}) exceeded")
