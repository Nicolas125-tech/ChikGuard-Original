# auth.md

Instructions for agent registration and identity assertion on ChikGuard.

## Discovery
Our OAuth/OIDC metadata is located at `/.well-known/oauth-authorization-server`.
Protected resource metadata is at `/.well-known/oauth-protected-resource`.

## Register Endpoint
Post to `/api/agent/register` to register your agent. We support identity assertion and anonymous registrations.
