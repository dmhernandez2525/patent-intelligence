"""Authentication and user preference service."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User, UserPreference, UserRole
from src.utils.security import create_access_token, hash_password, verify_password


class AuthService:
    """Registration, login, and user preference operations."""

    async def register_user(
        self,
        session: AsyncSession,
        email: str,
        password: str,
        role: str = UserRole.VIEWER.value,
    ) -> User:
        normalized_email = email.strip().lower()
        existing = await session.execute(select(User).where(User.email == normalized_email))
        if existing.scalar_one_or_none() is not None:
            raise ValueError("Email is already registered")

        user = User(
            email=normalized_email,
            hashed_password=hash_password(password),
            role=role,
        )
        session.add(user)
        await session.flush()

        preferences = UserPreference(user_id=user.id)
        session.add(preferences)
        await session.flush()
        await session.refresh(user)
        return user

    async def authenticate_user(
        self,
        session: AsyncSession,
        email: str,
        password: str,
    ) -> User | None:
        normalized_email = email.strip().lower()
        result = await session.execute(select(User).where(User.email == normalized_email))
        user = result.scalar_one_or_none()
        if user is None or not user.is_active:
            return None
        if not verify_password(password, user.hashed_password):
            return None

        user.last_login = datetime.now(UTC)
        await session.flush()
        return user

    def create_access_token_for_user(self, user: User) -> str:
        return create_access_token(
            user_id=user.id,
            email=user.email,
            role=user.role,
        )

    async def get_user_by_id(self, session: AsyncSession, user_id: int) -> User | None:
        result = await session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_user_preferences(self, session: AsyncSession, user_id: int) -> UserPreference:
        result = await session.execute(
            select(UserPreference).where(UserPreference.user_id == user_id)
        )
        preferences = result.scalar_one_or_none()
        if preferences is not None:
            return preferences

        preferences = UserPreference(user_id=user_id)
        session.add(preferences)
        await session.flush()
        return preferences

    async def update_user_preferences(
        self,
        session: AsyncSession,
        user_id: int,
        *,
        default_search_mode: str | None = None,
        alert_frequency: str | None = None,
        timezone: str | None = None,
        email_notifications_enabled: bool | None = None,
    ) -> UserPreference:
        preferences = await self.get_user_preferences(session, user_id)

        if default_search_mode is not None:
            preferences.default_search_mode = default_search_mode
        if alert_frequency is not None:
            preferences.alert_frequency = alert_frequency
        if timezone is not None:
            preferences.timezone = timezone
        if email_notifications_enabled is not None:
            preferences.email_notifications_enabled = email_notifications_enabled

        await session.flush()
        return preferences


auth_service = AuthService()
