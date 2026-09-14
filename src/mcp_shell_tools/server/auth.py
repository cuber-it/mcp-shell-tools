"""Who may call the server: token checks, and the settings they are built from.

Nothing here imports the SDK; :mod:`.app` hands the configured check to it. A
check is anything with an async ``check(token)``, so another way of verifying
tokens is one class and one entry in :data:`CHECKS`, chosen with
``MCP_AUTH_METHOD``.

The first way is token introspection (RFC 7662): the token is handed to the
authorization server, which says whether it is active and what it stands for.
Anything but a clear yes rejects the request, an unreachable authorization
server included.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Protocol

DEFAULT_METHOD = "introspection"
INTROSPECTION_PATH = "/introspect"
REQUIRED_SCOPES = ("user",)
LOCAL_HOSTS = ("127.0.0.1", "localhost", "::1")
CACHE_SECONDS = 300.0
TIMEOUT_SECONDS = 10.0
SWITCHED_ON = ("1", "true", "yes")

logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """The server is configured in a way it refuses to start with."""


@dataclass(frozen=True)
class TokenInfo:
    """What an accepted bearer token stands for.

    Attributes:
        client_id: Client the token was issued to.
        scopes: Scopes the token carries.
        subject: Who the token speaks for, when the issuer says so.
        expires_at: Unix time the token expires at, or None when not said.
    """

    client_id: str
    scopes: tuple[str, ...]
    subject: str | None = None
    expires_at: int | None = None


class TokenCheck(Protocol):
    """Whatever decides whether a bearer token is valid."""

    async def check(self, token: str) -> TokenInfo | None:
        """Return what the token stands for, or None to reject it."""


@dataclass(frozen=True)
class AuthConfig:
    """How callers are authenticated.

    Attributes:
        issuer_url: The authorization server clients are sent to.
        resource_url: The public URL this server is known by.
        required_scopes: Scopes every token has to carry.
        check: What decides whether a token is valid.
    """

    issuer_url: str
    resource_url: str
    required_scopes: tuple[str, ...]
    check: TokenCheck


class IntrospectionCheck:
    """Asks the authorization server about a token, and remembers briefly.

    Only accepted tokens are remembered, for at most ``cache_seconds``; a token
    revoked at the issuer stays usable that long.
    """

    def __init__(
        self,
        endpoint: str,
        cache_seconds: float = CACHE_SECONDS,
        timeout: float = TIMEOUT_SECONDS,
    ) -> None:
        """Bind the check to an introspection endpoint.

        Raises:
            ConfigurationError: The endpoint is neither HTTPS nor on this
                machine, so tokens would travel in the clear.
        """
        parts = urllib.parse.urlsplit(endpoint)
        local = parts.scheme == "http" and parts.hostname in LOCAL_HOSTS
        if parts.scheme != "https" and not local:
            raise ConfigurationError(
                f"refusing to send tokens in the clear: {endpoint}"
            )
        self._endpoint = endpoint
        self._cache_seconds = cache_seconds
        self._timeout = timeout
        self._remembered: dict[str, tuple[TokenInfo, float]] = {}

    async def check(self, token: str) -> TokenInfo | None:
        """Return what the token stands for, or None to reject it."""
        key = hashlib.sha256(token.encode()).hexdigest()
        info, valid_until = self._remembered.get(key, (None, 0.0))
        if info is not None and time.monotonic() < valid_until:
            return info

        answer = await asyncio.to_thread(self._ask, token)
        if answer.get("active") is not True:
            return None
        info = _token_info(answer)
        self._remember(key, info)
        return info

    def _ask(self, token: str) -> dict[str, Any]:
        """Ask the authorization server about one token.

        Blocking; :meth:`check` runs it off the event loop.

        Returns:
            The decoded answer, or an empty one when the server could not be
            asked or gave no JSON object. An empty answer is not active.
        """
        request = urllib.request.Request(
            self._endpoint,
            data=urllib.parse.urlencode({"token": token}).encode(),
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                body = response.read()
        except urllib.error.HTTPError as err:
            logger.info("introspection answered HTTP %s", err.code)
            return {}
        except (urllib.error.URLError, TimeoutError) as err:
            logger.warning("introspection endpoint unreachable: %s", err)
            return {}
        try:
            answer = json.loads(body)
        except ValueError:
            logger.warning("introspection answered without JSON")
            return {}
        return answer if isinstance(answer, dict) else {}

    def _remember(self, key: str, info: TokenInfo) -> None:
        """Keep an answer for the window, never beyond the token's expiry."""
        now = time.monotonic()
        valid_until = now + self._cache_seconds
        if info.expires_at is not None:
            valid_until = min(valid_until, now + info.expires_at - time.time())
        self._remembered = {
            kept: entry for kept, entry in self._remembered.items() if entry[1] > now
        }
        if valid_until > now:
            self._remembered[key] = (info, valid_until)


