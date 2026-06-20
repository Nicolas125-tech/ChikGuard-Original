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

## 2026-05-29 - [Fix Exception Stack Trace Leak in API Error Responses]
**Vulnerability:** Several API endpoints (`/api/routes.py` and `/api/reports_api.py`) were exposing internal Python exception strings (`str(e)` or `exc`) directly to the client when a 500 internal server error occurred.
**Learning:** Detailed error messages can leak sensitive internal implementation details, such as variable names, file paths, or system architecture (stack traces), giving attackers insights into the backend systems.
**Prevention:** Catch all exceptions globally or per-endpoint, log the detailed `Exception` using a logger for debugging, and return a generic, safe error message to the client.

## 2026-05-29 - [Fix Missing Authentication on HLS Video Stream]
**Vulnerability:** The HLS video stream endpoint (`/api/stream_sota/<path:filename>`) in `stream_gateway.py` was exposed without the `@require_auth()` decorator. Any unauthenticated user could access the live camera feed of the facility.
**Learning:** Experimental or backend-specific streaming gateways (like FFMPEG/HLS pipelines) sometimes bypass standard API authentication mechanisms if implemented as independent blueprints without global middleware protection.
**Prevention:** Always enforce global authentication middlewares or ensure every exposed route (even static file servers for video segments) has explicit access control.

## 2026-05-29 - [Fix Logic Flaw / State Mutation before Auth Check]
**Vulnerability:** The `/api/voice/command` endpoint modified global system state (`estado_dispositivos`) *before* executing the permissions check (`_guard_critical_action`). Even if the request was subsequently denied (403), the IoT hardware state had already been mutated, leading to an authentication bypass/IDOR that could trigger critical facility systems.
**Learning:** Checking permissions at the end of a function is a classic time-of-check to time-of-use (TOCTOU) logic flaw. Any side effects (state modification, database writes, external requests) must occur *strictly after* all authorization checks have passed.
## 2026-05-29 - [Fix Missing Auth on Device Telemetry and Control Endpoints]
**Vulnerability:** Endpoints in `backend/src/api/devices.py` such as `/api/auto-mode`, `/api/ventilacao`, `/api/aquecedor`, `/api/luz-dimmer` and `/api/estado-dispositivos` lacked the `@require_auth()` decorator. While some POST requests were implicitly protected by `_guard_critical_action`, the GET requests leaked the entire device configurations, temperature targets, and operational states of the farm hardware to unauthenticated external users.
**Learning:** Depending entirely on deeply nested guard functions (like `_guard_critical_action`) or implicit checks can leave GET routes fully exposed. Attackers can use this information to map out facility patterns, know exactly when systems are online/offline, and infer operational procedures.
## 2026-05-29 - [Fix Missing Privilege Escalation Check for Admin Role]
**Vulnerability:** The PATCH endpoint `/api/accounts/users/<id>` in `backend/src/api/auth.py` properly prevented low-level users from elevating accounts to `superadmin`. However, it lacked the same check for the `admin` role. A user with basic `accounts.manage` permissions (e.g., an Operator) could elevate their own account or another account to `admin`, or modify existing `admin` accounts, bypassing the role hierarchy.
**Learning:** When implementing Role-Based Access Control (RBAC) and hierarchy logic, developers often fix the highest-tier vulnerability (like `superadmin` checks) but forget the intermediary tiers. This creates lateral or partial vertical privilege escalation paths.
## 2026-05-29 - [Improvement: HTTP Security Headers Hardening]
**Vulnerability:** The backend lacked several industry-standard HTTP security headers (e.g., `Strict-Transport-Security`, `X-Content-Type-Options`, `X-Frame-Options`, `Content-Security-Policy`). This omission could facilitate attacks like Clickjacking, MIME-type sniffing, or Man-in-the-Middle (downgrade to HTTP).
**Learning:** Returning security headers natively from the backend (via `@app.after_request`) ensures that all REST and Web API traffic is strictly protected, even if the reverse proxy (like Nginx) is misconfigured or bypassed in local/edge deployments.
**Prevention:** Always implement an automated middleware or `after_request` hook that injects these headers globally, enforcing `nosniff`, `DENY` for frames, and a strong CSP.

