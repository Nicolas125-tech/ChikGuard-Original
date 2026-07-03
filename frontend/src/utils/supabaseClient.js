import { createClient } from '@supabase/supabase-js';

// Safe check for import.meta.env
const env = typeof import.meta !== 'undefined' && import.meta.env ? import.meta.env : {};
const supabaseUrl = env.VITE_SUPABASE_URL || '';
const supabaseAnonKey = env.VITE_SUPABASE_ANON_KEY || '';

export const isSupabaseConfigured = Boolean(supabaseUrl && supabaseAnonKey);

// Stub seguro: nunca lança TypeError, sempre retorna a estrutura esperada
// quando as variáveis de ambiente estão ausentes ou inválidas.
export const supabaseStub = {
  supabaseUrl: null,
  auth: {
    signUp: async () => ({ data: null, error: { message: 'Supabase não configurado neste ambiente.' } }),
    signInWithPassword: async () => ({ data: null, error: { message: 'Supabase não configurado neste ambiente.' } }),
    signInWithOAuth: async () => ({ data: null, error: { message: 'Supabase não configurado neste ambiente.' } }),
    signOut: async () => ({}),
    getSession: async () => ({ data: { session: null }, error: null }),
    onAuthStateChange: () => ({ data: { subscription: { unsubscribe: () => {} } } }),
  },
  from: () => ({
    select: () => ({
      eq: () => ({
        single: async () => ({ data: null, error: null }),
      }),
    }),
    update: () => ({
      eq: () => ({
        execute: async () => ({ data: null, error: null }),
      }),
    }),
  }),
};

export const supabase = isSupabaseConfigured
  ? createClient(supabaseUrl, supabaseAnonKey)
  : supabaseStub;
