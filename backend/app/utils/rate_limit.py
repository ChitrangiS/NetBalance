import time
from collections import defaultdict
from threading import Lock
from fastapi import HTTPException, Request, status


class InMemoryRateLimiter:
    """
    A simple sliding-window rate limiter using in-memory storage.

    PRODUCTION NOTE: This implementation works correctly for a
    SINGLE-PROCESS deployment (one uvicorn worker). With multiple
    workers or multiple backend instances, each instance has its
    own independent counter — the effective rate limit becomes
    N * limit (where N = number of instances). For true multi-instance
    rate limiting, use Redis with atomic INCR + EXPIRE (or a library
    like slowapi with a Redis backend). We use this simpler approach
    here because the learning value is in understanding the concept,
    and a single-worker deployment is appropriate for a portfolio project.

    Algorithm: sliding window counter
      - Track timestamps of all requests within the window
      - On each new request, discard timestamps older than window_seconds
      - If remaining count >= limit, reject the request
    """

    def __init__(self):
        # {key: [timestamp1, timestamp2, ...]}
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()  # Thread safety for concurrent requests

    def is_allowed(self, key: str, limit: int, window_seconds: int) -> bool:
        now = time.monotonic()
        cutoff = now - window_seconds

        with self._lock:
            # Discard timestamps outside the current window
            self._requests[key] = [
                ts for ts in self._requests[key] if ts > cutoff
            ]
            if len(self._requests[key]) >= limit:
                return False
            self._requests[key].append(now)
            return True


_rate_limiter = InMemoryRateLimiter()


def rate_limit(limit: int = 10, window_seconds: int = 60, key_func=None):
    """
    FastAPI dependency factory for rate limiting.

    Usage:
        @router.post("/login")
        def login(
            credentials: UserLogin,
            request: Request,
            _: None = Depends(rate_limit(limit=5, window_seconds=60)),
        ):
            ...

    The key_func determines how to "bucket" requests. Default: by IP.
    For login: key by (IP, email) to prevent targeted attacks on a
    specific account while still allowing normal usage from that IP.
    """
    def dependency(request: Request):
        if key_func:
            key = key_func(request)
        else:
            # X-Forwarded-For: the client's real IP when behind a proxy/load balancer
            # Fall back to direct client IP if not proxied
            forwarded_for = request.headers.get("X-Forwarded-For")
            key = forwarded_for.split(",")[0].strip() if forwarded_for else request.client.host

        if not _rate_limiter.is_allowed(key, limit, window_seconds):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many requests. Try again in {window_seconds} seconds.",
                headers={"Retry-After": str(window_seconds)},
            )

    return dependency