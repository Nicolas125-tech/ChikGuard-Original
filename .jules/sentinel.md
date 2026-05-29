## 2026-05-28 - [Overly Permissive WebSocket CORS] 
**Vulnerability:** SocketIO was initialized with `cors_allowed_origins="*"` while the HTTP routes used strict `ALLOWED_ORIGINS`, allowing any origin to connect to the websocket.
**Learning:** WebSocket implementations can inadvertently bypass strict HTTP CORS policies if not explicitly configured with the same origin restrictions. This creates a gap where attackers might exploit WebSocket connections (CSWSH) even when REST APIs are protected.
**Prevention:** Always reuse the same `ALLOWED_ORIGINS` constants from security/header modules when configuring WebSocket services like `SocketIO`.

## 2024-05-27 - [Add Missing Auth Checks to Sensitive API Endpoints]
**Vulnerability:** Critical internal API endpoints (e.g. `/api/agents/chat` which hits the Gemini API, and `/api/sync/status`) were exposed without authentication. This allowed unauthenticated users to trigger LLM calls, costing money and potentially exposing sensitive state data about the IoT/Sync systems.
**Learning:** In Flask apps employing Blueprints, relying on decorators ensures protection only if consistently applied to all routes handling business logic or external APIs.
**Prevention:** Enforce the use of `@require_auth()` via code reviews or middleware validation for all sensitive endpoints not explicitly whitelisted.

## 2024-05-27 - [Add Missing Auth Checks to Sensor API Endpoints]
**Vulnerability:** The `/api/sensors/history`, `/api/acoustic/live`, `/api/acoustic/history`, and other telemetry endpoints in `backend/src/api/sensors_api.py` were missing the `@require_auth()` decorator. This exposed internal sensor states, thermal anomalies, and telemetry history to any unauthenticated user on the network.
**Learning:** Endpoints meant strictly for internal application logic or dashboard visualization often lack route-level authentication decorators during initial development, relying mistakenly on frontend obfuscation or network isolation.
**Prevention:** Implement a global "secure-by-default" middleware policy that requires authentication for all `/api/*` endpoints unless specifically opted out via a `@public_route` decorator.

## 2024-05-27 - [Fix Privilege Escalation / IDOR in Admin Account Management]
**Vulnerability:** The `/api/admin/approve-user` and `/api/accounts/users/<id>` endpoints allowed any user with `accounts.manage` permission (e.g. an "operator" or a lower-privileged "admin") to elevate their own privileges or someone else's to `superadmin` by changing the `target_role` / `role` directly in the payload.
**Learning:** Checking for general permissions (e.g., `accounts.manage`) is not enough. We must explicitly check if the user is authorized to assign or mutate high-privilege roles to prevent privilege escalation.
**Prevention:** Implement strict role hierarchy checks. Users should never be able to assign roles that have equal or higher privilege levels than their own.

## 2024-05-29 - Authorization Bypass in Voice Command API
**Vulnerability:** The `/api/voice/command` endpoint modified global application state (`estado_dispositivos`) and processed command logic *before* invoking the internal authorization and authentication guard (`_guard_critical_action()`). This allowed unauthenticated attackers to mutate device states, bypassing security controls.
**Learning:** Inline authorization guards must strictly be called at the very beginning of the endpoint's execution flow. Any state mutation or side effect preceding the guard completely defeats its purpose.
**Prevention:** Structure endpoints into discrete phases: 1) Intent extraction/parsing, 2) Authorization/Authentication Guard check based on intent, 3) State mutation/execution. Never mix state mutations into the intent extraction phase.
