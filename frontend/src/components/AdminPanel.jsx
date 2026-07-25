import React, { useEffect, useState, useCallback } from 'react';
import { getBaseUrl } from '../utils/config';
import { supabase, isSupabaseConfigured } from '../utils/supabaseClient';
import {
  UserCheck, UserX, ShieldCheck, Clock, Users,
  RefreshCw, AlertTriangle, ShieldOff, Search,
  XCircle, CheckCircle2, AlertCircle, ChevronDown,
} from 'lucide-react';
import { toast } from 'sonner';

// ─── Helpers de estilo ───────────────────────────────────────────────────────
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
  REJECTED:  'bg-slate-600/20 text-slate-400 border-slate-600/30',
};

// ─── Modal de Confirmação Inline ─────────────────────────────────────────────
function ConfirmModal({ title, message, onConfirm, onCancel, danger = false, children }) {
  return (
    <div className="fixed inset-0 z-[200] flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={onCancel} />
      <div className="relative bg-slate-900 border border-slate-700 rounded-2xl p-6 w-full max-w-md shadow-2xl animate-scale-in">
        <h3 className="text-lg font-bold text-white mb-2">{title}</h3>
        <p className="text-slate-400 text-sm mb-4">{message}</p>
        {children}
        <div className="flex gap-3 justify-end mt-5">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-sm font-semibold text-slate-300 bg-slate-800 hover:bg-slate-700 rounded-xl transition-all"
          >
            Cancelar
          </button>
          <button
            onClick={onConfirm}
            className={`px-5 py-2 text-sm font-bold rounded-xl transition-all shadow ${
              danger
                ? 'bg-red-600 hover:bg-red-500 text-white shadow-red-500/20'
                : 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-emerald-500/20'
            }`}
          >
            Confirmar
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Componente principal ─────────────────────────────────────────────────────
export default function AdminPanel({ token, serverIP }) {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionLoading, setActionLoading] = useState(null);
  const [activeTab, setActiveTab] = useState('pending');
  const [search, setSearch] = useState('');
  const [confirm, setConfirm] = useState(null); // { type, userId, extra }
  const [rejectReason, setRejectReason] = useState('');

  const getAuthToken = useCallback(async () => {
    if (isSupabaseConfigured) {
      try {
        const { data: { session } } = await supabase.auth.getSession();
        if (session?.access_token) return session.access_token;
      } catch { /* fallthrough */ }
    }
    return token;
  }, [token]);

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    setError('');
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 10000);
    try {
      const authToken = await getAuthToken();
      const endpoint = activeTab === 'pending'
        ? `${getBaseUrl(serverIP)}/api/admin/pending-users`
        : `${getBaseUrl(serverIP)}/api/accounts/users`;

      const res = await fetch(endpoint, {
        headers: { Authorization: `Bearer ${authToken}` },
        signal: controller.signal,
      });

      if (res.status === 401) { setError('Sessão expirada. Faça login novamente.'); return; }
      if (res.status === 403) { setError('Acesso negado. Apenas administradores podem aceder a esta área.'); return; }
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        setError(d.msg || d.error || `Erro ${res.status} no servidor.`);
        return;
      }
      const d = await res.json();
      setUsers(d.items || []);
    } catch (err) {
      setError(err.name === 'AbortError'
        ? 'Tempo limite excedido. Verifique se o servidor backend está acessível.'
        : 'Falha de conexão. Verifique se o servidor está online.');
    } finally {
      clearTimeout(timeout);
      setLoading(false);
    }
  }, [serverIP, getAuthToken, activeTab]);

  useEffect(() => { fetchUsers(); }, [fetchUsers]);

  // ─── Ações ───────────────────────────────────────────────────────────────────
  const handleApprove = async (userId, targetRole) => {
    setActionLoading(userId);
    try {
      const authToken = await getAuthToken();
      const res = await fetch(`${getBaseUrl(serverIP)}/api/admin/approve-user`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${authToken}` },
        body: JSON.stringify({ target_user_id: userId, target_role: targetRole }),
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        toast.error(`Erro ao aprovar: ${d.detail || d.msg || 'Falha desconhecida.'}`);
        return;
      }
      toast.success('✅ Utilizador aprovado com sucesso!');
      setUsers(prev => prev.filter(u => u.id !== userId));
    } catch { toast.error('Erro de rede ao aprovar utilizador.'); }
    finally { setActionLoading(null); setConfirm(null); }
  };

  const handleReject = async (userId, reason) => {
    setActionLoading(userId);
    try {
      const authToken = await getAuthToken();
      const res = await fetch(`${getBaseUrl(serverIP)}/api/admin/reject-user`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${authToken}` },
        body: JSON.stringify({ target_user_id: userId, reason: reason || 'Acesso negado pelo administrador.' }),
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        toast.error(`Erro ao rejeitar: ${d.detail || 'Falha desconhecida.'}`);
        return;
      }
      toast.success('Solicitação rejeitada.');
      setUsers(prev => prev.filter(u => u.id !== userId));
    } catch { toast.error('Erro de rede ao rejeitar.'); }
    finally { setActionLoading(null); setConfirm(null); setRejectReason(''); }
  };

  const handleSuspend = async (userId) => {
    setActionLoading(userId);
    try {
      const authToken = await getAuthToken();
      const res = await fetch(`${getBaseUrl(serverIP)}/api/accounts/users/${userId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${authToken}` },
        body: JSON.stringify({ active: false }),
      });
      if (res.ok) {
        toast.success('🔒 Conta suspensa.');
        setUsers(prev => prev.map(u => u.id === userId ? { ...u, status: 'SUSPENDED', active: false } : u));
      } else {
        const d = await res.json().catch(() => ({}));
        toast.error(`Erro: ${d.detail || d.msg || 'Falha desconhecida.'}`);
      }
    } catch { toast.error('Erro de rede.'); }
    finally { setActionLoading(null); setConfirm(null); }
  };

  const handleReactivate = async (userId) => {
    setActionLoading(userId);
    try {
      const authToken = await getAuthToken();
      const res = await fetch(`${getBaseUrl(serverIP)}/api/accounts/users/${userId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${authToken}` },
        body: JSON.stringify({ active: true }),
      });
      if (res.ok) {
        toast.success('✅ Conta reativada.');
        setUsers(prev => prev.map(u => u.id === userId ? { ...u, status: 'ACTIVE', active: true } : u));
      } else {
        const d = await res.json().catch(() => ({}));
        toast.error(`Erro: ${d.detail || d.msg || 'Falha desconhecida.'}`);
      }
    } catch { toast.error('Erro de rede.'); }
    finally { setActionLoading(null); setConfirm(null); }
  };

  const handleDelete = async (userId) => {
    setActionLoading(userId);
    try {
      const authToken = await getAuthToken();
      const res = await fetch(`${getBaseUrl(serverIP)}/api/accounts/users/${userId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${authToken}` },
      });
      if (res.ok) {
        toast.success('🗑️ Conta excluída permanentemente.');
        setUsers(prev => prev.filter(u => u.id !== userId));
      } else {
        const d = await res.json().catch(() => ({}));
        toast.error(`Erro: ${d.detail || d.msg || 'Falha desconhecida.'}`);
      }
    } catch { toast.error('Erro de rede.'); }
    finally { setActionLoading(null); setConfirm(null); }
  };

  // ─── Filtro de busca ─────────────────────────────────────────────────────────
  const filtered = users.filter(u => {
    const q = search.toLowerCase();
    return !q ||
      (u.full_name || '').toLowerCase().includes(q) ||
      (u.email || '').toLowerCase().includes(q) ||
      (u.role || '').toLowerCase().includes(q) ||
      (u.status || '').toLowerCase().includes(q);
  });

  // ─── Render ──────────────────────────────────────────────────────────────────
  return (
    <div className="space-y-6 pb-8">
      {/* ── Modais de Confirmação ── */}
      {confirm?.type === 'approve' && (
        <ConfirmModal
          title="Aprovar Acesso"
          message={`Aprovar o utilizador como ${(confirm.role || 'viewer').toUpperCase()}? Ele terá acesso imediato ao sistema.`}
          onConfirm={() => handleApprove(confirm.userId, confirm.role || 'viewer')}
          onCancel={() => setConfirm(null)}
        />
      )}
      {confirm?.type === 'reject' && (
        <ConfirmModal
          title="Rejeitar Solicitação"
          message="Informe o motivo da rejeição (opcional). O acesso será negado permanentemente."
          danger
          onConfirm={() => handleReject(confirm.userId, rejectReason)}
          onCancel={() => { setConfirm(null); setRejectReason(''); }}
        >
          <textarea
            value={rejectReason}
            onChange={e => setRejectReason(e.target.value)}
            placeholder="Motivo da rejeição (opcional)..."
            rows={2}
            className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm text-slate-300 placeholder-slate-600 outline-none focus:border-red-500/50 resize-none"
          />
        </ConfirmModal>
      )}
      {confirm?.type === 'suspend' && (
        <ConfirmModal
          title="Suspender Conta"
          message="O utilizador perderá o acesso imediatamente. Poderá ser reativado a qualquer momento."
          danger
          onConfirm={() => handleSuspend(confirm.userId)}
          onCancel={() => setConfirm(null)}
        />
      )}
      {confirm?.type === 'delete' && (
        <ConfirmModal
          title="Excluir Conta Permanentemente"
          message="Esta ação não pode ser desfeita. Todos os dados do utilizador serão removidos."
          danger
          onConfirm={() => handleDelete(confirm.userId)}
          onCancel={() => setConfirm(null)}
        />
      )}
      {confirm?.type === 'reactivate' && (
        <ConfirmModal
          title="Reativar Conta"
          message="O utilizador voltará a ter acesso ao sistema com a role anterior."
          onConfirm={() => handleReactivate(confirm.userId)}
          onCancel={() => setConfirm(null)}
        />
      )}

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
          className="flex items-center gap-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 px-4 py-2.5 rounded-xl text-sm font-semibold transition-all disabled:opacity-50 flex-shrink-0"
        >
          <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
          Atualizar
        </button>
      </div>

      {/* ── Tabs ── */}
      <div className="flex gap-1 border-b border-slate-800">
        {[
          { id: 'pending', label: 'Pendentes de Aprovação', Icon: Clock },
          { id: 'all',     label: 'Todos os Utilizadores', Icon: Users },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-semibold rounded-t-xl border-b-2 transition-all ${
              activeTab === tab.id
                ? 'border-emerald-500 text-emerald-400 bg-emerald-500/10'
                : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'}`}
          >
            <tab.Icon size={15} />
            {tab.label}
          </button>
        ))}
      </div>

      {/* ── Search ── */}
      {!loading && users.length > 0 && (
        <div className="relative">
          <Search size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            placeholder="Pesquisar por nome, email, role ou status..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full bg-slate-900 border border-slate-800 text-slate-200 rounded-xl pl-10 pr-4 py-2.5 text-sm outline-none focus:border-emerald-500/50 transition-colors placeholder-slate-600"
          />
        </div>
      )}

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
      {!loading && !error && filtered.length === 0 && (
        <div className="text-center py-16 text-slate-500 bg-slate-900/50 rounded-2xl border border-slate-800">
          <Users size={40} className="mx-auto mb-3 opacity-30" />
          <p className="font-semibold text-slate-400">
            {search
              ? 'Nenhum utilizador corresponde à pesquisa.'
              : activeTab === 'pending'
                ? '✅ Nenhuma conta a aguardar aprovação.'
                : 'Nenhum utilizador encontrado no sistema.'}
          </p>
        </div>
      )}

      {/* ── Tabela ── */}
      {!loading && !error && filtered.length > 0 && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-slate-800/60 text-slate-400 text-xs uppercase tracking-wider">
                <tr>
                  <th className="py-3.5 px-5 text-left">Utilizador / Dados</th>
                  <th className="py-3.5 px-5 text-left">Localidade / Contato</th>
                  <th className="py-3.5 px-5 text-left">Role</th>
                  <th className="py-3.5 px-5 text-left">Status</th>
                  <th className="py-3.5 px-5 text-left">Cadastro</th>
                  <th className="py-3.5 px-5 text-left">Ações</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {filtered.map((u) => {
                  const isPending   = u.status === 'PENDING';
                  const isSuspended = u.status === 'SUSPENDED' || u.active === false;
                  const isActioning = actionLoading === u.id;
                  const isSuperadmin = u.role === 'superadmin';
                  const [approveRole, setApproveRole] = React.useState('viewer');

                  return (
                    <tr key={u.id} className="hover:bg-slate-800/30 transition-colors">
                      {/* Dados do usuário */}
                      <td className="py-4 px-5">
                        <div className="font-semibold text-slate-200">{u.full_name || '—'}</div>
                        <div className="text-slate-500 text-xs mt-0.5 space-y-0.5">
                          {u.email && <div>{u.email}</div>}
                          {u.phone && <div>📞 {u.phone}</div>}
                          {u.cpf   && <div>🪪 CPF: {u.cpf}</div>}
                        </div>
                      </td>

                      {/* Localidade */}
                      <td className="py-4 px-5 text-slate-400 text-xs">
                        <div>{u.location || '—'}</div>
                        {u.age && <div className="mt-0.5">{u.age} anos</div>}
                      </td>

                      {/* Role */}
                      <td className="py-4 px-5">
                        <span className={`px-2.5 py-1 rounded-full text-xs font-bold uppercase border ${ROLE_BADGE[u.role?.toLowerCase()] || ROLE_BADGE.viewer}`}>
                          {u.role || 'viewer'}
                        </span>
                      </td>

                      {/* Status */}
                      <td className="py-4 px-5">
                        <span className={`px-2.5 py-1 rounded-full text-xs font-bold uppercase border ${STATUS_BADGE[u.status] || STATUS_BADGE.PENDING}`}>
                          {u.status === 'PENDING'   && '⏳ '}
                          {u.status === 'ACTIVE'    && '✅ '}
                          {u.status === 'SUSPENDED' && '🔒 '}
                          {u.status === 'REJECTED'  && '❌ '}
                          {u.status || 'PENDING'}
                        </span>
                      </td>

                      {/* Data */}
                      <td className="py-4 px-5 text-slate-400 text-xs">
                        {u.created_at ? new Date(u.created_at).toLocaleDateString('pt-BR') : '—'}
                      </td>

                      {/* Ações */}
                      <td className="py-4 px-5">
                        <div className="flex items-center gap-2 flex-wrap">
                          {isPending ? (
                            <>
                              {/* Seletor de role + botão Aprovar */}
                              <select
                                aria-label="Selecionar função"
                                value={approveRole}
                                onChange={e => setApproveRole(e.target.value)}
                                className="bg-slate-950 border border-slate-700 text-slate-300 rounded-lg px-2 py-1.5 text-xs outline-none focus:border-emerald-500 cursor-pointer"
                              >
                                <option value="viewer">VIEWER</option>
                                <option value="operator">OPERATOR</option>
                                <option value="admin">ADMIN</option>
                              </select>
                              <button
                                disabled={isActioning}
                                onClick={() => setConfirm({ type: 'approve', userId: u.id, role: approveRole })}
                                className="flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold px-3 py-1.5 rounded-lg transition-all disabled:opacity-50 shadow shadow-emerald-500/20 whitespace-nowrap"
                              >
                                {isActioning ? <RefreshCw size={12} className="animate-spin" /> : <UserCheck size={12} />}
                                Aprovar
                              </button>
                              <button
                                disabled={isActioning}
                                onClick={() => setConfirm({ type: 'reject', userId: u.id })}
                                className="flex items-center gap-1.5 bg-red-900/40 hover:bg-red-600/50 text-red-300 text-xs font-bold px-3 py-1.5 rounded-lg border border-red-700/50 transition-all disabled:opacity-50 whitespace-nowrap"
                              >
                                <XCircle size={12} />
                                Rejeitar
                              </button>
                            </>
                          ) : isSuspended ? (
                            <button
                              disabled={isActioning || isSuperadmin}
                              onClick={() => setConfirm({ type: 'reactivate', userId: u.id })}
                              className="flex items-center gap-1.5 bg-emerald-600/20 hover:bg-emerald-600/40 text-emerald-400 text-xs font-bold px-3 py-1.5 rounded-lg border border-emerald-500/30 transition-all disabled:opacity-30 whitespace-nowrap"
                            >
                              {isActioning ? <RefreshCw size={12} className="animate-spin" /> : <CheckCircle2 size={12} />}
                              Reativar
                            </button>
                          ) : (
                            <button
                              disabled={isActioning || isSuperadmin}
                              onClick={() => setConfirm({ type: 'suspend', userId: u.id })}
                              title={isSuperadmin ? 'Superadmin não pode ser suspenso' : 'Suspender conta'}
                              className="flex items-center gap-1.5 bg-amber-600/20 hover:bg-amber-600/40 text-amber-400 text-xs font-bold px-3 py-1.5 rounded-lg border border-amber-500/30 transition-all disabled:opacity-30 whitespace-nowrap"
                            >
                              {isSuperadmin ? <ShieldOff size={12} /> : (isActioning ? <RefreshCw size={12} className="animate-spin" /> : <AlertCircle size={12} />)}
                              {isSuperadmin ? 'Protegido' : 'Suspender'}
                            </button>
                          )}

                          {/* Excluir — sempre visível, bloqueado para superadmin */}
                          {!isPending && (
                            <button
                              disabled={isActioning || isSuperadmin}
                              onClick={() => setConfirm({ type: 'delete', userId: u.id })}
                              title={isSuperadmin ? 'Superadmin não pode ser excluído' : 'Excluir conta permanentemente'}
                              className="flex items-center gap-1.5 bg-red-900/30 hover:bg-red-600/50 text-red-400 text-xs font-bold px-3 py-1.5 rounded-lg border border-red-800/50 transition-all disabled:opacity-30 whitespace-nowrap"
                            >
                              <UserX size={12} />
                              Excluir
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <div className="px-5 py-3 bg-slate-800/30 border-t border-slate-800 text-xs text-slate-500 flex justify-between items-center">
            <span>{filtered.length} de {users.length} utilizador(es)</span>
            {search && (
              <button onClick={() => setSearch('')} className="text-emerald-400 hover:text-emerald-300 transition-colors font-medium">
                Limpar filtro
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
