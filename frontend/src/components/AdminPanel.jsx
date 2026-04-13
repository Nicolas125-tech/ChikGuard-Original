import React, { useEffect, useState, useCallback } from 'react';
import { getBaseUrl } from '../utils/config';
import { supabase, isSupabaseConfigured } from '../utils/supabaseClient';
import {
  UserCheck, UserX, ShieldCheck, Clock, Users,
  RefreshCw, AlertTriangle, ShieldOff,
} from 'lucide-react';

// ─── Helpers de estilo ─────────────────────────────────────────────────────────
const ROLE_BADGE = {
  viewer:     'bg-slate-500/20 text-slate-300 border-slate-500/30',
  operator:   'bg-blue-500/20 text-blue-300 border-blue-500/30',
  admin:      'bg-amber-500/20 text-amber-300 border-amber-500/30',
  superadmin: 'bg-rose-500/20 text-rose-300 border-rose-500/30',
};

const STATUS_BADGE = {
  PENDING:   'bg-yellow-500/20 text-yellow-300 border-yellow-500/30',
  ACTIVE:    'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
  SUSPENDED: 'bg-red-500/20 text-red-300 border-red-500/30',
};

// ─── Componente principal ─────────────────────────────────────────────────────
export default function AdminPanel({ token, serverIP }) {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionLoading, setActionLoading] = useState(null); // userId em processo
  const [activeTab, setActiveTab] = useState('pending');

  // Obtém o token mais atual: prefere Supabase (OAuth), cai no token legado.
  const getAuthToken = useCallback(async () => {
    if (isSupabaseConfigured) {
      try {
        const { data: { session } } = await supabase.auth.getSession();
        if (session?.access_token) return session.access_token;
      } catch (_) { /* fallthrough */ }
    }
    return token;
  }, [token]);

  // ─── Fetch de utilizadores ──────────────────────────────────────────────────
  const fetchUsers = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const authToken = await getAuthToken();

      // Aba "Pendentes" usa endpoint específico (lista apenas PENDING via Supabase service_role)
      // Aba "Todos" usa o endpoint interno de Accounts do Flask
      const endpoint = activeTab === 'pending'
        ? `${getBaseUrl(serverIP)}/api/admin/pending-users`
        : `${getBaseUrl(serverIP)}/api/accounts/users`;

      const res = await fetch(endpoint, {
        headers: { Authorization: `Bearer ${authToken}` },
      });

      if (res.status === 401) {
        setError('Sessão expirada. Faça login novamente.');
        return;
      }
      if (res.status === 403) {
        setError('Acesso negado. Apenas administradores podem aceder a esta área.');
        return;
      }
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        setError(d.msg || d.error || `Erro ${res.status} no servidor.`);
        return;
      }

      const d = await res.json();
      setUsers(d.items || []);
    } catch {
      setError('Falha de conexão. Verifique se o servidor está online e acessível.');
    } finally {
      setLoading(false);
    }
  }, [serverIP, getAuthToken, activeTab]);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  // ─── Aprovar utilizador ─────────────────────────────────────────────────────
  const handleApprove = async (userId, targetRole) => {
    if (!window.confirm(`Confirma a aprovação como ${targetRole.toUpperCase()}?`)) return;
    setActionLoading(userId);
    try {
      const authToken = await getAuthToken();
      const res = await fetch(`${getBaseUrl(serverIP)}/api/admin/approve-user`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${authToken}`,
        },
        body: JSON.stringify({ target_user_id: userId, target_role: targetRole }),
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        alert(`Erro ao aprovar: ${d.msg || d.error || 'Falha desconhecida.'}`);
        return;
      }
      // Remove da lista de pendentes localmente (sem re-fetch)
      setUsers((prev) => prev.filter((u) => u.id !== userId));
    } catch {
      alert('Erro de rede ao aprovar utilizador. Tente novamente.');
    } finally {
      setActionLoading(null);
    }
  };

  // ─── Suspender utilizador ────────────────────────────────────────────────────
  const handleSuspend = async (userId) => {
    if (!window.confirm('Suspender esta conta? O utilizador perderá o acesso imediatamente.')) return;
    setActionLoading(userId);
    try {
      const authToken = await getAuthToken();
      const res = await fetch(`${getBaseUrl(serverIP)}/api/accounts/users/${userId}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${authToken}`,
        },
        body: JSON.stringify({ active: false }),
      });
      if (res.ok) {
        setUsers((prev) =>
          prev.map((u) => u.id === userId ? { ...u, status: 'SUSPENDED', active: false } : u)
        );
      } else {
        const d = await res.json().catch(() => ({}));
        alert(`Erro ao suspender: ${d.msg || 'Falha desconhecida.'}`);
      }
    } catch {
      alert('Erro de rede ao suspender conta.');
    } finally {
      setActionLoading(null);
    }
  };

  // ─── Reativar utilizador ─────────────────────────────────────────────────────
  const handleReactivate = async (userId) => {
    if (!window.confirm('Reativar esta conta?')) return;
    setActionLoading(userId);
    try {
      const authToken = await getAuthToken();
      const res = await fetch(`${getBaseUrl(serverIP)}/api/accounts/users/${userId}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${authToken}`,
        },
        body: JSON.stringify({ active: true }),
      });
      if (res.ok) {
        setUsers((prev) =>
          prev.map((u) => u.id === userId ? { ...u, status: 'ACTIVE', active: true } : u)
        );
      } else {
        const d = await res.json().catch(() => ({}));
        alert(`Erro ao reativar: ${d.msg || 'Falha desconhecida.'}`);
      }
    } catch {
      alert('Erro de rede ao reativar conta.');
    } finally {
      setActionLoading(null);
    }
  };

  // ─── Render ──────────────────────────────────────────────────────────────────
  return (
    <div className="space-y-6 pb-8">
      {/* ── Header ── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-extrabold text-white tracking-tight flex items-center gap-3">
            <span className="bg-amber-500/15 p-2.5 rounded-xl border border-amber-500/30 shadow-inner">
              <ShieldCheck size={22} className="text-amber-400" />
            </span>
            Gestão de Identidade e Acesso (IAM)
          </h2>
          <p className="text-slate-400 text-sm mt-1 ml-1">
            Aprovação, controlo de roles e gestão de contas do sistema.
          </p>
        </div>
        <button
          onClick={fetchUsers}
          disabled={loading}
          className="flex items-center gap-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 px-4 py-2.5 rounded-xl text-sm font-semibold transition-all disabled:opacity-50 flex-shrink-0">
          <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
          Atualizar
        </button>
      </div>

      {/* ── Tabs ── */}
      <div className="flex gap-1 border-b border-slate-800">
        {[
          { id: 'pending', label: 'Pendentes', Icon: Clock },
          { id: 'all',     label: 'Todos os Utilizadores', Icon: Users },
        ].map(({ id, label, Icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-semibold rounded-t-xl border-b-2 transition-all ${
              activeTab === id
                ? 'border-emerald-500 text-emerald-400 bg-emerald-500/10'
                : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'}`}>
            <Icon size={15} />
            {label}
          </button>
        ))}
      </div>

      {/* ── Error ── */}
      {error && (
        <div className="flex items-start gap-3 bg-red-500/10 border border-red-500/20 text-red-400 p-4 rounded-xl">
          <AlertTriangle size={18} className="flex-shrink-0 mt-0.5" />
          <span className="text-sm leading-relaxed">{error}</span>
        </div>
      )}

      {/* ── Loading ── */}
      {loading && (
        <div className="flex items-center justify-center py-16 gap-3 text-slate-500">
          <RefreshCw size={20} className="animate-spin" />
          <span>Carregando utilizadores...</span>
        </div>
      )}

      {/* ── Empty state ── */}
      {!loading && !error && users.length === 0 && (
        <div className="text-center py-16 text-slate-500 bg-slate-900/50 rounded-2xl border border-slate-800">
          <Users size={40} className="mx-auto mb-3 opacity-30" />
          <p className="font-semibold text-slate-400">
            {activeTab === 'pending'
              ? 'Nenhuma conta a aguardar aprovação.'
              : 'Nenhum utilizador encontrado no sistema.'}
          </p>
        </div>
      )}

      {/* ── Tabela de utilizadores ── */}
      {!loading && !error && users.length > 0 && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-slate-800/60 text-slate-400 text-xs uppercase tracking-wider">
                <tr>
                  <th className="py-3.5 px-5 text-left">Email / Utilizador</th>
                  <th className="py-3.5 px-5 text-left">Role Atual</th>
                  <th className="py-3.5 px-5 text-left">Status</th>
                  <th className="py-3.5 px-5 text-left">Criado em</th>
                  <th className="py-3.5 px-5 text-left">Ações</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {users.map((u) => {
                  const isPending   = u.status === 'PENDING' || activeTab === 'pending';
                  const isSuspended = u.status === 'SUSPENDED' || u.active === false;
                  const isActioning = actionLoading === u.id;
                  const isSuperadmin = u.role === 'superadmin';

                  return (
                    <tr key={u.id} className="hover:bg-slate-800/30 transition-colors">
                      <td className="py-4 px-5">
                        <div className="font-medium text-slate-200">{u.email || u.username || '—'}</div>
                        <div className="text-slate-500 font-mono text-xs mt-0.5">
                          {String(u.id).substring(0, 16)}…
                        </div>
                      </td>
                      <td className="py-4 px-5">
                        <span className={`px-2.5 py-1 rounded-full text-xs font-bold uppercase border
                          ${ROLE_BADGE[u.role?.toLowerCase()] || ROLE_BADGE.viewer}`}>
                          {u.role || 'viewer'}
                        </span>
                      </td>
                      <td className="py-4 px-5">
                        <span className={`px-2.5 py-1 rounded-full text-xs font-bold uppercase border
                          ${STATUS_BADGE[u.status] || STATUS_BADGE.PENDING}`}>
                          {u.status || (u.active === false ? 'SUSPENDED' : 'PENDING')}
                        </span>
                      </td>
                      <td className="py-4 px-5 text-slate-400 text-xs">
                        {u.created_at ? new Date(u.created_at).toLocaleDateString('pt-BR') : '—'}
                      </td>
                      <td className="py-4 px-5">
                        {isPending ? (
                          /* ── Aprovação ── */
                          <div className="flex items-center gap-2 flex-wrap">
                            <select
                              id={`role-select-${u.id}`}
                              defaultValue="viewer"
                              className="bg-slate-950 border border-slate-700 text-slate-300 rounded-lg px-2.5 py-1.5 text-xs outline-none focus:border-emerald-500 transition-colors cursor-pointer">
                              <option value="viewer">VIEWER</option>
                              <option value="operator">OPERATOR</option>
                              <option value="admin">ADMIN</option>
                              <option value="superadmin">SUPERADMIN</option>
                            </select>
                            <button
                              disabled={isActioning}
                              onClick={() => {
                                const el = document.getElementById(`role-select-${u.id}`);
                                handleApprove(u.id, el?.value || 'viewer');
                              }}
                              className="flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold px-3.5 py-1.5 rounded-lg transition-all disabled:opacity-50 shadow shadow-emerald-500/20 whitespace-nowrap">
                              <UserCheck size={13} />
                              {isActioning ? '...' : 'Aprovar'}
                            </button>
                          </div>
                        ) : isSuspended ? (
                          /* ── Reativar ── */
                          <button
                            disabled={isActioning || isSuperadmin}
                            onClick={() => handleReactivate(u.id)}
                            className="flex items-center gap-1.5 bg-emerald-600/20 hover:bg-emerald-600/40 text-emerald-400 text-xs font-bold px-3.5 py-1.5 rounded-lg border border-emerald-500/30 transition-all disabled:opacity-30 whitespace-nowrap">
                            <ShieldCheck size={13} />
                            {isActioning ? '...' : 'Reativar'}
                          </button>
                        ) : (
                          /* ── Suspender ── */
                          <button
                            disabled={isActioning || isSuperadmin}
                            onClick={() => handleSuspend(u.id)}
                            title={isSuperadmin ? 'Superadmin não pode ser suspenso' : 'Suspender conta'}
                            className="flex items-center gap-1.5 bg-red-600/20 hover:bg-red-600/40 text-red-400 text-xs font-bold px-3.5 py-1.5 rounded-lg border border-red-500/30 transition-all disabled:opacity-30 whitespace-nowrap">
                            {isSuperadmin ? <ShieldOff size={13} /> : <UserX size={13} />}
                            {isSuperadmin ? 'Protegido' : (isActioning ? '...' : 'Suspender')}
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <div className="px-5 py-3 bg-slate-800/30 border-t border-slate-800 text-xs text-slate-500 text-right">
            {users.length} utilizador(es) listado(s)
          </div>
        </div>
      )}
    </div>
  );
}