def _token_info(answer: dict[str, Any]) -> TokenInfo:
    """Read what an active introspection answer says about its token."""
    scope = answer.get("scope")
    subject = answer.get("sub")
    expires = answer.get("exp")
    return TokenInfo(
        client_id=str(answer.get("client_id", "")),
        scopes=tuple(scope.split()) if isinstance(scope, str) else (),
        subject=subject if isinstance(subject, str) else None,
        expires_at=int(expires) if isinstance(expires, int | float) else None,
    )


def _introspection(issuer_url: str) -> TokenCheck:
    """Return the introspection check at the issuer's introspection path."""
    return IntrospectionCheck(issuer_url.rstrip("/") + INTROSPECTION_PATH)


CHECKS: dict[str, Callable[[str], TokenCheck]] = {"introspection": _introspection}


def auth_from_environment(env: Mapping[str, str], path: str) -> AuthConfig | None:
    """Read how callers are authenticated.

    ``MCP_OAUTH_ENABLED`` switches it on. ``MCP_OAUTH_SERVER_URL`` names the
    authorization server and is passed on exactly as written, trailing slash
    included. ``MCP_PUBLIC_URL`` is the public base URL; the resource this
    server is known by is that URL with the endpoint path, so two servers
    under one host stay two resources. ``MCP_AUTH_METHOD`` picks the check,
    ``introspection`` unless set.

    Returns:
        The settings, or None when authentication is switched off.

    Raises:
        ConfigurationError: Authentication is switched on but incomplete, or
            the method is unknown.
    """
    if env.get("MCP_OAUTH_ENABLED", "").strip().lower() not in SWITCHED_ON:
        return None
    issuer = env.get("MCP_OAUTH_SERVER_URL", "").strip()
    public = env.get("MCP_PUBLIC_URL", "").strip()
    if not issuer or not public:
        raise ConfigurationError(
            "MCP_OAUTH_ENABLED is set, so MCP_OAUTH_SERVER_URL and MCP_PUBLIC_URL "
            "have to be set as well"
        )
    method = env.get("MCP_AUTH_METHOD", DEFAULT_METHOD).strip()
    if method not in CHECKS:
        raise ConfigurationError(
            f"no such auth method {method!r}, choose from {sorted(CHECKS)}"
        )
    return AuthConfig(
        issuer_url=issuer,
        resource_url=public.rstrip("/") + path,
        required_scopes=REQUIRED_SCOPES,
        check=CHECKS[method](issuer),
    )


def guard_exposure(transport: str, host: str, auth: AuthConfig | None) -> None:
    """Refuse to serve the tools to the network with nobody checking who calls.

    Raises:
        ConfigurationError: HTTP would listen beyond this machine without
            authentication.
    """
    if transport == "stdio" or auth is not None or host in LOCAL_HOSTS:
        return
    raise ConfigurationError(
        f"refusing to serve {host} without authentication; set "
        "MCP_OAUTH_ENABLED=true, or bind to 127.0.0.1 for local use"
    )
