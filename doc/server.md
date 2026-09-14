# Running the server

`mcp-shell-tools` serves the whole tool set over the Model Context Protocol. It
is built on the MCP Python SDK 2.x and speaks protocol revision 2026-07-28,
where every request carries its own protocol version and there is no
`initialize` handshake.

## Transports

| Transport | Use |
|---|---|
| `stdio` (default) | a client starts the server as a subprocess and talks over its pipes |
| `streamable-http` | the server listens on a port; clients connect over HTTP |

HTTP is served without sessions: nothing ties a client to the process between
requests. stdio carries no token, so authentication applies to HTTP only.

## Options

| Option | Default | Meaning |
|---|---|---|
| `--transport` | `stdio` | `stdio` or `streamable-http` |
| `--host` | `MCP_HOST`, else `127.0.0.1` | address to bind (HTTP) |
| `--port` | `MCP_PORT`, else `8000` | port to bind (HTTP) |
| `--path` | `/mcp` | path the endpoint answers on (HTTP) |
| `--working-dir` | current directory | where the tools start out |
| `--allowed-root` | the home directory | an allowed root; repeatable, replaces the default |
| `--state-dir` | `~/.mcp-shell-tools` | sessions, trash and grant; empty for none |
| `--mode` | `guarded` | `open`, `guarded` or `strict`, see [boundary](boundary.md) |
| `--exec` | off | let shell commands run without a grant |

## Environment

| Variable | Meaning |
|---|---|
| `MCP_HOST` | default for `--host` |
| `MCP_PORT` | default for `--port` |
| `MCP_OAUTH_ENABLED` | `true`, `yes` or `1` switches authentication on |
| `MCP_OAUTH_SERVER_URL` | the authorization server, passed on exactly as written, trailing slash included |
| `MCP_PUBLIC_URL` | public base URL of the server |
| `MCP_AUTH_METHOD` | how tokens are checked; `introspection` unless set |

## Refusing to start

The server stops before listening, with exit status 2 and a sentence on
standard error, when:

- HTTP would listen on an address other than loopback without authentication
- authentication is switched on but `MCP_OAUTH_SERVER_URL` or `MCP_PUBLIC_URL`
  is missing
- `MCP_AUTH_METHOD` names no known method
- the working directory does not exist

## Authentication

Over HTTP the server is an OAuth 2.0 protected resource (RFC 9728). It issues
no tokens itself; clients obtain them from the authorization server and send
them as `Authorization: Bearer <token>`.

The resource identifier is `MCP_PUBLIC_URL` without its trailing slash, followed
by `--path`. With `MCP_PUBLIC_URL=https://mcp.example.org/` and `--path /shell`
it is `https://mcp.example.org/shell`, and the metadata are published at
`https://mcp.example.org/.well-known/oauth-protected-resource/shell`.

| Request | Answer |
|---|---|
| no token, or a token the check rejects | `401` with `WWW-Authenticate` pointing to the metadata |
| a valid token without scope `user` | `403`, `error="insufficient_scope"` |
| a valid token with scope `user` | the request is served |

### Token introspection

The method `introspection` asks `<MCP_OAUTH_SERVER_URL>/introspect` about every
token (RFC 7662):

- The token is sent as a form field; the answer must say `"active": true`.
- An accepted token is remembered for five minutes, never beyond its `exp`.
  A token revoked at the issuer therefore stays usable for at most that long.
- Rejected tokens are not remembered.
- An unreachable authorization server, an error status or an answer that is not
  a JSON object rejects the token.
- The endpoint has to be HTTPS or on the loopback interface; anything else is
  refused at start, because the token would travel in the clear.

Whether a token was issued for this resource (`aud`) is not checked.

### Another method

A token check is any object with

```python
async def check(self, token: str) -> TokenInfo | None: ...
```

returning a `TokenInfo` for a valid token and `None` otherwise. To offer it,
add a factory that takes the authorization server URL to `CHECKS` in
`src/mcp_shell_tools/server/auth.py`; `MCP_AUTH_METHOD` then selects it by
name. Nothing in that module imports the SDK.

## Behind a reverse proxy

The proxy has to pass on:

1. Two routes per endpoint: the path itself and
   `/.well-known/oauth-protected-resource<path>`.
2. The `Authorization` header unchanged.
3. `Accept` and `Content-Type` unchanged.
4. The methods `POST`, `GET` and `DELETE`.
5. `text/event-stream` responses without buffering.
6. Request bodies of at least 4 MiB.

Bind the server to the address the proxy reaches, not to `127.0.0.1`. On a
loopback address the SDK turns on DNS rebinding protection and answers every
request whose `Host` header names the public domain with `421`.

A Traefik file provider entry for `/shell` on `mcp.example.org`, with the server
at `10.0.0.5:12204`:

```yaml
http:
  routers:
    mcp-shell-tools:
      rule: "Host(`mcp.example.org`) && PathPrefix(`/shell`)"
      entrypoints: [websecure]
      tls:
        certResolver: myresolver
      service: mcp-shell-tools
    mcp-shell-tools-metadata:
      rule: "Host(`mcp.example.org`) && Path(`/.well-known/oauth-protected-resource/shell`)"
      entrypoints: [websecure]
      tls:
        certResolver: myresolver
      service: mcp-shell-tools
  services:
    mcp-shell-tools:
      loadBalancer:
        servers:
          - url: "http://10.0.0.5:12204"
        responseForwarding:
          flushInterval: 100ms
```

## As a systemd user service

`~/.config/systemd/user/mcp-shell-tools.service`:

```ini
[Unit]
Description=MCP Shell Tools
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=/path/to/mcp-shell-tools/.venv/bin/mcp-shell-tools \
    --transport streamable-http \
    --path /shell \
    --working-dir /home/you
Environment=MCP_HOST=0.0.0.0
Environment=MCP_PORT=12204
Environment=MCP_OAUTH_ENABLED=true
Environment=MCP_OAUTH_SERVER_URL=https://auth.example.org/
Environment=MCP_PUBLIC_URL=https://mcp.example.org/
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
```

```bash
systemctl --user daemon-reload
systemctl --user enable --now mcp-shell-tools.service
journalctl --user -u mcp-shell-tools.service -f
```

Restarting the service takes the tools away from every connected client until
it is back. Grants take effect without a restart.

## Errors a client sees

A tool that refuses answers with `isError` and a sentence saying why, for
instance `no such file: /home/you/notes.txt`. A crash inside a tool reaches the
client only as `Error executing tool <name>`; its traceback goes to the server
log.
