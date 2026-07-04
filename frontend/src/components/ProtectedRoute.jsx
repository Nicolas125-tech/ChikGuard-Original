import React from 'react';
import { ShieldAlert, LogOut } from 'lucide-react';
import { authService } from '../utils/authService';

/**
 * Componente de Rota Protegida com controle de acesso RBAC e status de aprovação.
 * 
 * @param {object} props
 * @param {string} props.token Token de autenticação atual.
 * @param {string} props.userRole Papel atual do usuário (viewer, operator, manager, admin).
 * @param {string} props.status Status de aprovação da conta (PENDING, ACTIVE, SUSPENDED).
 * @param {string[]} props.allowedRoles Lista de papéis permitidos para acessar a tela.
 * @param {React.ReactNode} props.children Conteúdo a ser renderizado se autorizado.
 * @param {Function} props.onLogout Callback executado caso o usuário precise deslogar.
 */
export default function ProtectedRoute({
  token,
  userRole,
  status,
  allowedRoles = [],
  children,
  onLogout
}) {
  // 1. Não autenticado
  if (!token) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
        <div className="bg-slate-900 border border-slate-800 p-8 rounded-2xl max-w-md w-full text-center shadow-xl">
          <ShieldAlert className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <h1 className="text-xl font-bold text-white mb-2">Acesso Restrito</h1>
          <p className="text-slate-400 mb-6 text-sm">
            Você precisa estar autenticado para acessar esta área da plataforma ChikGuard.
          </p>
          <button
            onClick={() => window.location.reload()}
            className="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-3 rounded-xl transition-colors"
          >
            Fazer Login
          </button>
        </div>
      </div>
    );
  }

  // 2. Conta Suspensa
  if (status === 'SUSPENDED') {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
        <div className="bg-slate-900 border border-red-500/20 p-8 rounded-2xl max-w-md w-full text-center shadow-xl">
          <ShieldAlert className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <h1 className="text-xl font-bold text-red-400 mb-2">Conta Suspensa</h1>
          <p className="text-slate-400 mb-6 text-sm">
            Sua conta do ChikGuard foi suspensa. Entre em contato com o suporte ou o administrador da granja.
          </p>
          <button
            onClick={onLogout}
            className="w-full flex items-center justify-center gap-2 bg-slate-800 hover:bg-slate-700 text-white font-bold py-3 rounded-xl transition-colors"
          >
            <LogOut size={16} /> Sair do Sistema
          </button>
        </div>
      </div>
    );
  }

  // 3. Conta Pendente de Aprovação
  if (status === 'PENDING') {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
        <div className="bg-slate-900 border border-amber-500/20 p-8 rounded-2xl max-w-md w-full text-center shadow-xl">
          <div className="bg-amber-500/10 rounded-full p-4 w-16 h-16 flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h1 className="text-xl font-bold text-amber-400 mb-3">Aguardando Aprovação</h1>
          <p className="text-slate-300 mb-6 text-sm leading-relaxed">
            A sua conta foi criada com sucesso, mas precisa de ser aprovada por um administrador antes de aceder ao sistema.
            Você receberá uma notificação quando for aprovado.
          </p>
          <button
            onClick={onLogout}
            className="w-full flex items-center justify-center gap-2 bg-slate-800 hover:bg-slate-700 text-white font-bold py-3 rounded-xl transition-colors"
          >
            <LogOut size={16} /> Sair e Voltar ao Login
          </button>
        </div>
      </div>
    );
  }

  // 4. Sem Permissão (RBAC insuficiente)
  const isAuthorized = allowedRoles.length === 0 || authService.hasAccess(userRole, allowedRoles);
  if (!isAuthorized) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
        <div className="bg-slate-900 border border-red-500/20 p-8 rounded-2xl max-w-md w-full text-center shadow-xl">
          <ShieldAlert className="w-16 h-16 text-red-400 mx-auto mb-4" />
          <h1 className="text-xl font-bold text-white mb-2">Acesso Negado</h1>
          <p className="text-slate-400 mb-6 text-sm">
            Seu nível de acesso atual ({userRole}) não tem permissão para visualizar esta tela.
            Esta área é restrita a: {allowedRoles.join(', ')}.
          </p>
          <div className="flex flex-col gap-3">
            <button
              onClick={() => window.location.reload()}
              className="w-full bg-slate-800 hover:bg-slate-700 text-white font-semibold py-3 rounded-xl transition-colors"
            >
              Recarregar Painel
            </button>
            <button
              onClick={onLogout}
              className="w-full text-sm text-slate-500 hover:text-slate-300 transition-colors py-2"
            >
              Sair da Conta
            </button>
          </div>
        </div>
      </div>
    );
  }

  // 5. Autorizado
  return children;
}
