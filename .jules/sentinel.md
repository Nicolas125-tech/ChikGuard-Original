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

## 2025-02-28 - [Sentinel] **Vulnerability:** Path Traversal in HLS Stream Gateway **Learning:** The Flask `send_from_directory` function was directly serving the user-provided `filename` from the API route (`/<path:filename>`). While `send_from_directory` is generally safe, using dynamic filenames directly from path parameters is an insecure practice without explicit sanitization, potentially risking file inclusion attacks if configurations or proxy behaviors change. **Prevention:** Always sanitize user-provided filenames using `werkzeug.utils.secure_filename` before passing them to file-serving routines like `send_from_directory`.
