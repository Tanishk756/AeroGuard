# Stage C Authentication

## Architecture

Stage C uses opaque server-side sessions:

```text
credentials -> FastAPI -> Argon2id verification -> random session secret
           -> SHA-256 session hash in SQLite -> HttpOnly cookie
```

The raw session secret is never stored in the database, logs, exceptions, or
JSON responses. No JWT or bearer-token fallback is implemented.

## Configuration

Settings use the `AEROGUARD_` environment prefix:

- `SESSION_LIFETIME_MINUTES` (default `60`)
- `SESSION_COOKIE_NAME` (default `aeroguard_session`)
- `SESSION_COOKIE_PATH` (default `/api/v1`)
- `SESSION_COOKIE_SAMESITE` (default `lax`)
- `SESSION_COOKIE_SECURE` (default false only for local development)
- `SESSION_COOKIE_DOMAIN`
- `ALLOWED_ORIGINS` as a JSON array when set through environment configuration;
    local Vite defaults are `http://localhost:5173` and `http://127.0.0.1:5173`
- `CSRF_PROTECTION_ENABLED` (default true)
- `PASSWORD_MIN_LENGTH` (default `12`)
- `PASSWORD_MAX_LENGTH` (default `128`)

Production-like environments must enable secure cookies and configure origins.

## API

- `POST /api/v1/auth/login` accepts `identifier` and `password`, sets the cookie, and returns public user data.
- `POST /api/v1/auth/logout` revokes the current session and clears the cookie.
- `GET /api/v1/me` returns public user data for an active session.

Authentication failures use the existing structured error response and
correlation ID. Login deliberately uses `AUTH_INVALID_CREDENTIALS` for unknown,
incorrect, and disabled credentials. Protected requests use
`AUTH_UNAUTHENTICATED`, `AUTH_SESSION_EXPIRED`, `AUTH_SESSION_REVOKED`, or
`AUTH_USER_DISABLED`.

## Browser and Tauri transport

The cookie is HttpOnly, `SameSite=Lax`, and scoped to `/api/v1`. `Secure` is
false only for local HTTP development and true otherwise. Credentialed CORS uses
an explicit origin allowlist; wildcard origins are prohibited. State-changing
requests with a disallowed Origin are rejected. This origin boundary does not
replace a future full CSRF-token design for cross-site workflows.

The same cookie model is intended to be evaluated in the future Tauri webview.
Desktop-specific token bridges are deferred until native packaging is available.

## Initialization and testing

There is no default administrator or known password. Developers can explicitly
create a user with hidden interactive password input:

```powershell
Push-Location .\backend
..\.venv\Scripts\python.exe -m app.cli create-user
Pop-Location
```

Authentication tests use isolated temporary SQLite databases and cover hashing,
normalization, duplicates, login/logout, cookies, expiry, revocation, disabled
users, fixation resistance, origin rejection, and sensitive-value leakage.

## Deferred work

RBAC, roles, permissions, audit logging, API keys, password reset, MFA, account
lockout, production rate limiting, frontend authentication UI, WebSocket
authorization, and Tauri/native packaging remain outside Stage C.