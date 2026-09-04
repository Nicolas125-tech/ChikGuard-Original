-- ============================================================
-- ChikGuard — RBAC e RLS Zero-Trust Schema para Supabase
-- Script de Migração Remota
-- ============================================================

-- ─── 1. Semeando Tenant Padrão se não existir ─────────────────────────────────
INSERT INTO public.tenant (id, name, active)
VALUES (1, 'Granja Padrão', true)
ON CONFLICT (id) DO NOTHING;

-- ─── 2. Modificando Tabela profiles ───────────────────────────────────────────
-- Garante a coluna tenant_id na tabela profiles apontando para tenant
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS tenant_id BIGINT REFERENCES public.tenant(id) DEFAULT 1;

-- Atualiza a check constraint de role na tabela profiles
ALTER TABLE public.profiles DROP CONSTRAINT IF EXISTS profiles_role_check;
ALTER TABLE public.profiles ADD CONSTRAINT profiles_role_check CHECK (role IN ('viewer', 'operator', 'manager', 'admin', 'superadmin'));

-- ─── 3. Funções Auxiliares (Helper Functions) para Políticas RLS ──────────────
-- Usar SECURITY DEFINER e setar search_path para evitar recursão infinita e injeção.
CREATE OR REPLACE FUNCTION public.get_user_tenant_id()
RETURNS BIGINT
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  RETURN (
    SELECT tenant_id 
    FROM public.profiles 
    WHERE id = auth.uid()
  );
END;
$$;

CREATE OR REPLACE FUNCTION public.get_user_role()
RETURNS TEXT
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  RETURN (
    SELECT role 
    FROM public.profiles 
    WHERE id = auth.uid()
  );
END;
$$;

-- ─── 4. Atualizando o Trigger de handle_new_user ──────────────────────────────
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
  -- Conta quantos perfis ativos já existem
  SELECT COUNT(*) INTO active_count FROM public.profiles WHERE status = 'ACTIVE';

  -- Apenas o primeiro usuário do sistema é ativado como admin inicial (bootstrap).
  -- Todos os demais usuários entram estritamente como 'viewer' e 'PENDING',
  -- exigindo aprovação explícita de um Administrador.
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
  ON CONFLICT (id) DO UPDATE
  SET role = EXCLUDED.role,
      status = EXCLUDED.status;
      
  RETURN NEW;
END;
$$;

-- Recria a trigger
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW
  EXECUTE FUNCTION public.handle_new_user();

-- ─── 5. Habilitando RLS em todas as tabelas ───────────────────────────────────
ALTER TABLE public.tenant ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.account ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.role_permission ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.reading ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.bird_snapshot ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.bird_identity ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.bird_track_point ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.event_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sensor_reading ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.batch ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.weight_estimate ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.acoustic_reading ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.thermal_anomaly ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.energy_usage_daily ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sync_queue_item ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.batch_logbook ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.push_token ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.camera ENABLE ROW LEVEL SECURITY;

-- ─── 6. Removendo Políticas Permissivas Anteriores ───────────────────────────
DO $$
DECLARE
    t_name text;
    p_name text;
BEGIN
    FOR t_name IN
        SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename IN (
            'tenant', 'profiles', 'account', 'role_permission', 'reading', 'bird_snapshot', 
            'bird_identity', 'bird_track_point', 'event_log', 'sensor_reading', 'batch', 
            'weight_estimate', 'acoustic_reading', 'thermal_anomaly', 'energy_usage_daily', 
            'audit_log', 'sync_queue_item', 'batch_logbook', 'push_token', 'camera'
        )
    LOOP
        FOR p_name IN
            SELECT policyname FROM pg_policies WHERE schemaname = 'public' AND tablename = t_name AND policyname IN (
                'Permitir leitura anonima', 'Permitir insercao anonima',
                'Permitir leitura autenticada', 'Permitir insercao autenticada',
                'Permitir atualizacao autenticada', 'Permitir delecao autenticada'
            )
        LOOP
            EXECUTE format('DROP POLICY IF EXISTS %I ON public.%I', p_name, t_name);
        END LOOP;
    END LOOP;
END $$;

-- ─── 7. Criando Novas Políticas Baseadas em Tenant e RBAC ────────────────────

-- 7a. Políticas para 'tenant'
CREATE POLICY tenant_select ON public.tenant FOR SELECT TO authenticated
  USING (id = public.get_user_tenant_id() OR public.get_user_role() IN ('admin', 'superadmin'));

CREATE POLICY tenant_all_admin ON public.tenant FOR ALL TO authenticated
  USING (public.get_user_role() IN ('admin', 'superadmin'))
  WITH CHECK (public.get_user_role() IN ('admin', 'superadmin'));

-- 7b. Políticas para 'profiles'
-- ATENÇÃO: NÃO usar get_user_role() aqui! Isso causa recursão infinita (500 Internal Server Error)
-- pois a função lê a tabela profiles, que dispara a política, que chama a função, etc.
-- SOLUÇÃO: usar subquery EXISTS direta na própria tabela profiles com alias.

-- Qualquer usuário autenticado lê seu próprio perfil (sem recursão)
CREATE POLICY profiles_read_own ON public.profiles
  FOR SELECT TO authenticated
  USING (auth.uid() = id);

-- Admins e managers veem todos os profiles (subquery com alias para evitar recursão)
CREATE POLICY profiles_read_elevated ON public.profiles
  FOR SELECT TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.profiles self
      WHERE self.id = auth.uid()
        AND self.role IN ('admin', 'superadmin', 'manager')
        AND self.status = 'ACTIVE'
    )
  );

