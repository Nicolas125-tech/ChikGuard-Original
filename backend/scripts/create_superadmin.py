"""
Script para criar a conta de Super Admin no Supabase Auth + profiles.
Usa a Service Role Key para ter acesso administrativo completo.
"""
import os
import sys
import requests
from dotenv import load_dotenv

# Load .env from backend directory
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
load_dotenv(env_path)

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

if not SUPABASE_URL or not SERVICE_ROLE_KEY:
    print("[ERRO] SUPABASE_URL ou SUPABASE_SERVICE_ROLE_KEY nao configurados no .env")
    sys.exit(1)

SUPERADMIN_EMAIL = "nicolasbissoqui@gmail.com"
SUPERADMIN_PASSWORD = "chikguard_admin_secure"

headers = {
    "apikey": SERVICE_ROLE_KEY,
    "Authorization": f"Bearer {SERVICE_ROLE_KEY}",
    "Content-Type": "application/json",
}


def create_auth_user():
    """Cria o usuario no Supabase Auth via Admin API."""
    print(f"[AUTH] Criando usuario no Supabase Auth: {SUPERADMIN_EMAIL}")

    # First, check if user already exists by listing users
    resp = requests.get(
        f"{SUPABASE_URL}/auth/v1/admin/users",
        headers=headers,
        timeout=15,
    )

    if resp.status_code == 200:
        users = resp.json().get("users", [])
        for user in users:
            if user.get("email", "").lower() == SUPERADMIN_EMAIL.lower():
                user_id = user["id"]
                print(f"[OK] Usuario ja existe no Auth: {user_id}")
                return user_id

    # Create the user
    payload = {
        "email": SUPERADMIN_EMAIL,
        "password": SUPERADMIN_PASSWORD,
        "email_confirm": True,
        "app_metadata": {
            "role": "superadmin",
        },
        "user_metadata": {
            "full_name": "Nicolas Bissoqui",
            "role": "superadmin",
        },
    }

    resp = requests.post(
        f"{SUPABASE_URL}/auth/v1/admin/users",
        headers=headers,
        json=payload,
        timeout=15,
    )

    if resp.status_code in (200, 201):
        user_id = resp.json()["id"]
        print(f"[OK] Usuario criado no Auth com sucesso! ID: {user_id}")
        return user_id
    else:
        print(f"[ERRO] Erro ao criar usuario no Auth: {resp.status_code}")
        print(resp.text)
        if "already been registered" in resp.text:
            print("[AVISO] Usuario ja registrado, buscando ID...")
            resp2 = requests.get(
                f"{SUPABASE_URL}/auth/v1/admin/users",
                headers=headers,
                timeout=15,
            )
            if resp2.status_code == 200:
                for user in resp2.json().get("users", []):
                    if user.get("email", "").lower() == SUPERADMIN_EMAIL.lower():
                        return user["id"]
        return None


def create_profile(user_id):
    """Cria ou atualiza o profile na tabela profiles do Supabase."""
    print(f"[PROFILE] Criando/atualizando profile para user_id: {user_id}")

    # Check if profile exists
    resp = requests.get(
        f"{SUPABASE_URL}/rest/v1/profiles?id=eq.{user_id}&select=*",
        headers={**headers, "Prefer": "return=representation"},
        timeout=15,
    )

    profile_data = {
        "id": user_id,
        "role": "superadmin",
        "status": "ACTIVE",
        "full_name": "Nicolas Bissoqui",
        "email": SUPERADMIN_EMAIL,
    }

    if resp.status_code == 200 and resp.json():
        print("   Profile ja existe, atualizando role para superadmin...")
        resp = requests.patch(
            f"{SUPABASE_URL}/rest/v1/profiles?id=eq.{user_id}",
            headers={**headers, "Prefer": "return=representation"},
            json={"role": "superadmin", "status": "ACTIVE"},
            timeout=15,
        )
        if resp.status_code in (200, 204):
            print("[OK] Profile atualizado para superadmin + ACTIVE!")
        else:
            print(f"[AVISO] Resposta ao atualizar: {resp.status_code} -- {resp.text}")
    else:
        resp = requests.post(
            f"{SUPABASE_URL}/rest/v1/profiles",
            headers={**headers, "Prefer": "return=representation"},
            json=profile_data,
            timeout=15,
        )
        if resp.status_code in (200, 201):
            print("[OK] Profile criado com sucesso!")
        else:
            print(f"[AVISO] Resposta ao criar profile: {resp.status_code} -- {resp.text}")


def main():
    print("=" * 60)
    print("  ChikGuard -- Criacao de Super Admin")
    print("=" * 60)
    print(f"  Email:    {SUPERADMIN_EMAIL}")
    print(f"  Senha:    {SUPERADMIN_PASSWORD}")
    print(f"  Role:     superadmin")
    print(f"  Supabase: {SUPABASE_URL}")
    print("=" * 60)

    user_id = create_auth_user()
    if not user_id:
        print("\n[ERRO] Falha ao criar/encontrar o usuario. Abortando.")
        sys.exit(1)

    create_profile(user_id)

    print("\n" + "=" * 60)
    print("  SUPER ADMIN CONFIGURADO COM SUCESSO!")
    print("=" * 60)
    print(f"  Login:  {SUPERADMIN_EMAIL}")
    print(f"  Senha:  {SUPERADMIN_PASSWORD}")
    print(f"  Role:   superadmin")
    print(f"  Status: ACTIVE (sem necessidade de aprovacao)")
    print("=" * 60)


if __name__ == "__main__":
    main()
