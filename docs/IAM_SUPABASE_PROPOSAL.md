# Proposta de Arquitetura IAM (Identity and Access Management) - ChikGuard

Este documento detalha o design e a implementação do módulo de IAM para o ChikGuard utilizando Supabase, focado num modelo de *Onboarding com Aprovação Manual* (Closed Beta).

A segurança principal é garantida na base de dados (PostgreSQL) através de Row Level Security (RLS) e Remote Procedure Calls (RPCs), garantindo que clientes (Frontend/Mobile) não podem escalar privilégios.

## 1. Modelagem da Base de Dados (Schema `public` vs `auth`)

### Criação de ENUMs e Tabela de Perfis

```sql
-- 1.1 Criar os tipos ENUM para status e role
CREATE TYPE public.user_status AS ENUM ('PENDING', 'ACTIVE', 'REJECTED', 'SUSPENDED');
CREATE TYPE public.user_role AS ENUM ('SUPERADMIN', 'FARM_ADMIN', 'OPERATOR', 'VIEWER');

-- 1.2 Criar a tabela public.profiles referenciando auth.users
CREATE TABLE public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    status public.user_status NOT NULL DEFAULT 'PENDING',
    role public.user_role NOT NULL DEFAULT 'VIEWER',
    approved_at TIMESTAMP WITH TIME ZONE,
    approved_by UUID REFERENCES public.profiles(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Ativar RLS na tabela profiles
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
```

### Trigger de Criação Automática

```sql
-- 1.3 Função para criar perfil automaticamente após registo no Auth
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.profiles (id, status, role)
  VALUES (new.id, 'PENDING', 'VIEWER');
  RETURN new;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 1.4 Trigger associado à tabela auth.users
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();
```

## 2. Segurança na Base de Dados (Row Level Security - RLS)

### Políticas para `public.profiles`

```sql
-- 2.1 Acesso de leitura ao próprio perfil
CREATE POLICY "Utilizador pode ler o próprio perfil"
ON public.profiles
FOR SELECT
TO authenticated
USING (auth.uid() = id);

-- (Opcional) Superadmin pode ler todos os perfis
CREATE POLICY "Superadmin pode ler todos os perfis"
ON public.profiles
FOR SELECT
TO authenticated
USING (
  (SELECT role FROM public.profiles WHERE id = auth.uid()) = 'SUPERADMIN'
);

-- Nota: Não criar políticas de UPDATE ou DELETE para utilizadores comuns,
-- garantindo que não podem alterar o próprio status ou role.
```

### Exemplo de Bloqueio Global em Tabelas de Domínio (`cameras`)

```sql
-- Exemplo de RLS para a tabela 'cameras' com verificação de status 'ACTIVE'
-- Presume-se que a tabela 'cameras' tenha um campo 'owner_id' (UUID)

ALTER TABLE public.cameras ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Acesso apenas para utilizadores ACTIVE nas suas câmaras"
ON public.cameras
FOR SELECT
TO authenticated
USING (
  auth.uid() = owner_id AND
  (SELECT status FROM public.profiles WHERE id = auth.uid()) = 'ACTIVE'
);
```

## 3. Painel de Controlo do SuperAdmin (Supabase RPCs)

### Funções Seguras em Postgres

```sql
-- 3.1 Retorna utilizadores PENDING (apenas para SUPERADMIN)
CREATE OR REPLACE FUNCTION public.get_pending_users()
RETURNS SETOF public.profiles
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  -- Verificar se o utilizador que chama é SUPERADMIN
  IF (SELECT role FROM public.profiles WHERE id = auth.uid()) != 'SUPERADMIN' THEN
    RAISE EXCEPTION 'Acesso negado: Apenas SUPERADMIN pode ver utilizadores pendentes.';
  END IF;

  RETURN QUERY SELECT * FROM public.profiles WHERE status = 'PENDING';
END;
$$;

-- 3.2 Aprova utilizador e define role (apenas para SUPERADMIN)
CREATE OR REPLACE FUNCTION public.approve_user(
  target_user_id UUID,
  target_role text
)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  caller_role public.user_role;
BEGIN
  -- 1. Verificar privilégios de quem executa a função
  SELECT role INTO caller_role FROM public.profiles WHERE id = auth.uid();

  IF caller_role != 'SUPERADMIN' THEN
    RAISE EXCEPTION 'Acesso negado: Apenas SUPERADMIN pode aprovar utilizadores.';
  END IF;

  -- 2. Atualizar o perfil alvo
  UPDATE public.profiles
  SET
    status = 'ACTIVE',
    role = target_role::public.user_role,
    approved_at = NOW(),
    approved_by = auth.uid()
  WHERE id = target_user_id;

  -- Verificar se o utilizador existia
  IF NOT FOUND THEN
    RAISE EXCEPTION 'Utilizador com ID % não encontrado.', target_user_id;
  END IF;
END;
$$;
```

