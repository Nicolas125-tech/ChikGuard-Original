from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

router = APIRouter()

@router.get("/robots.txt", response_class=Response)
async def robots_txt(request: Request):
    base_url = str(request.base_url)
    robots_content = f"""User-agent: *
Allow: /
Disallow: /api/private/
Disallow: /admin/

User-agent: GPTBot
Disallow: /

User-agent: OAI-SearchBot
Allow: /

User-agent: Claude-Web
Allow: /

User-agent: Google-Extended
Disallow: /

Content-Signal: ai-train=no, search=yes, ai-input=no
Sitemap: {base_url}sitemap.xml
"""
    return Response(content=robots_content, media_type="text/plain")

@router.get("/sitemap.xml", response_class=Response)
async def sitemap_xml(request: Request):
    base_url = str(request.base_url)
    sitemap_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/protocol.html">
  <url>
    <loc>{base_url}</loc>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>{base_url}auth.md</loc>
    <changefreq>monthly</changefreq>
    <priority>0.5</priority>
  </url>
</urlset>
"""
    return Response(content=sitemap_content, media_type="application/xml")

@router.get("/auth.md", response_class=Response)
async def auth_md():
    md_content = """# auth.md

Instructions for agent registration and identity assertion on ChikGuard.

## Discovery
Our OAuth/OIDC metadata is located at `/.well-known/oauth-authorization-server`.
Protected resource metadata is at `/.well-known/oauth-protected-resource`.

## Register Endpoint
Post to `/api/agent/register` to register your agent. We support identity assertion and anonymous registrations.
"""
    return Response(content=md_content, media_type="text/markdown")

@router.get("/.well-known/api-catalog")
async def api_catalog(request: Request):
    base_url = str(request.base_url)
    # RFC 9727 linkset schema
    catalog = {
        "linkset": [
            {
                "anchor": f"{base_url}api",
                "service-desc": [
                    {
                        "href": f"{base_url}docs",
                        "type": "application/openapi+json"
                    }
                ],
                "service-doc": [
                    {
                        "href": f"{base_url}docs"
                    }
                ],
                "status": [
                    {
                        "href": f"{base_url}api/health/system"
                    }
                ]
            }
        ]
    }
    return JSONResponse(content=catalog, media_type="application/linkset+json")

@router.get("/.well-known/openid-configuration")
async def openid_configuration(request: Request):
    base_url = str(request.base_url)
    config = {
        "issuer": base_url.rstrip("/"),
        "authorization_endpoint": f"{base_url}oauth/authorize",
        "token_endpoint": f"{base_url}oauth/token",
        "jwks_uri": f"{base_url}oauth/jwks",
        "response_types_supported": ["code", "token", "id_token"],
        "grant_types_supported": ["authorization_code", "client_credentials"]
    }
    return JSONResponse(content=config)

@router.get("/.well-known/oauth-authorization-server")
async def oauth_authorization_server(request: Request):
    base_url = str(request.base_url)
    config = {
        "issuer": base_url.rstrip("/"),
        "authorization_endpoint": f"{base_url}oauth/authorize",
        "token_endpoint": f"{base_url}oauth/token",
        "jwks_uri": f"{base_url}oauth/jwks",
        "response_types_supported": ["code", "token"],
        "grant_types_supported": ["authorization_code", "client_credentials"],
        "agent_auth": {
            "skill": "https://workos.com/auth-md",
            "register_uri": f"{base_url}api/agent/register",
            "identity_types_supported": ["anonymous"]
        }
    }
    return JSONResponse(content=config)

@router.get("/.well-known/oauth-protected-resource")
async def oauth_protected_resource(request: Request):
    base_url = str(request.base_url)
    resource = {
        "resource": f"{base_url}api",
        "authorization_servers": [
            base_url.rstrip("/")
        ],
        "scopes_supported": ["read", "write"]
    }
    return JSONResponse(content=resource)

@router.get("/.well-known/mcp/server-card.json")
async def mcp_server_card(request: Request):
    base_url = str(request.base_url)
    card = {
        "serverInfo": {
            "name": "ChikGuard MCP Server",
            "version": "2.0.0"
        },
        "endpoint": f"{base_url}mcp",
        "capabilities": {
            "tools": {
                "list": True,
                "call": True
            },
            "resources": {
                "list": True
            }
        }
      }
    return JSONResponse(content=card)

@router.get("/.well-known/agent-skills/index.json")
async def agent_skills_index():
    index = {
        "$schema": "https://schemas.agentskills.io/discovery/0.2.0/schema.json",
        "skills": [
            {
                "name": "robots-txt",
                "type": "skill-md",
                "description": "Crawler rules and discovery pathways",
                "url": "https://isitagentready.com/.well-known/agent-skills/robots-txt/SKILL.md",
                "digest": "sha256:7f058097f5fa26bc2bf3d748f21950d9959dc3dc7dc11059f13dc1e2dfa9a3b2"
            }
        ]
    }
    return JSONResponse(content=index)
