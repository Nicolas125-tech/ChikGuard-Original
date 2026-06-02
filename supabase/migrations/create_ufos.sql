-- Script SQL para criar a tabela "ufos" no Supabase

-- Cria a tabela ufos
CREATE TABLE IF NOT EXISTS public.ufos (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  nome TEXT NOT NULL,
  local_aparicao TEXT NOT NULL,
  data_avistamento DATE NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Ativa o RLS na tabela (recomendado)
ALTER TABLE public.ufos ENABLE ROW LEVEL SECURITY;

-- Remove políticas antigas caso já existam (para tornar o script idempotente)
DROP POLICY IF EXISTS "Permitir leitura anonima" ON public.ufos;
DROP POLICY IF EXISTS "Permitir insercao anonima" ON public.ufos;

-- Cria política para permitir que qualquer um leia (SELECT)
CREATE POLICY "Permitir leitura anonima"
ON public.ufos
FOR SELECT
USING (true);

-- Cria política para permitir que qualquer um insira (INSERT)
CREATE POLICY "Permitir insercao anonima"
ON public.ufos
FOR INSERT
WITH CHECK (true);
