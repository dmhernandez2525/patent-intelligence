# Phase 11.1: Multi-User Authentication - Software Design Document

## Overview

Phase 11.1 introduces account authentication, role-based access control, organization membership, user preferences, activity logging, and optional JWT user context across existing endpoints.

## New Backend Components

### Models

- `src/models/user.py`
  - `User`: email/password account, role, login timestamps
  - `UserPreference`: default search mode, alert frequency, timezone
  - `UserActivityLog`: login/search/watchlist and other auditable events
- `src/models/organization.py`
  - `Organization`: owner and invite code
  - `OrganizationMember`: user membership with role
  - `OrganizationInvite`: pending/accepted invite flow

### Services

- `src/services/auth_service.py`
  - Registration with bcrypt hashing
  - Login validation and JWT issuing
  - User preference read/update
- `src/services/organization_service.py`
  - Organization creation, invite, accept invite flows
- `src/services/activity_service.py`
  - Centralized user activity logging
- `src/services/sso_service.py`
  - Google/Microsoft OAuth2 flow stubs

### Security + Middleware

- `src/utils/security.py`
  - `hash_password`, `verify_password`, JWT create/decode (`HS256`)
- `src/utils/user_rate_limiter.py`
  - Per-user token bucket rate limiting with Redis + in-memory fallback
- `src/api/middleware/auth_context.py`
  - Optional bearer token parsing into request state
  - Global per-user or per-IP rate limiting enforcement

### API Surface

- `src/api/routes/auth.py`
  - `POST /api/auth/register`
  - `POST /api/auth/login`
  - `GET /api/auth/me`
  - `GET/PATCH /api/auth/preferences`
  - `GET /api/auth/admin/ping` (admin role required)
  - `POST /api/auth/organizations`
  - `POST /api/auth/organizations/{organization_id}/invites`
  - `POST /api/auth/invites/{invite_token}/accept`
  - `GET /api/auth/sso/{provider}/start`
  - `GET /api/auth/sso/{provider}/callback`

## Personalization Threading

Existing route modules now accept optional user context through middleware/dependencies. Search and watchlist actions are logged with user identity when authenticated.

## Migration

- `src/database/migrations/versions/20260215_0001_add_user_auth_models.py`
  - Adds users, preferences, activity logs, organizations, memberships, and invites.

## Security Decisions

- Passwords are never stored in plain text.
- JWT claims include `sub`, `email`, and `role`, with expiry and issuance timestamps.
- Role checks are explicit and deny-by-default.
- Rate limiting keys are user-based for authenticated traffic and IP-based for anonymous traffic.

