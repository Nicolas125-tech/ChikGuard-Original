-- ============================================================
-- ChikGuard — RBAC Schema para Supabase
-- Execute este script no SQL Editor do seu projeto Supabase:
-- https://supabase.com/dashboard/project/<SEU_REF>/sql/new
-- ============================================================

-- ─── 1. Tabela profiles ──────────────────────────────────────────────────────
-- Estende auth.users com metadados de role e status de aprovação.
-- É criada automaticamente via trigger quando um novo utilizador se regista.
CREATE TABLE IF NOT EXISTS public.profiles (
  id          UUID        PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email       TEXT        NOT NULL,
  role        TEXT        NOT NULL DEFAULT 'viewer'
              CHECK (role IN ('viewer', 'operator', 'admin', 'superadmin')),
  status      TEXT        NOT NULL DEFAULT 'PENDING'
              CHECK (status IN ('PENDING', 'ACTIVE', 'SUSPENDED')),
  full_name   TEXT,
  approved_at TIMESTAMPTZ,
  approved_by UUID        REFERENCES auth.users(id) ON DELETE SET NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Índice para buscas por status (frequentes no painel admin)
CREATE INDEX IF NOT EXISTS idx_profiles_status ON public.profiles(status);
CREATE INDEX IF NOT EXISTS idx_profiles_role   ON public.profiles(role);

-- ─── 2. Trigger: criar profile automaticamente no register ───────────────────
-- Quando um novo utilizador se regista (via email/password ou OAuth),
-- um profile PENDING é criado automaticamente.
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER              -- Roda com permissão de dono da função
SET search_path = public      -- Evita search_path injection
AS $$
BEGIN
  INSERT INTO public.profiles (id, email, role, status)
  VALUES (
    NEW.id,
    COALESCE(NEW.email, ''),
    COALESCE(NEW.raw_user_meta_data->>'role', 'viewer'),
    'PENDING'
  )
  ON CONFLICT (id) DO NOTHING; -- Idempotente: não falha se já existe
  RETURN NEW;
END;
$$;

-- Remover trigger anterior (caso exista) e recriar
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW
  EXECUTE FUNCTION public.handle_new_user();

-- ─── 3. Trigger: atualizar updated_at automaticamente ───────────────────────
CREATE OR REPLACE FUNCTION public.handle_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS set_profiles_updated_at ON public.profiles;
CREATE TRIGGER set_profiles_updated_at
  BEFORE UPDATE ON public.profiles
  FOR EACH ROW
  EXECUTE FUNCTION public.handle_updated_at();

-- ─── 4. Row Level Security (RLS) ─────────────────────────────────────────────
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

-- Remover políticas antigas (para garantir idempotência do script)
DROP POLICY IF EXISTS "users_read_own_profile"       ON public.profiles;
DROP POLICY IF EXISTS "admins_read_all_profiles"     ON public.profiles;
DROP POLICY IF EXISTS "admins_update_all_profiles"   ON public.profiles;
DROP POLICY IF EXISTS "admins_delete_profiles"       ON public.profiles;

-- 4a. Qualquer utilizador autenticado pode LER o próprio perfil
CREATE POLICY "users_read_own_profile"
ON public.profiles
FOR SELECT
TO authenticated
USING (auth.uid() = id);

-- 4b. Admin/Superadmin podem LER todos os perfis
CREATE POLICY "admins_read_all_profiles"
ON public.profiles
FOR SELECT
TO authenticated
USING (
  EXISTS (
    SELECT 1 FROM public.profiles AS p
    WHERE p.id = auth.uid()
      AND p.role IN ('admin', 'superadmin')
      AND p.status = 'ACTIVE'
  )
);

-- 4c. Admin/Superadmin podem ATUALIZAR qualquer perfil (aprovação, mudança de role)
CREATE POLICY "admins_update_all_profiles"
ON public.profiles
FOR UPDATE
TO authenticated
USING (
  EXISTS (
    SELECT 1 FROM public.profiles AS p
    WHERE p.id = auth.uid()
      AND p.role IN ('admin', 'superadmin')
      AND p.status = 'ACTIVE'
  )
);

-- Nota: DELETE é feito via CASCADE de auth.users — não precisamos de policy explícita.

-- ─── 5. RPC helper: buscar status por e-mail (usado pelo backend Flask) ──────
-- Usado em auth.py:  supabase.rpc("get_user_status_by_email", {"user_email": ...})
CREATE OR REPLACE FUNCTION public.get_user_status_by_email(user_email TEXT)
RETURNS TEXT
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_status TEXT;
BEGIN
  SELECT status INTO v_status
  FROM public.profiles p
  JOIN auth.users u ON u.id = p.id
  WHERE u.email = user_email
  LIMIT 1;

  RETURN COALESCE(v_status, 'PENDING');
END;
$$;

-- ─── 6. (Opcional) Migrar utilizadores existentes ────────────────────────────
-- Se já tiver utilizadores em auth.users sem profile correspondente,
-- descomente e execute este bloco:
--
-- INSERT INTO public.profiles (id, email, role, status)
-- SELECT
--   u.id,
--   COALESCE(u.email, ''),
--   'viewer',
--   'ACTIVE'   -- Utilizadores existentes já são considerados ativos
-- FROM auth.users u
-- WHERE NOT EXISTS (
--   SELECT 1 FROM public.profiles p WHERE p.id = u.id
-- );
