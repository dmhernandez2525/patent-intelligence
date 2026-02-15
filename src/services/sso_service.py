"""SSO integration stubs for Google and Microsoft OAuth2."""

from enum import StrEnum
from urllib.parse import urlencode

from src.config import settings


class SSOProvider(StrEnum):
    GOOGLE = "google"
    MICROSOFT = "microsoft"


class SSOService:
    """Builds provider URLs and returns stub callback payloads."""

    def start_flow(self, provider: SSOProvider, state: str) -> dict:
        if provider == SSOProvider.GOOGLE:
            return self._build_google_flow(state)
        return self._build_microsoft_flow(state)

    def callback_stub(self, provider: SSOProvider, code: str, state: str | None) -> dict:
        return {
            "provider": provider.value,
            "status": "stub",
            "code_received": bool(code),
            "state": state,
            "message": (
                "OAuth callback received. Complete token exchange and profile mapping "
                "when production SSO credentials are configured."
            ),
        }

    def _build_google_flow(self, state: str) -> dict:
        configured = bool(settings.google_oauth_client_id and settings.google_oauth_redirect_uri)
        query = urlencode(
            {
                "response_type": "code",
                "client_id": settings.google_oauth_client_id,
                "redirect_uri": settings.google_oauth_redirect_uri,
                "scope": "openid email profile",
                "state": state,
                "access_type": "online",
                "prompt": "consent",
            }
        )
        return {
            "provider": SSOProvider.GOOGLE.value,
            "configured": configured,
            "authorization_url": f"https://accounts.google.com/o/oauth2/v2/auth?{query}",
        }

    def _build_microsoft_flow(self, state: str) -> dict:
        configured = bool(
            settings.microsoft_oauth_client_id and settings.microsoft_oauth_redirect_uri
        )
        query = urlencode(
            {
                "client_id": settings.microsoft_oauth_client_id,
                "response_type": "code",
                "redirect_uri": settings.microsoft_oauth_redirect_uri,
                "response_mode": "query",
                "scope": "openid email profile",
                "state": state,
            }
        )
        return {
            "provider": SSOProvider.MICROSOFT.value,
            "configured": configured,
            "authorization_url": (
                "https://login.microsoftonline.com/common/oauth2/v2.0/authorize?" + query
            ),
        }


sso_service = SSOService()
