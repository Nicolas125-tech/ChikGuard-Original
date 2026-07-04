import { supabase, isSupabaseConfigured } from './supabaseClient';

/**
 * Serviço de Autenticação ChikGuard para integração com o Supabase.
 * Encapsula o fluxo de login, logout, registro e checagem de privilégios RBAC.
 */
export const authService = {
  /**
   * Realiza login com e-mail e senha no Supabase
   * @param {string} email
   * @param {string} password
   * @returns {Promise<{session: any, profile: any}>}
   */
  async login(email, password) {
    if (!isSupabaseConfigured) {
      throw new Error('Supabase não configurado neste ambiente.');
    }

    const { data, error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });

    if (error) throw error;

    if (!data.session) {
      throw new Error('Não foi possível estabelecer uma sessão de login.');
    }

    // Busca o perfil do usuário na tabela profiles para obter a role e o status reais
    const profile = await this.getUserProfile(data.session.user.id);

    return {
      session: data.session,
      profile,
    };
  },

  /**
   * Encerra a sessão do usuário
   */
  async logout() {
    if (isSupabaseConfigured) {
      const { error } = await supabase.auth.signOut();
      if (error) console.error('Erro durante o logout do Supabase:', error);
    }
  },

  /**
   * Solicita cadastro na plataforma ChikGuard
   * @param {string} email 
   * @param {string} password 
   * @param {object} userData Dados adicionais (nome, telefone, cpf, etc.)
   */
  async signUp(email, password, userData = {}) {
    if (!isSupabaseConfigured) {
      throw new Error('Supabase não configurado neste ambiente.');
    }

    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        data: {
          full_name: userData.fullName,
          phone: userData.phone,
          cpf: userData.cpf,
          location: userData.location,
          age: userData.age ? parseInt(userData.age, 10) : null,
          tenant_id: userData.tenantId || 1, // Associa ao tenant padrão inicialmente
        },
      },
    });

    if (error) throw error;
    return data;
  },

  /**
   * Retorna os dados do perfil associado ao UUID do usuário
   * @param {string} userId UUID do usuário
   */
  async getUserProfile(userId) {
    if (!isSupabaseConfigured) return null;

    try {
      const { data, error } = await supabase
        .from('profiles')
        .select('role, status, tenant_id, full_name, email')
        .eq('id', userId)
        .single();

      if (error) {
        console.warn('Erro ao carregar perfil, usando papel padrão viewer:', error.message);
        return { role: 'viewer', status: 'PENDING', tenant_id: 1 };
      }
      return data;
    } catch (err) {
      console.error('Erro na requisição de profiles:', err);
      return { role: 'viewer', status: 'PENDING', tenant_id: 1 };
    }
  },

  /**
   * Recupera a sessão atual ativa
   */
  async getSession() {
    if (!isSupabaseConfigured) return { session: null };
    const { data, error } = await supabase.auth.getSession();
    if (error) {
      console.error('Erro ao ler a sessão:', error);
      return { session: null };
    }
    return data;
  },

  /**
   * Verifica se o usuário logado possui uma das roles autorizadas
   * @param {string} userRole Role atual do usuário
   * @param {string[]} allowedRoles Lista de papéis autorizados
   */
  hasAccess(userRole, allowedRoles = []) {
    if (!userRole) return false;
    const role = userRole.toLowerCase();
    
    // Admins e Superadmins têm acesso total a qualquer tela
    if (role === 'admin' || role === 'superadmin') return true;
    
    return allowedRoles.map(r => r.toLowerCase()).includes(role);
  }
};
