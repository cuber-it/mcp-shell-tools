"""How a bearer token is checked, and how the check is configured."""

from __future__ import annotations

import asyncio
import time

import pytest

from loopback import Issuer, free_port
from mcp_shell_tools.server.auth import (
    REQUIRED_SCOPES,
    AuthConfig,
    ConfigurationError,
    IntrospectionCheck,
    TokenInfo,
    auth_from_environment,
    guard_exposure,
)

ACTIVE = {"active": True, "client_id": "claude", "scope": "user mcp", "sub": "s-1"}
SWITCHED_ON = {
    "MCP_OAUTH_ENABLED": "true",
    "MCP_OAUTH_SERVER_URL": "https://issuer.example/",
    "MCP_PUBLIC_URL": "https://mcp.example/",
}


def checked(check: IntrospectionCheck, token: str) -> TokenInfo | None:
    """Run one check to its end."""
    return asyncio.run(check.check(token))


def test_an_active_token_is_accepted_with_what_it_stands_for(issuer: Issuer) -> None:
    expires = int(time.time()) + 3600
    issuer.answer = {**ACTIVE, "exp": expires}

    info = checked(IntrospectionCheck(issuer.introspection), "good")

    assert info == TokenInfo("claude", ("user", "mcp"), "s-1", expires)
    assert issuer.tokens == ["good"]


def test_an_inactive_token_is_rejected(issuer: Issuer) -> None:
    assert checked(IntrospectionCheck(issuer.introspection), "bad") is None


@pytest.mark.parametrize("status", [401, 500])
def test_an_error_status_rejects_even_an_active_answer(
    issuer: Issuer, status: int
) -> None:
    issuer.answer = ACTIVE
    issuer.status = status

    assert checked(IntrospectionCheck(issuer.introspection), "good") is None


@pytest.mark.parametrize("body", [b"not json", b"[1, 2]", b'{"active": "yes"}', b""])
def test_an_unusable_answer_rejects(issuer: Issuer, body: bytes) -> None:
    issuer.body = body

    assert checked(IntrospectionCheck(issuer.introspection), "good") is None


def test_an_unreachable_issuer_rejects() -> None:
    check = IntrospectionCheck(f"http://127.0.0.1:{free_port()}/introspect", timeout=2)

    assert checked(check, "good") is None


def test_an_answer_with_unexpected_fields_still_counts(issuer: Issuer) -> None:
    issuer.answer = {"active": True, "scope": 7, "sub": ["x"], "exp": "soon", "x": 1}

    info = checked(IntrospectionCheck(issuer.introspection), "good")

    assert info == TokenInfo("", (), None, None)


def test_an_accepted_token_is_remembered(issuer: Issuer) -> None:
    issuer.answer = ACTIVE
    check = IntrospectionCheck(issuer.introspection)
    checked(check, "good")
    issuer.answer = {"active": False}

    assert checked(check, "good") is not None
    assert issuer.tokens == ["good"]


def test_a_rejected_token_is_asked_about_again(issuer: Issuer) -> None:
    check = IntrospectionCheck(issuer.introspection)
    checked(check, "bad")
    issuer.answer = ACTIVE

    assert checked(check, "bad") is not None
    assert issuer.tokens == ["bad", "bad"]


def test_without_a_cache_window_every_check_asks(issuer: Issuer) -> None:
    issuer.answer = ACTIVE
    check = IntrospectionCheck(issuer.introspection, cache_seconds=0)

    checked(check, "good")
    checked(check, "good")

    assert issuer.tokens == ["good", "good"]


def test_an_expired_token_is_not_remembered(issuer: Issuer) -> None:
    issuer.answer = {**ACTIVE, "exp": int(time.time()) - 10}
    check = IntrospectionCheck(issuer.introspection)

    checked(check, "stale")
    checked(check, "stale")

    assert issuer.tokens == ["stale", "stale"]


@pytest.mark.parametrize(
    ("endpoint", "refused"),
    [
        ("https://issuer.example/introspect", False),
        ("http://127.0.0.1:9/introspect", False),
        ("http://localhost:9/introspect", False),
        ("http://issuer.example/introspect", True),
        ("http://localhost.example/introspect", True),
        ("ftp://127.0.0.1/introspect", True),
    ],
)
def test_tokens_travel_only_encrypted_or_locally(endpoint: str, refused: bool) -> None:
    if refused:
        with pytest.raises(ConfigurationError, match="in the clear"):
            IntrospectionCheck(endpoint)
    else:
        assert isinstance(IntrospectionCheck(endpoint), IntrospectionCheck)


@pytest.mark.parametrize("switch", ["", "false", "0", "no"])
def test_authentication_is_off_unless_switched_on(switch: str) -> None:
    env = {**SWITCHED_ON, "MCP_OAUTH_ENABLED": switch}

    assert auth_from_environment(env, "/mcp") is None


@pytest.mark.parametrize("missing", ["MCP_OAUTH_SERVER_URL", "MCP_PUBLIC_URL"])
def test_switched_on_but_incomplete_is_refused(missing: str) -> None:
    env = {name: value for name, value in SWITCHED_ON.items() if name != missing}

    with pytest.raises(ConfigurationError, match="have to be set"):
        auth_from_environment(env, "/mcp")


def test_an_unknown_method_is_refused() -> None:
    env = {**SWITCHED_ON, "MCP_AUTH_METHOD": "carrier-pigeon"}

    with pytest.raises(ConfigurationError, match="no such auth method"):
        auth_from_environment(env, "/mcp")


@pytest.mark.parametrize("public", ["https://mcp.example/", "https://mcp.example"])
def test_the_resource_is_the_public_url_with_the_path(public: str) -> None:
    auth = auth_from_environment({**SWITCHED_ON, "MCP_PUBLIC_URL": public}, "/shell")

    assert isinstance(auth, AuthConfig)
    assert auth.resource_url == "https://mcp.example/shell"
    assert auth.issuer_url == "https://issuer.example/"
    assert auth.required_scopes == REQUIRED_SCOPES


def test_introspection_at_the_issuer_is_the_default_method(issuer: Issuer) -> None:
    issuer.answer = ACTIVE
    env = {**SWITCHED_ON, "MCP_OAUTH_SERVER_URL": f"{issuer.url}/"}

    auth = auth_from_environment(env, "/mcp")

    assert isinstance(auth, AuthConfig)
    assert asyncio.run(auth.check.check("good")) is not None
    assert issuer.tokens == ["good"]


@pytest.mark.parametrize(
    ("transport", "host", "authenticated", "refused"),
    [
        ("stdio", "0.0.0.0", False, False),
        ("streamable-http", "127.0.0.1", False, False),
        ("streamable-http", "::1", False, False),
        ("streamable-http", "0.0.0.0", False, True),
        ("streamable-http", "0.0.0.0", True, False),
    ],
)
def test_the_network_gets_the_tools_only_with_authentication(
    transport: str, host: str, authenticated: bool, refused: bool
) -> None:
    auth = auth_from_environment(SWITCHED_ON, "/mcp") if authenticated else None

    if refused:
        with pytest.raises(ConfigurationError, match="without authentication"):
            guard_exposure(transport, host, auth)
    else:
        assert guard_exposure(transport, host, auth) is None