## 4. Integração Frontend, Backend e Mobile

### Proteção de Rotas (React / React Native)

No frontend, usamos o evento `onAuthStateChange` para detetar o login e, em seguida, consultamos o perfil do utilizador.

```typescript
// Exemplo genérico React/React Native (AuthGuard.tsx ou similar)
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom'; // ou 'expo-router' no mobile
import { supabase } from './supabaseClient';

export function useRequireAuth() {
  const [session, setSession] = useState(null);
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      if (session) fetchProfile(session.user.id);
      else setLoading(false);
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
      if (session) fetchProfile(session.user.id);
      else {
        setProfile(null);
        setLoading(false);
        navigate('/login');
      }
    });

    return () => subscription.unsubscribe();
  }, []);

  const fetchProfile = async (userId) => {
    const { data, error } = await supabase
      .from('profiles')
      .select('status, role')
      .eq('id', userId)
      .single();

    if (!error && data) {
      setProfile(data);
      if (data.status === 'PENDING') {
        navigate('/aguardando-aprovacao');
      } else if (data.status !== 'ACTIVE') {
        // Lidar com REJECTED ou SUSPENDED
        navigate('/conta-inativa');
      }
    }
    setLoading(false);
  };

  return { session, profile, loading };
}
```

### Backend (Python) - Exemplo de Consumo da RPC

No backend, podemos ter rotas que o painel de admin chama, e o backend interage com o Supabase usando o cliente oficial de Python usando as credenciais do Admin (Service Role ou token do utilizador).

```python
# Exemplo no backend (src/api/admin_api.py ou similar)
from flask import Blueprint, jsonify, request
from supabase import create_client, Client
import os

admin_api = Blueprint('admin', __name__)

SUPABASE_URL = os.environ.get("SUPABASE_URL")
# Usando a chave de serviço (Service Role Key) para bypass RLS, se o backend agir como sistema.
# Alternativamente, usar o access_token do utilizador que fez a request (melhor prática para manter RLS).
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

@admin_api.route('/api/admin/approve-user', methods=['POST'])
def approve_user_endpoint():
    # Na prática, verificar se o utilizador logado tem permissões no próprio backend ou
    # passar o token JWT do header Authorization para o cliente do Supabase.

    # Exemplo passando o token do cliente para manter a identidade na RPC:
    auth_header = request.headers.get('Authorization')
    if auth_header:
        # Extrair token (Bearer xyz...)
        token = auth_header.split(" ")[1]
        supabase.postgrest.auth(token)

    data = request.json
    target_user_id = data.get('target_user_id')
    target_role = data.get('target_role', 'VIEWER')

    try:
        # Chamar a RPC approve_user que criámos na base de dados
        response = supabase.rpc(
            'approve_user',
            {'target_user_id': target_user_id, 'target_role': target_role}
        ).execute()

        return jsonify({"message": "User approved successfully", "data": response.data}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400
```

### Opcional: Custom JWT Claims (Postgres Hooks)

Em vez de fazer `SELECT * FROM profiles` a cada request ou em cada RLS policy, o Supabase suporta injetar dados no próprio token JWT através de **Custom Access Token Hooks** (atualmente em Beta).

**Vantagem**: RLS mais rápido e menos pedidos na base de dados pelo frontend.

1. **Ativar o Hook:** No painel do Supabase, em `Authentication > Hooks`, configuramos uma função PL/pgSQL que corre *antes* do token ser emitido.
2. **Exemplo do Hook:**

```sql
CREATE OR REPLACE FUNCTION public.custom_access_token_hook(event jsonb)
RETURNS jsonb
LANGUAGE plpgsql
STABLE
AS $$
  DECLARE
    claims jsonb;
    user_status public.user_status;
    user_role public.user_role;
  BEGIN
    -- Obter os dados atuais de status e role
    SELECT status, role INTO user_status, user_role
    FROM public.profiles
    WHERE id = (event->>'user_id')::uuid;

    claims := event->'claims';

    IF user_status IS NOT NULL THEN
      -- Injetar no JWT
      claims := jsonb_set(claims, '{user_status}', to_jsonb(user_status));
      claims := jsonb_set(claims, '{user_role}', to_jsonb(user_role));
    END IF;

    -- Atualizar e retornar o evento modificado
    event := jsonb_set(event, '{claims}', claims);
    RETURN event;
  END;
$$;
```

3. **Uso no RLS (Exemplo atualizado):**
Em vez de `(SELECT status FROM profiles WHERE id = auth.uid()) = 'ACTIVE'`, podemos usar apenas:
`(auth.jwt() ->> 'user_status') = 'ACTIVE'`
