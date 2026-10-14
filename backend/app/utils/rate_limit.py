import threading
import time
from collections import defaultdict, deque
from typing import Optional
from fastapi import HTTPException, Request, status
from app.utils.security import decode_token


class InMemoryRateLimiter:
    """
    In-memory sliding window rate limiter using Python standard library.
    
    IMPORTANT ARCHITECTURAL & HORIZONTAL SCALING LIMITATION:
    This limiter operates strictly within the memory space of a single Python process.
    In multi-worker deployments (e.g. Uvicorn with multiple workers) or horizontally
    scaled multi-container deployments (Kubernetes, ECS, multiple Cloud Run instances),
    each process maintains its own isolated in-memory state. Consequently, rate limits
    would be multiplied by the number of active workers/instances.
    Before horizontal scaling or multi-process production deployment, this rate limiter
    MUST be replaced by a shared centralized store (e.g. Redis-backed token bucket)
    or managed at an upstream API gateway / reverse proxy (e.g. Cloudflare, Envoy, Nginx).
    """

    def __init__(self):
        self._lock = threading.Lock()
        # Map of scope:key -> deque of timestamps
        self._history = defaultdict(deque)

    def is_allowed(self, key: str, max_requests: int, window_seconds: int) -> bool:
        now = time.time()
        cutoff = now - window_seconds
        with self._lock:
            timestamps = self._history[key]
            # Evict timestamps outside the window
            while timestamps and timestamps[0] <= cutoff:
                timestamps.popleft()

            if len(timestamps) >= max_requests:
                return False

            timestamps.append(now)
            return True

    def reset(self):
        with self._lock:
            self._history.clear()


limiter = InMemoryRateLimiter()


def get_client_identifier(request: Request, trust_forwarded_headers: bool = False) -> str:
    """
    Extract a resilient client identifier for rate limiting.
    
    1. If a valid Bearer token is provided, extract the authenticated user ID.
       This prevents cross-user collisions for clients behind corporate NATs,
       and prevents authenticated attackers from evading limits by rotating IP headers.
    2. For unauthenticated clients, use the direct socket connection host (request.client.host).
       Client-supplied 'X-Forwarded-For' headers are deliberately NOT trusted by default,
       preventing trivial rate-limit evasion via forged proxy headers.
    """
    # 1. Check for Bearer token
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
        payload = decode_token(token)
        if payload:
            user_id = payload.get("sub") or payload.get("id") or payload.get("user_id")
            if isinstance(user_id, str) and user_id:
                return f"user:{user_id}"

    # 2. Unauthenticated: check proxy headers only if explicitly enabled
    if trust_forwarded_headers:
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            first_ip = forwarded_for.split(",")[0].strip()
            if first_ip:
                return f"ip:{first_ip}"

    # Default to direct connection IP
    client_ip = request.client.host if request.client else "unknown"
    return f"ip:{client_ip}"


def rate_limit_dependency(
    max_requests: int,
    window_seconds: int,
    scope: str = "default",
    trust_forwarded_headers: bool = False
):
    """
    FastAPI dependency that enforces rate limiting per authenticated user or connection IP.
    """
    async def dependency(request: Request):
        client_id = get_client_identifier(request, trust_forwarded_headers=trust_forwarded_headers)
        key = f"{scope}:{client_id}"
        if not limiter.is_allowed(key, max_requests=max_requests, window_seconds=window_seconds):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded for {scope}. Please try again later."
            )

    return dependency

