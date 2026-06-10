# Email Verification and Password Recovery

Public authentication routes for confirming a registered email address and resetting a forgotten password. Both flows use opaque tokens stored in Redis and deliver links via Bitrix24 CRM email activities when Bitrix integration is enabled.

Related code: `backend/auth/email_verification.py`, `backend/auth/password_recovery.py`, `backend/auth/router.py`.

---

## Overview

| Flow | Send link | Complete action |
|---|---|---|
| Email verification | `POST /email/send-confirmation` | `POST /email/confirm` |
| Password recovery | `POST /password/send-recovery` | `POST /password/reset` |

All four endpoints are **public** (no `Authorization` header). Each has a matching `OPTIONS` handler for CORS preflight.

After registration (`POST /register`), users are created with `email_verified=false`. Non-admin users must verify email before login, refresh, or protected API access succeed (HTTP 403). Password recovery is independent of verification status but still requires an active (non-cancelled) account.

---

## Prerequisites

- **Redis** — tokens, per-email cooldowns, and rate limits live in Redis.
- **Bitrix24** (production) — when `BITRIX_ENABLED=true`, confirmation and recovery emails are sent as outgoing CRM email activities (`crm.activity.add`) to the user’s mapped Bitrix contact.
- **Contact mapping** — the user must have a `maas_bitrix_ids_mapping` row for entity type `contact` unless `*_REQUIRE_BITRIX_CONTACT=false`.
- **Environment** — configure URL templates and feature flags in `.env` (see [Configuration](#configuration)).

---

## Email Verification

### Purpose

Let a registered user confirm ownership of their email address. On success, `users.email_verified` is set to `true` and `email_verified_at` is recorded.

### End-to-end flow

```
1. User registers (POST /register) → email_verified=false
2. Frontend calls POST /email/send-confirmation with the user's email
3. Backend issues a token in Redis and sends a Bitrix email with a link
4. User opens link → frontend page reads ?token= from URL
5. Frontend calls POST /email/confirm with the token
6. User can log in and use protected routes
```

### `POST /email/send-confirmation`

**Request**

```json
{
  "email": "user@example.com"
}
```

**Success response** (`200 OK`)

```json
{
  "message": "If the email is registered, a confirmation message has been sent."
}
```

**Behavior**

- Email is normalized (trimmed, lowercased) before lookup.
- If the address is unknown, already verified, on send cooldown, or email cannot be sent (e.g. missing Bitrix contact when required), the API still returns **the same generic message** — this avoids email enumeration.
- A new send revokes any previous verification token for that user (one active token per user).
- Confirmation link format: `EMAIL_VERIFICATION_CONFIRM_URL_TEMPLATE` with `{token}` replaced (default: `https://app.example.com/confirm-email?token={token}`).

**Example (curl)**

```bash
curl -X POST "https://api.example.com/email/send-confirmation" \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com"}'
```

### `POST /email/confirm`

**Request**

```json
{
  "token": "<token-from-email-link>"
}
```

**Success response** (`200 OK`)

```json
{
  "message": "Email confirmed.",
  "email_verified": true
}
```

**Behavior**

- Valid token marks the user verified and deletes the Redis token pair.
- Confirming an already-verified user is idempotent: same success message, token cleaned up.
- Empty or missing token → `400` with `"Invalid or expired confirmation link."`

**Example (curl)**

```bash
curl -X POST "https://api.example.com/email/confirm" \
  -H "Content-Type: application/json" \
  -d '{"token":"abc123..."}'
```

### Access control after verification

Non-admin users with `email_verified=false` receive **403** on login, refresh, and any route using `get_current_user`:

```json
{
  "detail": "Email address not verified. Please confirm your email before accessing your account."
}
```

Admins bypass this check.

---

## Password Recovery

### Purpose

Allow a user who forgot their password to receive a time-limited reset link, set a new password, and invalidate all existing refresh sessions.

### End-to-end flow

```
1. User requests recovery on "Forgot password" UI
2. Frontend calls POST /password/send-recovery with email
3. Backend issues a token in Redis and sends a Bitrix email with reset link
4. User opens link → frontend reads ?token= from URL
5. User submits new password → POST /password/reset
6. User must log in again (all refresh sessions revoked)
```

### `POST /password/send-recovery`

**Request**

```json
{
  "email": "user@example.com"
}
```

**Success response** (`200 OK`)

```json
{
  "message": "If the email is registered, a password recovery message has been sent."
}
```

**Behavior**

- Same anti-enumeration pattern as email verification.
- Skips cancelled accounts (`status=cancelled`) without revealing that fact.
- Does not require `email_verified=true` — unverified users can still reset password if the account exists and is active.
- Reset link: `PASSWORD_RECOVERY_RESET_URL_TEMPLATE` with `{token}` substituted (default: `https://app.example.com/reset-password?token={token}`).
- Issuing a new recovery email revokes the previous token for that user.

**Example (curl)**

```bash
curl -X POST "https://api.example.com/password/send-recovery" \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com"}'
```

### `POST /password/reset`

**Request**

```json
{
  "token": "<token-from-email-link>",
  "password": "newSecurePassword"
}
```

**Success response** (`200 OK`)

```json
{
  "message": "Password has been reset."
}
```

**Password rules**

- Non-empty (after trim).
- Minimum length **6 characters** (same as registration).

**Side effects on success**

- Password is bcrypt-hashed; `password_changed_at` updated.
- `must_change_password` cleared.
- Recovery token removed from Redis.
- **All refresh sessions** for that user are revoked in Redis — existing refresh cookies stop working.

**Example (curl)**

```bash
curl -X POST "https://api.example.com/password/reset" \
  -H "Content-Type: application/json" \
  -d '{"token":"abc123...","password":"newSecurePassword"}'
```

---

## Frontend integration

### Suggested pages

| Page | URL query param | API call |
|---|---|---|
| Confirm email | `token` | `POST /email/confirm` |
| Reset password | `token` | `POST /password/reset` |

Read the token from the query string (matching your `*_URL_TEMPLATE`), show a form for the new password on the reset page, then POST to the API.

### Send vs confirm UX

- **Resend confirmation**: call `POST /email/send-confirmation` again; respect cooldown (default 5 minutes between sends per email) and show a neutral message either way.
- **After reset**: redirect to login; do not assume an access token is still valid.

### CORS

Browsers may preflight `OPTIONS` on these paths; the auth router exposes matching `OPTIONS` handlers.

### Client IP and proxies

Rate limits use the first IP in `X-Forwarded-For` when present, otherwise the direct client host. Ensure your reverse proxy sets `X-Forwarded-For` correctly in production.

---

## Responses and errors

| Status | When | Typical `detail` / body |
|---|---|---|
| `200` | Success (including “silent” send skips) | Generic `message` in body |
| `400` | Invalid or expired token (confirm/reset) | `"Invalid or expired confirmation link."` or `"Invalid or expired recovery link."` |
| `422` | Validation error (e.g. password too short) | FastAPI validation errors |
| `429` | Rate limit exceeded | `"Too many requests. Please try again later."` + `Retry-After` header (seconds) |
| `503` | Feature disabled (`*_ENABLED=false`) | `"Email verification is not available."` or `"Password recovery is not available."` |

Send endpoints never return `404` for unknown emails.

---

## Redis keys

| Key pattern | Purpose |
|---|---|
| `auth:email-verify:token:{token}` | User id for verification token |
| `auth:email-verify:user:{user_id}` | Current verification token for user |
| `auth:email-verify:sent:{email}` | Send cooldown per normalized email |
| `auth:email-verify:rl:email:{email}` | Send rate limit per email |
| `auth:email-verify:rl:ip:{ip}` | Send rate limit per IP |
| `auth:email-verify:rl:confirm:ip:{ip}` | Confirm rate limit per IP |
| `auth:password-reset:token:{token}` | User id for recovery token |
| `auth:password-reset:user:{user_id}` | Current recovery token for user |
| `auth:password-reset:sent:{email}` | Send cooldown per normalized email |
| `auth:password-reset:rl:email:{email}` | Send rate limit per email |
| `auth:password-reset:rl:ip:{ip}` | Send rate limit per IP |
| `auth:password-reset:rl:reset:ip:{ip}` | Reset rate limit per IP |

---

## Configuration

Variables are loaded in `backend/core/config.py`. Defaults are documented in `.env.example`.

### Email verification

| Variable | Description | Default |
|---|---|---|
| `EMAIL_VERIFICATION_ENABLED` | Master switch | `true` |
| `EMAIL_VERIFICATION_TOKEN_TTL_SECONDS` | Token lifetime | `86400` (24h) |
| `EMAIL_VERIFICATION_CONFIRM_URL_TEMPLATE` | Link in email; must include `{token}` | `https://app.example.com/confirm-email?token={token}` |
| `EMAIL_VERIFICATION_SEND_COOLDOWN_SECONDS` | Min interval between sends per email | `300` |
| `EMAIL_VERIFICATION_RATE_LIMIT_PER_EMAIL` | Max sends per email per window | `3` |
| `EMAIL_VERIFICATION_RATE_LIMIT_PER_IP` | Max send/confirm requests per IP per window | `20` |
| `EMAIL_VERIFICATION_RATE_LIMIT_WINDOW_SECONDS` | Rate limit window | `3600` |
| `EMAIL_VERIFICATION_BITRIX_SUBJECT` | CRM activity subject | `Подтверждение электронной почты` |
| `EMAIL_VERIFICATION_BITRIX_MESSAGE_FROM` | `SETTINGS.MESSAGE_FROM` | (see `.env.example`) |
| `EMAIL_VERIFICATION_BITRIX_RESPONSIBLE_ID` | `RESPONSIBLE_ID` | `1` |
| `EMAIL_VERIFICATION_REQUIRE_BITRIX_CONTACT` | If `true`, no token/email without contact mapping | `true` |

### Password recovery

| Variable | Description | Default |
|---|---|---|
| `PASSWORD_RECOVERY_ENABLED` | Master switch | `true` |
| `PASSWORD_RECOVERY_TOKEN_TTL_SECONDS` | Token lifetime | `3600` (1h) |
| `PASSWORD_RECOVERY_RESET_URL_TEMPLATE` | Link in email; must include `{token}` | `https://app.example.com/reset-password?token={token}` |
| `PASSWORD_RECOVERY_SEND_COOLDOWN_SECONDS` | Min interval between sends per email | `300` |
| `PASSWORD_RECOVERY_RATE_LIMIT_PER_EMAIL` | Max sends per email per window | `3` |
| `PASSWORD_RECOVERY_RATE_LIMIT_PER_IP` | Max send/reset requests per IP per window | `20` |
| `PASSWORD_RECOVERY_RATE_LIMIT_WINDOW_SECONDS` | Rate limit window | `3600` |
| `PASSWORD_RECOVERY_BITRIX_SUBJECT` | CRM activity subject | `Восстановление пароля` |
| `PASSWORD_RECOVERY_BITRIX_MESSAGE_FROM` | `SETTINGS.MESSAGE_FROM` | (see `.env.example`) |
| `PASSWORD_RECOVERY_BITRIX_RESPONSIBLE_ID` | `RESPONSIBLE_ID` | `1` |
| `PASSWORD_RECOVERY_REQUIRE_BITRIX_CONTACT` | If `true`, no token/email without contact mapping | `true` |

Set `*_ENABLED=false` to disable endpoints (HTTP 503) without removing routes — useful for rollback or non-production environments.

---

## Operational notes

- **Bitrix failures**: If sending the CRM email fails after a token was created, the token is deleted and no cooldown is set; the client still sees the generic success message on send.
- **One token per user**: Requesting a new link invalidates the previous token for that user.
- **OpenAPI**: Interactive docs list these under the **Authentication** tag when the API is running (`/docs`).
- **Specs**: Formal requirements live in `openspec/specs/email-verification/spec.md` and `openspec/specs/password-recovery/spec.md`.
