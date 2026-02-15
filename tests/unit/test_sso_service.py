"""Tests for SSO stub service."""

from src.services.sso_service import SSOProvider, sso_service


def test_google_start_flow_contains_provider_and_url() -> None:
    result = sso_service.start_flow(SSOProvider.GOOGLE, state="abc")
    assert result["provider"] == "google"
    assert "authorization_url" in result


def test_microsoft_start_flow_contains_provider_and_url() -> None:
    result = sso_service.start_flow(SSOProvider.MICROSOFT, state="xyz")
    assert result["provider"] == "microsoft"
    assert "authorization_url" in result


def test_callback_stub_response_shape() -> None:
    result = sso_service.callback_stub(SSOProvider.GOOGLE, code="code", state="state")
    assert result["provider"] == "google"
    assert result["code_received"] is True
    assert result["status"] == "stub"
