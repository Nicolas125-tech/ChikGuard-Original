-- Add UNIQUE constraint to camera.camera_id to allow foreign keys to reference it
ALTER TABLE public.camera ADD CONSTRAINT uq_camera_id UNIQUE (camera_id);

-- Drop old insecure policies
DO $$
DECLARE
    t_name text;
    p_name text;
BEGIN
    FOR t_name IN
        SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename IN ('tenant', 'account', 'role_permission', 'reading', 'bird_snapshot', 'bird_identity', 'bird_track_point', 'event_log', 'sensor_reading', 'batch', 'weight_estimate', 'acoustic_reading', 'thermal_anomaly', 'energy_usage_daily', 'audit_log', 'sync_queue_item', 'batch_logbook', 'push_token', 'camera')
    LOOP
        FOR p_name IN
            SELECT policyname FROM pg_policies WHERE schemaname = 'public' AND tablename = t_name AND policyname IN ('Permitir leitura anonima', 'Permitir insercao anonima')
        LOOP
            EXECUTE format('DROP POLICY IF EXISTS %I ON public.%I', p_name, t_name);
        END LOOP;
    END LOOP;
END $$;

-- Add basic authenticated RLS policies
DO $$
DECLARE
    t_name text;
BEGIN
    FOR t_name IN
        SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename IN ('tenant', 'account', 'role_permission', 'reading', 'bird_snapshot', 'bird_identity', 'bird_track_point', 'event_log', 'sensor_reading', 'batch', 'weight_estimate', 'acoustic_reading', 'thermal_anomaly', 'energy_usage_daily', 'audit_log', 'sync_queue_item', 'batch_logbook', 'push_token', 'camera')
    LOOP
        EXECUTE format('CREATE POLICY "Permitir leitura autenticada" ON public.%I FOR SELECT TO authenticated USING (true)', t_name);
        EXECUTE format('CREATE POLICY "Permitir insercao autenticada" ON public.%I FOR INSERT TO authenticated WITH CHECK (true)', t_name);
        EXECUTE format('CREATE POLICY "Permitir atualizacao autenticada" ON public.%I FOR UPDATE TO authenticated USING (true)', t_name);
        EXECUTE format('CREATE POLICY "Permitir delecao autenticada" ON public.%I FOR DELETE TO authenticated USING (true)', t_name);
    END LOOP;
END $$;

-- Add Foreign Keys for tenant_id
ALTER TABLE public.account ADD CONSTRAINT fk_account_tenant FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE CASCADE;
ALTER TABLE public.reading ADD CONSTRAINT fk_reading_tenant FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE CASCADE;
ALTER TABLE public.bird_snapshot ADD CONSTRAINT fk_snapshot_tenant FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE CASCADE;
ALTER TABLE public.bird_identity ADD CONSTRAINT fk_identity_tenant FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE CASCADE;
ALTER TABLE public.bird_track_point ADD CONSTRAINT fk_track_tenant FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE CASCADE;
ALTER TABLE public.event_log ADD CONSTRAINT fk_event_tenant FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE CASCADE;
ALTER TABLE public.sensor_reading ADD CONSTRAINT fk_sensor_tenant FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE CASCADE;
ALTER TABLE public.batch ADD CONSTRAINT fk_batch_tenant FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE CASCADE;
ALTER TABLE public.weight_estimate ADD CONSTRAINT fk_weight_tenant FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE CASCADE;
ALTER TABLE public.acoustic_reading ADD CONSTRAINT fk_acoustic_tenant FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE CASCADE;
ALTER TABLE public.thermal_anomaly ADD CONSTRAINT fk_thermal_tenant FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE CASCADE;
ALTER TABLE public.energy_usage_daily ADD CONSTRAINT fk_energy_tenant FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE CASCADE;
ALTER TABLE public.audit_log ADD CONSTRAINT fk_audit_tenant FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE CASCADE;
ALTER TABLE public.sync_queue_item ADD CONSTRAINT fk_sync_tenant FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE CASCADE;
ALTER TABLE public.batch_logbook ADD CONSTRAINT fk_logbook_tenant FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE CASCADE;
ALTER TABLE public.push_token ADD CONSTRAINT fk_push_tenant FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE CASCADE;
ALTER TABLE public.camera ADD CONSTRAINT fk_camera_tenant FOREIGN KEY (tenant_id) REFERENCES public.tenant(id) ON DELETE CASCADE;

-- Add Foreign Keys for camera_id
ALTER TABLE public.event_log ADD CONSTRAINT fk_event_camera FOREIGN KEY (camera_id) REFERENCES public.camera(camera_id) ON DELETE CASCADE;
ALTER TABLE public.sensor_reading ADD CONSTRAINT fk_sensor_camera FOREIGN KEY (camera_id) REFERENCES public.camera(camera_id) ON DELETE CASCADE;
ALTER TABLE public.batch ADD CONSTRAINT fk_batch_camera FOREIGN KEY (camera_id) REFERENCES public.camera(camera_id) ON DELETE CASCADE;
ALTER TABLE public.weight_estimate ADD CONSTRAINT fk_weight_camera FOREIGN KEY (camera_id) REFERENCES public.camera(camera_id) ON DELETE CASCADE;
ALTER TABLE public.acoustic_reading ADD CONSTRAINT fk_acoustic_camera FOREIGN KEY (camera_id) REFERENCES public.camera(camera_id) ON DELETE CASCADE;
ALTER TABLE public.thermal_anomaly ADD CONSTRAINT fk_thermal_camera FOREIGN KEY (camera_id) REFERENCES public.camera(camera_id) ON DELETE CASCADE;
ALTER TABLE public.energy_usage_daily ADD CONSTRAINT fk_energy_camera FOREIGN KEY (camera_id) REFERENCES public.camera(camera_id) ON DELETE CASCADE;
ALTER TABLE public.batch_logbook ADD CONSTRAINT fk_logbook_camera FOREIGN KEY (camera_id) REFERENCES public.camera(camera_id) ON DELETE CASCADE;