-- ============================================================
-- ChikGuard — Security Patch: RBAC & RLS Privilege Escalation Fix
-- Migração de Correção Imediata de Vulnerabilidades Críticas
-- ============================================================

-- ─── 1. Corrigir Trigger handle_new_user ─────────────────────────────────────
-- Remove a vulnerabilidade que promovia qualquer e-mail com 'admin'
-- Novos usuários entram como 'viewer' e 'PENDING' (exceto o 1º usuário bootstrap)
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  active_count INTEGER;
  new_role TEXT;
  new_status TEXT;
BEGIN
  -- Conta quantos perfis ativos já existem no sistema
  SELECT COUNT(*) INTO active_count FROM public.profiles WHERE status = 'ACTIVE';

  -- Apenas o primeiro usuário da história do sistema é elevado a admin inicial (bootstrap).
  -- Todos os demais usuários cadastrados entram estritamente como 'viewer' e 'PENDING',
  -- aguardando aprovação explícita de um Administrador.
  IF active_count = 0 THEN
    new_role := 'admin';
    new_status := 'ACTIVE';
  ELSE
    new_role := 'viewer';
    new_status := 'PENDING';
  END IF;

  INSERT INTO public.profiles (id, email, role, status, tenant_id, full_name, phone, cpf, location, age)
  VALUES (
    NEW.id,
    COALESCE(NEW.email, ''),
    new_role,
    new_status,
    COALESCE((NEW.raw_user_meta_data->>'tenant_id')::BIGINT, 1),
    NEW.raw_user_meta_data->>'full_name',
    NEW.raw_user_meta_data->>'phone',
    NEW.raw_user_meta_data->>'cpf',
    NEW.raw_user_meta_data->>'location',
    NULLIF(NEW.raw_user_meta_data->>'age', '')::INTEGER
  )
  ON CONFLICT (id) DO NOTHING;
      
  RETURN NEW;
END;
$$;

-- ─── 2. Corrigir Política RLS profiles_update_own ────────────────────────────
-- Impede que usuários autenticados alterem role, status ou tenant_id do seu perfil
DROP POLICY IF EXISTS profiles_update_own ON public.profiles;

CREATE POLICY profiles_update_own ON public.profiles
  FOR UPDATE TO authenticated
  USING (auth.uid() = id)
  WITH CHECK (
    auth.uid() = id
    -- Garante que role, status e tenant_id não possam ser alterados pelo próprio usuário comum
    AND role = (SELECT p.role FROM public.profiles p WHERE p.id = auth.uid())
    AND status = (SELECT p.status FROM public.profiles p WHERE p.id = auth.uid())
    AND tenant_id = (SELECT p.tenant_id FROM public.profiles p WHERE p.id = auth.uid())
  );
