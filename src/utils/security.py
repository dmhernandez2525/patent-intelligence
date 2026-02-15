"""Password hashing and JWT helpers."""

from datetime import UTC, datetime, timedelta
from typing import cast

from jose import JWTError, jwt
from passlib.context import CryptContext

from src.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a user password with bcrypt."""
    return cast(str, pwd_context.hash(password))


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against a bcrypt hash."""
    return cast(bool, pwd_context.verify(password, hashed_password))


def create_access_token(
    user_id: int,
    email: str,
    role: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT access token."""
    now = datetime.now(UTC)
    expires_at = now + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    return cast(str, jwt.encode(payload, settings.validated_secret_key, algorithm=settings.algorithm))


def decode_access_token(token: str) -> dict[str, str] | None:
    """Decode an access token and return payload claims."""
    try:
        payload = jwt.decode(
            token,
            settings.validated_secret_key,
            algorithms=[settings.algorithm],
        )
    except JWTError:
        return None

    subject = payload.get("sub")
    if not isinstance(subject, str):
        return None

    email = payload.get("email")
    role = payload.get("role")

    return {
        "sub": subject,
        "email": email if isinstance(email, str) else "",
        "role": role if isinstance(role, str) else "",
    }
