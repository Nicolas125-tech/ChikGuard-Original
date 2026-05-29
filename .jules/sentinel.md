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
**Prevention:** Apply the `@require_auth()` decorator at the routing level for all device telemetry and configuration endpoints. Use explicit route decorators instead of relying solely on inner function guards.