-- Trigger handle_new_user usa SECURITY DEFINER e ignora RLS.
-- Esta política permite que o próprio usuário insira (caso necessário):
CREATE POLICY profiles_insert_by_trigger ON public.profiles
  FOR INSERT TO authenticated
  WITH CHECK (auth.uid() = id);

-- Usuários atualizam apenas o próprio perfil
CREATE POLICY profiles_update_own ON public.profiles
  FOR UPDATE TO authenticated
  USING (auth.uid() = id)
  WITH CHECK (
    auth.uid() = id
    AND role = (SELECT p.role FROM public.profiles p WHERE p.id = auth.uid())
    AND status = (SELECT p.status FROM public.profiles p WHERE p.id = auth.uid())
    AND tenant_id = (SELECT p.tenant_id FROM public.profiles p WHERE p.id = auth.uid())
  );

-- Admins e superadmins atualizam qualquer perfil (aprovar/suspender usuários)
CREATE POLICY profiles_update_admin ON public.profiles
  FOR UPDATE TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.profiles self
      WHERE self.id = auth.uid()
        AND self.role IN ('admin', 'superadmin')
        AND self.status = 'ACTIVE'
    )
  );

-- 7c. Políticas para 'role_permission'
CREATE POLICY role_permission_select ON public.role_permission FOR SELECT TO authenticated
  USING (true);

CREATE POLICY role_permission_admin ON public.role_permission FOR ALL TO authenticated
  USING (public.get_user_role() IN ('admin', 'superadmin'))
  WITH CHECK (public.get_user_role() IN ('admin', 'superadmin'));

-- 7d. Políticas para 'account'
CREATE POLICY account_select ON public.account FOR SELECT TO authenticated
  USING (
    tenant_id = public.get_user_tenant_id()
    OR public.get_user_role() IN ('admin', 'superadmin')
  );

CREATE POLICY account_modify ON public.account FOR ALL TO authenticated
  USING (
    (tenant_id = public.get_user_tenant_id() AND public.get_user_role() = 'manager')
    OR public.get_user_role() IN ('admin', 'superadmin')
  )
  WITH CHECK (
    (tenant_id = public.get_user_tenant_id() AND public.get_user_role() = 'manager')
    OR public.get_user_role() IN ('admin', 'superadmin')
  );

-- 7e. Políticas para 'audit_log' (apenas manager do próprio tenant e admin geral consultam)
CREATE POLICY audit_log_select ON public.audit_log FOR SELECT TO authenticated
  USING (
    (tenant_id = public.get_user_tenant_id() AND public.get_user_role() = 'manager')
    OR public.get_user_role() IN ('admin', 'superadmin')
  );

CREATE POLICY audit_log_insert ON public.audit_log FOR INSERT TO authenticated
  WITH CHECK (
    (tenant_id = public.get_user_tenant_id() AND public.get_user_role() IN ('operator', 'manager'))
    OR public.get_user_role() IN ('admin', 'superadmin')
  );

-- 7f. Loop para criar políticas CRUD para todas as tabelas transacionais/telemetria
DO $$
DECLARE
    t_name text;
BEGIN
    FOR t_name IN
        SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename IN (
            'reading', 'bird_snapshot', 'bird_identity', 'bird_track_point', 
            'event_log', 'sensor_reading', 'batch', 'weight_estimate', 'acoustic_reading', 
            'thermal_anomaly', 'energy_usage_daily', 'sync_queue_item', 
            'batch_logbook', 'push_token', 'camera'
        )
    LOOP
        -- SELECT: Qualquer papel ativo no tenant visualiza os dados
        EXECUTE format('
            CREATE POLICY %I_select ON public.%I FOR SELECT TO authenticated
            USING (
                tenant_id = public.get_user_tenant_id()
                OR public.get_user_role() IN (''admin'', ''superadmin'')
            )
        ', t_name, t_name);

        -- INSERT: Apenas Operators, Managers e Admins inserem dados de telemetria/lotes
        EXECUTE format('
            CREATE POLICY %I_insert ON public.%I FOR INSERT TO authenticated
            WITH CHECK (
                (tenant_id = public.get_user_tenant_id() AND public.get_user_role() IN (''operator'', ''manager''))
                OR public.get_user_role() IN (''admin'', ''superadmin'')
            )
        ', t_name, t_name);

        -- UPDATE: Apenas Operators, Managers e Admins atualizam dados de telemetria/lotes
        EXECUTE format('
            CREATE POLICY %I_update ON public.%I FOR UPDATE TO authenticated
            USING (
                (tenant_id = public.get_user_tenant_id() AND public.get_user_role() IN (''operator'', ''manager''))
                OR public.get_user_role() IN (''admin'', ''superadmin'')
            )
            WITH CHECK (
                (tenant_id = public.get_user_tenant_id() AND public.get_user_role() IN (''operator'', ''manager''))
                OR public.get_user_role() IN (''admin'', ''superadmin'')
            )
        ', t_name, t_name);

        -- DELETE: Apenas Managers e Admins removem dados
        EXECUTE format('
            CREATE POLICY %I_delete ON public.%I FOR DELETE TO authenticated
            USING (
                (tenant_id = public.get_user_tenant_id() AND public.get_user_role() = ''manager'')
                OR public.get_user_role() IN (''admin'', ''superadmin'')
            )
        ', t_name, t_name);
    END LOOP;
END $$;
