"""Authentication dependencies and RBAC guards."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import get_session
from src.models.user import User


@dataclass(slots=True)
class RequestUserContext:
    """Request-scoped authenticated user identity."""

    user_id: int
    email: str
    role: str


async def get_optional_request_user(request: Request) -> RequestUserContext | None:
    """Return authenticated user context if available."""
    context = getattr(request.state, "user_context", None)
    if isinstance(context, RequestUserContext):
        return context
    return None


async def get_current_user(
    request_user: RequestUserContext | None = Depends(get_optional_request_user),
    session: AsyncSession = Depends(get_session),
) -> User:
    """Return current authenticated user or raise 401."""
    if request_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    result = await session.execute(select(User).where(User.id == request_user.user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication context",
        )

    return user


def require_roles(*allowed_roles: str) -> Callable[[User], Awaitable[User]]:
    """Build an RBAC guard dependency for route protection."""
    role_set = set(allowed_roles)

    async def _dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in role_set:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient role permissions",
            )
        return current_user

    return _dependency


def resolve_user_id(request_user: RequestUserContext | None, fallback: str = "default") -> str:
    """Map optional authenticated user context to a user key."""
    if request_user is None:
        return fallback
    return str(request_user.user_id)
