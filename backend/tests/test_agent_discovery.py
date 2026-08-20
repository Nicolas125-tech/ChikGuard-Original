import sys
import importlib
if "cv2" in sys.modules and type(sys.modules["cv2"]).__name__ == "MagicMock":
    del sys.modules["cv2"]
import cv2
import os
import sys

# Ajusta sys.path para enxergar src/ e o backend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

import pytest
from fastapi.testclient import TestClient
from main import fastapi_app

client = TestClient(fastapi_app)

def test_robots_txt():
    """Garante que /robots.txt seja servido como text/plain com HTTP 200 e regras de User-agent."""
    response = client.get("/robots.txt")
    assert response.status_code == 200
    assert "text/plain" in response.headers.get("content-type", "")
    content = response.text
    assert "User-agent: *" in content
    assert "User-agent: GPTBot" in content
    assert "User-agent: OAI-SearchBot" in content
    assert "User-agent: Claude-Web" in content
    assert "User-agent: Google-Extended" in content
    assert "Content-Signal: ai-train=no" in content
    assert "Sitemap:" in content

def test_sitemap_xml():
    """Garante que /sitemap.xml seja retornado como XML com HTTP 200."""
    response = client.get("/sitemap.xml")
    assert response.status_code == 200
    assert "xml" in response.headers.get("content-type", "")
    assert "<urlset" in response.text

def test_homepage_link_headers():
    """Garante que a página inicial retorne cabeçalhos de resposta Link para descoberta de agentes."""
    response = client.get("/")
    assert response.status_code == 200
    link_header = response.headers.get("Link", "")
    assert 'rel="api-catalog"' in link_header
    assert 'rel="service-doc"' in link_header

def test_homepage_markdown_negotiation():
    """Garante que a página inicial retorne Markdown ao receber Accept: text/markdown."""
    # Requisição padrão
    response_html = client.get("/")
    assert response_html.status_code == 200
    
    # Requisição com accept text/markdown
    response_md = client.get("/", headers={"Accept": "text/markdown"})
    assert response_md.status_code == 200
    assert "text/markdown" in response_md.headers.get("content-type", "")
    assert "x-markdown-tokens" in response_md.headers
    assert "# ChikGuard" in response_md.text

def test_api_catalog():
    """Garante que /.well-known/api-catalog retorne application/linkset+json com a lista de endpoints."""
    response = client.get("/.well-known/api-catalog")
    assert response.status_code == 200
    assert "application/linkset+json" in response.headers.get("content-type", "")
    data = response.json()
    assert "linkset" in data
    assert len(data["linkset"]) > 0
    assert "anchor" in data["linkset"][0]
    assert "service-desc" in data["linkset"][0]

def test_oauth_discovery():
    """Garante que /.well-known/openid-configuration retorne os metadados corretos de OIDC."""
    response = client.get("/.well-known/openid-configuration")
    assert response.status_code == 200
    data = response.json()
    assert "issuer" in data
    assert "authorization_endpoint" in data
    assert "token_endpoint" in data
    assert "jwks_uri" in data

def test_oauth_authorization_server():
    """Garante que /.well-known/oauth-authorization-server retorne metadados com agent_auth."""
    response = client.get("/.well-known/oauth-authorization-server")
    assert response.status_code == 200
    data = response.json()
    assert "agent_auth" in data
    assert "register_uri" in data["agent_auth"]

def test_oauth_protected_resource():
    """Garante que /.well-known/oauth-protected-resource retorne os metadados do recurso."""
    response = client.get("/.well-known/oauth-protected-resource")
    assert response.status_code == 200
    data = response.json()
    assert "resource" in data
    assert "authorization_servers" in data

def test_auth_md():
    """Garante que /auth.md seja retornado como markdown com cabeçalho auth.md."""
    response = client.get("/auth.md")
    assert response.status_code == 200
    assert "text/markdown" in response.headers.get("content-type", "")
    assert "# auth.md" in response.text or "# Auth.md" in response.text

def test_mcp_server_card():
    """Garante que /.well-known/mcp/server-card.json seja retornado com informações do MCP."""
    response = client.get("/.well-known/mcp/server-card.json")
    assert response.status_code == 200
    data = response.json()
    assert "serverInfo" in data
    assert "capabilities" in data

def test_agent_skills_index():
    """Garante que /.well-known/agent-skills/index.json retorne o índice de habilidades."""
    response = client.get("/.well-known/agent-skills/index.json")
    assert response.status_code == 200
    data = response.json()
    assert "$schema" in data
    assert "skills" in data
