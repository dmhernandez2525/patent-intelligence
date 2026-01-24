"""EPO Open Patent Services (OPS) API client.

Handles OAuth2 authentication and provides methods for accessing
DOCDB (bibliographic), INPADOC (legal status), and family data.

API Documentation: https://www.epo.org/searching-for-patents/data/web-services/ops.html
"""
import base64
from datetime import datetime, timedelta, timezone

import httpx

from src.config import settings
from src.utils.logger import logger
from src.utils.rate_limiter import RateLimiter


class EPOAuthError(Exception):
    """Raised when EPO authentication fails."""


class EPOAPIError(Exception):
    """Raised when EPO API returns an error."""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        super().__init__(f"EPO API error {status_code}: {message}")


class EPOClient:
    """Client for EPO Open Patent Services API."""

    AUTH_URL = "https://ops.epo.org/3.2/auth/accesstoken"
    BASE_URL = "https://ops.epo.org/3.2/rest-services"

    def __init__(
        self,
        consumer_key: str | None = None,
        consumer_secret: str | None = None,
    ):
        self.consumer_key = consumer_key or settings.epo_consumer_key
        self.consumer_secret = consumer_secret or settings.epo_consumer_secret
        self._access_token: str | None = None
        self._token_expires_at: datetime | None = None
        self._rate_limiter = RateLimiter(
            max_requests=10,  # EPO allows ~2 requests/sec for registered users
            time_window=5.0,
        )
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _authenticate(self) -> None:
        """Obtain OAuth2 access token from EPO."""
        if not self.consumer_key or not self.consumer_secret:
            raise EPOAuthError(
                "EPO consumer_key and consumer_secret are required. "
                "Register at https://developers.epo.org/"
            )

        credentials = base64.b64encode(
            f"{self.consumer_key}:{self.consumer_secret}".encode()
        ).decode()

        client = await self._get_client()
        response = await client.post(
            self.AUTH_URL,
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"grant_type": "client_credentials"},
        )

        if response.status_code != 200:
            raise EPOAuthError(f"Authentication failed: {response.status_code} {response.text}")

        data = response.json()
        self._access_token = data["access_token"]
        expires_in = int(data.get("expires_in", 1200))
        self._token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in - 60)

        logger.info("epo.authenticated", expires_in=expires_in)

    async def _ensure_token(self) -> str:
        """Ensure we have a valid access token."""
        if (
            self._access_token is None
            or self._token_expires_at is None
            or datetime.now(timezone.utc) >= self._token_expires_at
        ):
            await self._authenticate()
        return self._access_token  # type: ignore[return-value]

    async def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        """Make an authenticated request to EPO OPS."""
        await self._rate_limiter.acquire()
        token = await self._ensure_token()

        client = await self._get_client()
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }
        headers.update(kwargs.pop("headers", {}))

        url = f"{self.BASE_URL}/{path}"
        response = await client.request(method, url, headers=headers, **kwargs)

        if response.status_code == 401:
            # Token expired, re-authenticate and retry
            await self._authenticate()
            headers["Authorization"] = f"Bearer {self._access_token}"
            response = await client.request(method, url, headers=headers, **kwargs)

        if response.status_code == 403:
            logger.warning("epo.rate_limited", path=path)
            raise EPOAPIError(403, "Rate limited by EPO. Try again later.")

        if response.status_code == 404:
            return response  # Caller handles 404

        if response.status_code >= 400:
            raise EPOAPIError(response.status_code, response.text[:500])

        return response

    async def get_published_data(
        self,
        reference_type: str,
        input_format: str,
        number: str,
        endpoint: str = "biblio",
    ) -> dict | None:
        """
        Fetch published data from DOCDB.

        Args:
            reference_type: 'publication', 'application', or 'priority'
            input_format: 'docdb', 'epodoc', or 'original'
            number: Patent number (format depends on input_format)
            endpoint: 'biblio', 'abstract', 'full-cycle', 'claims', etc.
        """
        path = f"published-data/{reference_type}/{input_format}/{number}/{endpoint}"

        response = await self._request("GET", path)
        if response.status_code == 404:
            return None

        return response.json()

    async def search_publications(
        self,
        query: str,
        range_begin: int = 1,
        range_end: int = 25,
    ) -> dict | None:
        """
        Search published patents using CQL query syntax.

        Args:
            query: CQL query (e.g., 'ti=battery AND pa=samsung')
            range_begin: Start index (1-based)
            range_end: End index (max 100 per request)
        """
        path = "published-data/search/biblio"
        params = {"q": query, "Range": f"{range_begin}-{range_end}"}

        response = await self._request("GET", path, params=params)
        if response.status_code == 404:
            return None

        return response.json()

    async def get_family(
        self,
        reference_type: str,
        input_format: str,
        number: str,
    ) -> dict | None:
        """
        Fetch patent family data from INPADOC.

        Returns simple or extended family members.
        """
        path = f"family/{reference_type}/{input_format}/{number}/biblio"

        response = await self._request("GET", path)
        if response.status_code == 404:
            return None

        return response.json()

    async def get_legal_status(
        self,
        reference_type: str,
        input_format: str,
        number: str,
    ) -> dict | None:
        """
        Fetch legal status events from INPADOC.

        Returns legal events like grant, lapse, expiry, etc.
        """
        path = f"legal/{reference_type}/{input_format}/{number}"

        response = await self._request("GET", path)
        if response.status_code == 404:
            return None

        return response.json()

    async def get_register_data(
        self,
        input_format: str,
        number: str,
        endpoint: str = "biblio",
    ) -> dict | None:
        """
        Fetch register (procedural) data for EP applications.

        Only available for EP applications.
        """
        path = f"register/{input_format}/{number}/{endpoint}"

        response = await self._request("GET", path)
        if response.status_code == 404:
            return None

        return response.json()