## 2026-05-30 - [Missing rate limiting on authentication and webhook endpoints]
**Vulnerability:** The `/api/login` and `/api/admin/notify-new-user` endpoints in `backend/src/api/auth.py` were missing the `@limiter.limit` decorator from `flask-limiter`. While there was manual application logic for the login, not having `flask-limiter` creates gaps and relies on custom code that can easily have errors. Missing rate limits on webhooks can lead to denial of service or excessive resource consumption.
**Learning:** Explicitly leveraging the standard initialized `flask-limiter` on sensitive endpoints like authentication routes ensures a unified and standard defense-in-depth security layer against brute force.
**Prevention:** Always apply `flask-limiter`'s `@limiter.limit` decorator to highly sensitive routes (such as logins and webhooks) to mitigate brute-force and DoS attacks reliably.

## 2026-06-14 - [Fix Missing JWT Validation Centralization in Video Route]
**Vulnerability:** The `/api/video` MJPEG streaming endpoint in `backend/src/api/routes.py` manually decoded the JWT token using `pyjwt.decode(...)` without invoking the centralized `@require_auth` logic.
**Learning:** Manual JWT decoding bypasses critical centralized checks (such as verifying if an account is `ACTIVE`, blacklisted, or possesses the required role definitions). Streaming endpoints relying on tokens via query parameters often make this mistake.
**Prevention:** To secure API endpoints that require authentication via URL query parameters, extend the centralized `@require_auth` decorator (e.g., `@require_auth(allow_query_token=True)`) to ensure all security guards execute uniformly.

## 2026-06-20 - [Safe Role Extraction for Missing Middleware Context in Auth Routes]
**Vulnerability:** Endpoints using `guard_critical_action` instead of `@require_auth()` do not explicitly inject `request.user_role` if the JWT middleware context is stripped or bypassing standard parsing due to structural differences. Direct extraction of `request.user_role` can raise an `AttributeError` or return `None`, leading to runtime errors instead of secure denial.
**Learning:** Even if `guard_critical_action` checks global endpoint permissions, checking explicit user roles dynamically requires robust fallback extraction (`getattr(request, "user_role", "viewer")`).
**Prevention:** When implementing Role-Based Access Control (RBAC) in Flask routes protected by custom guards, safely extract the role using a secure fallback before performing level arithmetic using dictionaries like `ROLE_LEVELS`.

## 2026-06-20 - [Fix Missing JWT Validation in FastAPI MJPEG Stream Endpoint]
**Vulnerability:** In the FastAPI migration (`backend/src/api/fastapi_webrtc.py`), the `/api/webrtc/video` endpoint expected a query parameter `token` for authentication, but only validated its presence (`if not token:`). It did not perform cryptographic validation (JWT decoding) to ensure the token was valid, signed by the application, or hadn't expired. This allowed unauthenticated users to access the live video stream by simply providing any string as a token.
**Learning:** `OAuth2PasswordBearer` (used by `get_current_user` in FastAPI) does not natively extract tokens from query parameters out of the box. Simply asking for `token: str = None` bypasses middleware validation. If you do not explicitly invoke `jwt.decode` on query-based tokens, you introduce an authentication bypass.
**Prevention:** To secure FastAPI endpoints requiring authentication via URL query parameters (e.g., streaming video feeds where `Bearer` headers aren't feasible via `<img src="..." />`), you must explicitly validate the token within the endpoint using `jwt.decode(token, SUPABASE_JWT_SECRET, algorithms=['HS256'], audience='authenticated')` or build a custom `Depends` that extracts and validates the token from the request query.

## 2026-06-20 - [Fix CORS Wildcard Vulnerability in FastAPI and WebSocket Services]
**Vulnerability:** The FastAPI middleware (`backend/main.py`) and the SocketIO ASGI app (`backend/src/api/fastapi_ws.py`) were configured with `allow_origins=["*"]` and `cors_allowed_origins='*'` respectively. This wildcard configuration allowed any external domain to make cross-origin requests or establish WebSocket connections.
**Learning:** Using a wildcard `'*'` for CORS circumvents strict HTTP CORS policies. For WebSocket specifically, it exposes the application to Cross-Site WebSocket Hijacking (CSWSH), allowing malicious pages to establish authenticated WebSocket connections if the user's session is active, or at the very least interact with APIs bypassing Same-Origin Policy.
**Prevention:** Always restrict CORS allowed origins to a centrally defined, explicit list of trusted domains (e.g., `ALLOWED_ORIGINS` in `src.security.headers`) instead of using wildcards in both HTTP middleware and WebSocket server initialization.
