"""Middleware for optional auth context and per-user rate limiting."""

from collections.abc import Awaitable, Callable

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from src.api.dependencies.auth import RequestUserContext
from src.utils.logger import logger
from src.utils.security import decode_access_token
from src.utils.user_rate_limiter import user_rate_limiter


def _extract_bearer_token(authorization_header: str | None) -> str | None:
    if not authorization_header:
        return None
    parts = authorization_header.split(" ", maxsplit=1)
    if len(parts) != 2:
        return None
    scheme, token = parts
    if scheme.lower() != "bearer" or not token:
        return None
    return token


class AuthContextMiddleware(BaseHTTPMiddleware):
    """Attach optional user context and enforce per-user token bucket limits."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request.state.user_context = None

        token = _extract_bearer_token(request.headers.get("Authorization"))
        if token:
            payload = decode_access_token(token)
            if payload and payload["sub"].isdigit():
                request.state.user_context = RequestUserContext(
                    user_id=int(payload["sub"]),
                    email=payload["email"],
                    role=payload["role"],
                )

        user_context = request.state.user_context
        if isinstance(user_context, RequestUserContext):
            rate_key = f"user:{user_context.user_id}"
        else:
            client_host = request.client.host if request.client else "unknown"
            rate_key = f"ip:{client_host}"

        allowed = await user_rate_limiter.allow_request(rate_key)
        if not allowed:
            logger.warning("rate_limit.rejected", rate_key=rate_key, path=request.url.path)
            return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})

        return await call_next(request)
