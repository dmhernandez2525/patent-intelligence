"""Authentication, RBAC, organization, and SSO endpoints."""

import secrets

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies.auth import get_current_user, require_roles
from src.api.schemas.auth import (
    InviteAcceptResponse,
    LoginRequest,
    OrganizationCreateRequest,
    OrganizationInviteRequest,
    OrganizationInviteResponse,
    OrganizationResponse,
    PreferencesResponse,
    PreferencesUpdateRequest,
    RegisterRequest,
    SSOCallbackResponse,
    SSOStartResponse,
    TokenResponse,
    UserResponse,
)
from src.config import settings
from src.database.connection import get_session
from src.models.user import User
from src.services.activity_service import activity_service
from src.services.auth_service import auth_service
from src.services.organization_service import organization_service
from src.services.sso_service import SSOProvider, sso_service
from src.utils.logger import logger

router = APIRouter()

def _to_user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        last_login=user.last_login.isoformat() if user.last_login else None,
        created_at=user.created_at.isoformat() if user.created_at else None,
    )


def _resolve_sso_provider(provider: str) -> SSOProvider:
    lowered = provider.lower()
    if lowered == SSOProvider.GOOGLE.value:
        return SSOProvider.GOOGLE
    if lowered == SSOProvider.MICROSOFT.value:
        return SSOProvider.MICROSOFT
    raise HTTPException(status_code=404, detail="Unsupported SSO provider")

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> UserResponse:
    try:
        user = await auth_service.register_user(
            session,
            email=payload.email,
            password=payload.password,
            role=payload.role,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    await activity_service.log_event(
        session,
        event_type="auth.register",
        user_id=user.id,
        resource_type="user",
        resource_id=str(user.id),
        event_metadata={"role": user.role},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )
    await session.commit()
    logger.info("auth.registered", user_id=user.id, email=user.email, role=user.role)
    return _to_user_response(user)


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    user = await auth_service.authenticate_user(session, payload.email, payload.password)
    if user is None:
        await activity_service.log_event(
            session,
            event_type="auth.login_failed",
            event_metadata={"email": payload.email.lower()},
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent"),
            success=False,
        )
        await session.commit()
        raise HTTPException(status_code=401, detail="Invalid email or password")

    access_token = auth_service.create_access_token_for_user(user)
    await activity_service.log_event(
        session,
        event_type="auth.login",
        user_id=user.id,
        resource_type="user",
        resource_id=str(user.id),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )
    await session.commit()

    return TokenResponse(
        access_token=access_token,
        expires_in=settings.access_token_expire_minutes * 60,
        user=_to_user_response(user),
    )


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return _to_user_response(current_user)

@router.get("/preferences", response_model=PreferencesResponse)
async def get_preferences(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> PreferencesResponse:
    preferences = await auth_service.get_user_preferences(session, current_user.id)
    return PreferencesResponse(
        default_search_mode=preferences.default_search_mode,
        alert_frequency=preferences.alert_frequency,
        timezone=preferences.timezone,
        email_notifications_enabled=preferences.email_notifications_enabled,
        updated_at=preferences.updated_at.isoformat() if preferences.updated_at else None,
    )


@router.patch("/preferences", response_model=PreferencesResponse)
async def update_preferences(
    payload: PreferencesUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> PreferencesResponse:
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No preferences provided")

    preferences = await auth_service.update_user_preferences(
        session,
        current_user.id,
        default_search_mode=updates.get("default_search_mode"),
        alert_frequency=updates.get("alert_frequency"),
        timezone=updates.get("timezone"),
        email_notifications_enabled=updates.get("email_notifications_enabled"),
    )
    await activity_service.log_event(
        session,
        event_type="user.preferences_updated",
        user_id=current_user.id,
        resource_type="user_preferences",
        resource_id=str(preferences.id),
    )
    await session.commit()

    return PreferencesResponse(
        default_search_mode=preferences.default_search_mode,
        alert_frequency=preferences.alert_frequency,
        timezone=preferences.timezone,
        email_notifications_enabled=preferences.email_notifications_enabled,
        updated_at=preferences.updated_at.isoformat() if preferences.updated_at else None,
    )


@router.get("/admin/ping")
async def admin_ping(current_user: User = Depends(require_roles("admin"))) -> dict[str, str]:
    return {"status": "ok", "user": current_user.email}

@router.post(
    "/organizations", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED
)
async def create_organization(
    payload: OrganizationCreateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> OrganizationResponse:
    organization = await organization_service.create_organization(
        session,
        owner_id=current_user.id,
        name=payload.name,
    )
    await activity_service.log_event(
        session,
        event_type="organization.created",
        user_id=current_user.id,
        resource_type="organization",
        resource_id=str(organization.id),
    )
    await session.commit()
    return OrganizationResponse(
        id=organization.id,
        name=organization.name,
        owner_id=organization.owner_id,
        invite_code=organization.invite_code,
        created_at=organization.created_at.isoformat() if organization.created_at else None,
    )


@router.post("/organizations/{organization_id}/invites", response_model=OrganizationInviteResponse)
async def invite_to_organization(
    organization_id: int,
    payload: OrganizationInviteRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> OrganizationInviteResponse:
    try:
        invite = await organization_service.invite_user(
            session,
            organization_id=organization_id,
            invited_by_user_id=current_user.id,
            invited_email=payload.email,
            note=payload.note,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    await activity_service.log_event(
        session,
        event_type="organization.invite_created",
        user_id=current_user.id,
        resource_type="organization_invite",
        resource_id=str(invite.id),
        event_metadata={"organization_id": organization_id, "invited_email": invite.invited_email},
    )
    await session.commit()

    return OrganizationInviteResponse(
        id=invite.id,
        organization_id=invite.organization_id,
        invited_email=invite.invited_email,
        invite_token=invite.invite_token,
        invite_code=invite.invite_code,
        status=invite.status,
        expires_at=invite.expires_at.isoformat() if invite.expires_at else None,
    )


@router.post("/invites/{invite_token}/accept", response_model=InviteAcceptResponse)
async def accept_invite(
    invite_token: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> InviteAcceptResponse:
    try:
        membership = await organization_service.accept_invite(
            session, invite_token, current_user.id
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    await activity_service.log_event(
        session,
        event_type="organization.invite_accepted",
        user_id=current_user.id,
        resource_type="organization_member",
        resource_id=str(membership.id),
    )
    await session.commit()
    return InviteAcceptResponse(
        organization_id=membership.organization_id,
        user_id=membership.user_id,
        role=membership.role,
    )


@router.get("/sso/{provider}/start", response_model=SSOStartResponse)
async def sso_start(
    provider: str, state: str = Query(default_factory=lambda: secrets.token_urlsafe(16))
) -> SSOStartResponse:
    resolved_provider = _resolve_sso_provider(provider)
    result = sso_service.start_flow(resolved_provider, state)
    return SSOStartResponse(**result)


@router.get("/sso/{provider}/callback", response_model=SSOCallbackResponse)
async def sso_callback(
    provider: str,
    code: str = Query(..., min_length=1),
    state: str | None = Query(default=None),
) -> SSOCallbackResponse:
    resolved_provider = _resolve_sso_provider(provider)
    result = sso_service.callback_stub(resolved_provider, code, state)
    return SSOCallbackResponse(**result)
