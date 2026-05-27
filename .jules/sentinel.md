## 2024-05-27 - [Add Missing Auth Checks to Sensitive API Endpoints]
**Vulnerability:** Critical internal API endpoints (e.g. `/api/agents/chat` which hits the Gemini API, and `/api/sync/status`) were exposed without authentication. This allowed unauthenticated users to trigger LLM calls, costing money and potentially exposing sensitive state data about the IoT/Sync systems.
**Learning:** In Flask apps employing Blueprints, relying on decorators ensures protection only if consistently applied to all routes handling business logic or external APIs.
**Prevention:** Enforce the use of `@require_auth()` via code reviews or middleware validation for all sensitive endpoints not explicitly whitelisted.
