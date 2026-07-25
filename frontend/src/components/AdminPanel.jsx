import React, { useEffect, useState, useCallback, useRef } from 'react';
import { supabase, isSupabaseConfigured } from '../utils/supabaseClient';
import {
  UserCheck, UserX, ShieldCheck, Clock, Users,
  RefreshCw, AlertTriangle, ShieldOff, Search,
  XCircle, CheckCircle2, AlertCircle, Settings,
  Crown, Eye, Wrench, ChevronDown,
} from 'lucide-react';
import { toast } from 'sonner';

// ─── Constantes ──────────────────────────────────────────────────────────────
const ROLE_LEVELS = { viewer: 1, operator: 2, admin: 3, superadmin: 4 };

const ROLE_META = {
  viewer:     { label: 'Visualizador', icon: Eye,       cls: 'bg-slate-500/20 text-slate-300 border-slate-500/30' },
  operator:   { label: 'Operador',     icon: Wrench,    cls: 'bg-blue-500/20 text-blue-300 border-blue-500/30' },
  admin:      { label: 'Admin',        icon: ShieldCheck,cls: 'bg-amber-500/20 text-amber-300 border-amber-500/30' },
  superadmin: { label: 'Superadmin',   icon: Crown,     cls: 'bg-rose-500/20 text-rose-300 border-rose-500/30' },
};

const STATUS_META = {
  PENDING:   { cls: 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30',  icon: '⏳' },
  ACTIVE:    { cls: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30', icon: '✅' },
  SUSPENDED: { cls: 'bg-red-500/20 text-red-300 border-red-500/30',            icon: '🔒' },
  REJECTED:  { cls: 'bg-slate-600/20 text-slate-400 border-slate-600/30',      icon: '❌' },
};

// ─── Modal de Confirmação ─────────────────────────────────────────────────────
function ConfirmModal({ title, message, onConfirm, onCancel, danger = false, loading = false, children }) {
  return (
    <div className="fixed inset-0 z-[300] flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/75 backdrop-blur-sm" onClick={onCancel} />
      <div className="relative bg-slate-900 border border-slate-700 rounded-2xl p-6 w-full max-w-md shadow-2xl z-10" style={{animation:'scale-in .15s ease'}}>
        <h3 className="text-base font-bold text-white mb-1">{title}</h3>
        <p className="text-slate-400 text-sm mb-4 leading-relaxed">{message}</p>
        {children}
        <div className="flex gap-3 justify-end mt-5">
          <button onClick={onCancel} disabled={loading}
            className="px-4 py-2 text-sm font-semibold text-slate-300 bg-slate-800 hover:bg-slate-700 rounded-xl transition-all disabled:opacity-50">
            Cancelar
          </button>
          <button onClick={onConfirm} disabled={loading}
            className={`px-5 py-2 text-sm font-bold rounded-xl transition-all flex items-center gap-2 disabled:opacity-50 ${
              danger ? 'bg-red-600 hover:bg-red-500 text-white' : 'bg-emerald-600 hover:bg-emerald-500 text-white'
            }`}>
            {loading && <RefreshCw size={13} className="animate-spin" />}
            Confirmar
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Drawer de Edição de Perfil ───────────────────────────────────────────────
function ProfileDrawer({ user, myRole, onClose, onSaved }) {
  const [form, setForm] = useState({
    full_name: user.full_name || '',
    phone:     user.phone || '',
    location:  user.location || '',
    age:       user.age || '',
    role:      user.role || 'viewer',
    status:    user.status || 'PENDING',
  });
  const [saving, setSaving] = useState(false);
  const myLevel = ROLE_LEVELS[myRole] || 0;

  const handleSave = async () => {
    setSaving(true);
    try {
      const payload = {
        full_name: form.full_name,
        phone:     form.phone,
        location:  form.location,
        age:       form.age ? parseInt(form.age) : null,
        role:      form.role,
        status:    form.status,
      };
      if (form.status === 'ACTIVE' && !user.approved_at) {
        payload.approved_at = new Date().toISOString();
      }
      const { error } = await supabase.from('profiles').update(payload).eq('id', user.id);
      if (error) throw error;
      toast.success('✅ Perfil atualizado com sucesso!');
      onSaved({ ...user, ...payload });
      onClose();
    } catch (err) {
      toast.error(`Erro: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  const roles = Object.entries(ROLE_META).filter(([r]) => ROLE_LEVELS[r] < myLevel || myRole === 'superadmin');

  return (
    <div className="fixed inset-0 z-[250] flex items-end sm:items-center justify-center p-0 sm:p-4">
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-slate-900 border border-slate-700 rounded-t-2xl sm:rounded-2xl w-full sm:max-w-lg shadow-2xl z-10 max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-slate-800">
          <div>
            <h3 className="text-base font-bold text-white">Editar Perfil</h3>
            <p className="text-xs text-slate-400 mt-0.5">{user.email}</p>
          </div>
          <button onClick={onClose} className="p-2 text-slate-500 hover:text-slate-300 rounded-lg hover:bg-slate-800 transition-all">
            <XCircle size={18} />
          </button>
        </div>

        {/* Body */}
        <div className="overflow-y-auto p-5 space-y-4 flex-1">
          {/* Nome */}
          <div>
            <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">Nome Completo</label>
            <input value={form.full_name} onChange={e => setForm(f=>({...f, full_name:e.target.value}))}
              className="w-full bg-slate-950 border border-slate-800 text-slate-200 rounded-xl px-4 py-2.5 text-sm outline-none focus:border-emerald-500/60 transition-colors"
              placeholder="Nome do utilizador" />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">Telefone</label>
              <input value={form.phone} onChange={e => setForm(f=>({...f, phone:e.target.value}))}
                className="w-full bg-slate-950 border border-slate-800 text-slate-200 rounded-xl px-4 py-2.5 text-sm outline-none focus:border-emerald-500/60 transition-colors"
                placeholder="(00) 00000-0000" />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">Idade</label>
              <input type="number" value={form.age} onChange={e => setForm(f=>({...f, age:e.target.value}))}
                className="w-full bg-slate-950 border border-slate-800 text-slate-200 rounded-xl px-4 py-2.5 text-sm outline-none focus:border-emerald-500/60 transition-colors"
                placeholder="—" />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">Localidade</label>
            <input value={form.location} onChange={e => setForm(f=>({...f, location:e.target.value}))}
              className="w-full bg-slate-950 border border-slate-800 text-slate-200 rounded-xl px-4 py-2.5 text-sm outline-none focus:border-emerald-500/60 transition-colors"
              placeholder="Cidade/Estado" />
          </div>

          {/* Role */}
          <div>
            <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">Função (Role)</label>
            <div className="grid grid-cols-2 gap-2">
              {roles.map(([r, meta]) => {
                const Icon = meta.icon;
                return (
                  <button key={r} onClick={() => setForm(f=>({...f, role:r}))}
                    className={`flex items-center gap-2 px-3 py-2.5 rounded-xl border text-sm font-semibold transition-all ${
                      form.role === r
                        ? 'border-emerald-500/60 bg-emerald-500/10 text-emerald-300'
                        : 'border-slate-700 bg-slate-800/50 text-slate-400 hover:border-slate-600 hover:text-slate-200'
                    }`}>
                    <Icon size={14} />
                    {meta.label}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Status */}
          <div>
            <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">Status da Conta</label>
            <div className="grid grid-cols-2 gap-2">
              {Object.entries(STATUS_META).filter(([s]) => s !== 'REJECTED').map(([s, meta]) => (
                <button key={s} onClick={() => setForm(f=>({...f, status:s}))}
                  className={`flex items-center gap-2 px-3 py-2.5 rounded-xl border text-sm font-semibold transition-all ${
                    form.status === s
                      ? 'border-emerald-500/60 bg-emerald-500/10 text-emerald-300'
                      : 'border-slate-700 bg-slate-800/50 text-slate-400 hover:border-slate-600 hover:text-slate-200'
                  }`}>
                  <span>{meta.icon}</span>
                  {s}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-5 border-t border-slate-800 flex gap-3">
          <button onClick={onClose} disabled={saving}
            className="flex-1 px-4 py-2.5 text-sm font-semibold text-slate-300 bg-slate-800 hover:bg-slate-700 rounded-xl transition-all disabled:opacity-50">
            Cancelar
          </button>
          <button onClick={handleSave} disabled={saving}
            className="flex-1 px-4 py-2.5 text-sm font-bold text-white bg-emerald-600 hover:bg-emerald-500 rounded-xl transition-all disabled:opacity-50 flex items-center justify-center gap-2">
            {saving && <RefreshCw size={13} className="animate-spin" />}
            {saving ? 'Salvando...' : 'Salvar Alterações'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Componente Principal ─────────────────────────────────────────────────────
export default function AdminPanel({ token, serverIP, role: myRole }) {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState('pending');
  const [search, setSearch] = useState('');
  const [actionLoading, setActionLoading] = useState(null);
  const [confirm, setConfirm] = useState(null); // {type, userId, extra}
  const [rejectReason, setRejectReason] = useState('');
  const [editUser, setEditUser] = useState(null);
  const abortRef = useRef(null);

  const myLevel = ROLE_LEVELS[myRole] || 4; // superadmin by default in this panel

  // ── Fetch direto do Supabase (sem depender do backend) ────────────────────
  const fetchUsers = useCallback(async () => {
    setLoading(true);
    setError('');

    // Cancela fetch anterior se houver
    if (abortRef.current) abortRef.current = false;
    abortRef.current = true;

    try {
      if (!isSupabaseConfigured) {
        setError('Supabase não está configurado neste ambiente. Configure VITE_SUPABASE_URL e VITE_SUPABASE_ANON_KEY.');
        setUsers([]);
        return;
      }

      let query = supabase.from('profiles').select('*').order('created_at', { ascending: false });

      if (activeTab === 'pending') {
        query = query.eq('status', 'PENDING');
      }

      const { data, error: sbErr } = await query;

      if (!abortRef.current) return; // componente desmontado

      if (sbErr) {
        // Tabela não existe ainda — mostrar estado vazio amigável
        if (sbErr.code === 'PGRST116' || sbErr.message?.includes('does not exist')) {
          setError('A tabela "profiles" ainda não existe no Supabase. Execute a migration SQL para criá-la.');
        } else {
          setError(`Erro Supabase: ${sbErr.message}`);
        }
        setUsers([]);
        return;
      }

      setUsers(data || []);
    } catch (err) {
      if (abortRef.current) {
        setError(`Falha ao carregar: ${err.message}`);
      }
    } finally {
      if (abortRef.current) setLoading(false);
    }
  }, [activeTab]);

  useEffect(() => {
    fetchUsers();
    return () => { abortRef.current = false; };
  }, [fetchUsers]);

  // ── Aprovar ───────────────────────────────────────────────────────────────
  const handleApprove = async (userId, targetRole) => {
    setActionLoading(userId);
    try {
      const { error } = await supabase.from('profiles').update({
        status: 'ACTIVE',
        role: targetRole,
        approved_at: new Date().toISOString(),
      }).eq('id', userId);
      if (error) throw error;
      toast.success('✅ Utilizador aprovado!');
      setUsers(prev => prev.filter(u => activeTab === 'pending' ? u.id !== userId : u));
      if (activeTab !== 'pending') {
        setUsers(prev => prev.map(u => u.id === userId ? { ...u, status: 'ACTIVE', role: targetRole } : u));
      }
    } catch (err) {
      toast.error(`Erro ao aprovar: ${err.message}`);
    } finally {
      setActionLoading(null);
      setConfirm(null);
    }
  };

  // ── Rejeitar ──────────────────────────────────────────────────────────────
  const handleReject = async (userId, reason) => {
    setActionLoading(userId);
    try {
      const { error } = await supabase.from('profiles').update({
        status: 'REJECTED',
        rejection_reason: reason || 'Acesso negado pelo administrador.',
      }).eq('id', userId);
      if (error) throw error;
      toast.success('Solicitação rejeitada.');
      setUsers(prev => prev.filter(u => u.id !== userId));
    } catch (err) {
      toast.error(`Erro: ${err.message}`);
    } finally {
      setActionLoading(null);
      setConfirm(null);
      setRejectReason('');
    }
  };

  // ── Suspender ─────────────────────────────────────────────────────────────
  const handleSuspend = async (userId) => {
    setActionLoading(userId);
    try {
      const { error } = await supabase.from('profiles').update({ status: 'SUSPENDED' }).eq('id', userId);
      if (error) throw error;
      toast.success('🔒 Conta suspensa.');
      setUsers(prev => prev.map(u => u.id === userId ? { ...u, status: 'SUSPENDED' } : u));
    } catch (err) {
      toast.error(`Erro: ${err.message}`);
    } finally {
      setActionLoading(null);
      setConfirm(null);
    }
  };

  // ── Reativar ──────────────────────────────────────────────────────────────
  const handleReactivate = async (userId) => {
    setActionLoading(userId);
    try {
      const { error } = await supabase.from('profiles').update({ status: 'ACTIVE' }).eq('id', userId);
      if (error) throw error;
      toast.success('✅ Conta reativada.');
      setUsers(prev => prev.map(u => u.id === userId ? { ...u, status: 'ACTIVE' } : u));
    } catch (err) {
      toast.error(`Erro: ${err.message}`);
    } finally {
      setActionLoading(null);
      setConfirm(null);
    }
  };

  // ── Filtro de busca ────────────────────────────────────────────────────────
  const filtered = users.filter(u => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      (u.full_name || '').toLowerCase().includes(q) ||
      (u.email    || '').toLowerCase().includes(q) ||
      (u.role     || '').toLowerCase().includes(q) ||
      (u.status   || '').toLowerCase().includes(q) ||
      (u.location || '').toLowerCase().includes(q)
    );
  });

  // ── Contagens de status ────────────────────────────────────────────────────
  const pendingCount = users.filter(u => u.status === 'PENDING').length;

  // ─── Render ────────────────────────────────────────────────────────────────
  return (
    <div className="space-y-6 pb-10">

      {/* ── Modais de Confirmação ── */}
      {confirm?.type === 'approve' && (
        <ConfirmModal title="Aprovar Acesso" loading={!!actionLoading}
          message={`Aprovar este utilizador com a função ${(confirm.role||'viewer').toUpperCase()}? Ele terá acesso imediato ao sistema.`}
          onConfirm={() => handleApprove(confirm.userId, confirm.role || 'viewer')}
          onCancel={() => setConfirm(null)} />
      )}
      {confirm?.type === 'reject' && (
        <ConfirmModal title="Rejeitar Solicitação" danger loading={!!actionLoading}
          message="Informe o motivo da rejeição (opcional)."
          onConfirm={() => handleReject(confirm.userId, rejectReason)}
          onCancel={() => { setConfirm(null); setRejectReason(''); }}>
          <textarea value={rejectReason} onChange={e => setRejectReason(e.target.value)} rows={2}
            placeholder="Motivo (opcional)..."
            className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm text-slate-300 placeholder-slate-600 outline-none focus:border-red-500/50 resize-none mt-1" />
        </ConfirmModal>
      )}
      {confirm?.type === 'suspend' && (
        <ConfirmModal title="Suspender Conta" danger loading={!!actionLoading}
          message="O utilizador perderá o acesso imediatamente. Pode ser reativado a qualquer momento."
          onConfirm={() => handleSuspend(confirm.userId)} onCancel={() => setConfirm(null)} />
      )}
      {confirm?.type === 'reactivate' && (
        <ConfirmModal title="Reativar Conta" loading={!!actionLoading}
          message="O utilizador voltará a ter acesso com a role anterior."
          onConfirm={() => handleReactivate(confirm.userId)} onCancel={() => setConfirm(null)} />
      )}

      {/* ── Drawer de Edição ── */}
      {editUser && (
        <ProfileDrawer user={editUser} myRole={myRole || 'superadmin'}
          onClose={() => setEditUser(null)}
          onSaved={updated => {
            setUsers(prev => prev.map(u => u.id === updated.id ? updated : u));
            if (activeTab === 'pending' && updated.status !== 'PENDING') {
              setUsers(prev => prev.filter(u => u.id !== updated.id));
            }
          }} />
      )}

      {/* ── Header ── */}
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
        <div>
          <h2 className="text-xl font-extrabold text-white tracking-tight flex items-center gap-3">
            <span className="bg-amber-500/15 p-2.5 rounded-xl border border-amber-500/30">
              <ShieldCheck size={20} className="text-amber-400" />
            </span>
            Gestão de Identidade e Acesso (IAM)
          </h2>
          <p className="text-slate-400 text-sm mt-1 ml-1">
            Aprovação, configuração de perfis e controlo de roles.
          </p>
        </div>
        <button onClick={fetchUsers} disabled={loading}
          className="flex items-center gap-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 px-4 py-2.5 rounded-xl text-sm font-semibold transition-all disabled:opacity-50 flex-shrink-0">
          <RefreshCw size={15} className={loading ? 'animate-spin' : ''} />
          Atualizar
        </button>
      </div>

      {/* ── Supabase não configurado — guia de setup ── */}
      {!isSupabaseConfigured && (
        <div className="bg-amber-500/10 border border-amber-500/20 rounded-2xl p-6">
          <div className="flex items-start gap-3">
            <AlertTriangle size={20} className="text-amber-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-bold text-amber-300 mb-1">Supabase não configurado</p>
              <p className="text-amber-200/70 text-sm mb-3">
                Para usar a gestão de acesso, configure as variáveis de ambiente no arquivo <code className="text-amber-300">.env</code>:
              </p>
              <pre className="bg-slate-950/80 rounded-lg p-3 text-xs text-emerald-300 font-mono border border-slate-800">
{`VITE_SUPABASE_URL=https://seu-projeto.supabase.co
VITE_SUPABASE_ANON_KEY=eyJ...`}
              </pre>
            </div>
          </div>
        </div>
      )}

      {/* ── Tabs ── */}
      {isSupabaseConfigured && (
        <>
          <div className="flex gap-1 border-b border-slate-800">
            {[
              { id: 'pending', label: 'Aguardando Aprovação', icon: Clock,  count: pendingCount },
              { id: 'all',     label: 'Todos os Utilizadores', icon: Users, count: null },
            ].map(({ id, label, icon: Icon, count }) => (
              <button key={id} onClick={() => setActiveTab(id)}
                className={`flex items-center gap-2 px-4 py-2.5 text-sm font-semibold rounded-t-xl border-b-2 transition-all ${
                  activeTab === id
                    ? 'border-emerald-500 text-emerald-400 bg-emerald-500/10'
                    : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'}`}>
                <Icon size={14} />
                {label}
                {count > 0 && (
                  <span className="bg-rose-500 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full min-w-[18px] text-center leading-tight">
                    {count}
                  </span>
                )}
              </button>
            ))}
          </div>

          {/* ── Search ── */}
          {!loading && users.length > 0 && (
            <div className="relative">
              <Search size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500" />
              <input type="text" placeholder="Pesquisar por nome, email, role, status..."
                value={search} onChange={e => setSearch(e.target.value)}
                className="w-full bg-slate-900 border border-slate-800 text-slate-200 rounded-xl pl-10 pr-4 py-2.5 text-sm outline-none focus:border-emerald-500/50 transition-colors placeholder-slate-600" />
            </div>
          )}

          {/* ── Error ── */}
          {error && (
            <div className="flex items-start gap-3 bg-red-500/10 border border-red-500/20 text-red-300 p-4 rounded-xl">
              <AlertTriangle size={17} className="flex-shrink-0 mt-0.5 text-red-400" />
              <span className="text-sm leading-relaxed">{error}</span>
            </div>
          )}

          {/* ── Loading ── */}
          {loading && (
            <div className="flex items-center justify-center py-20 gap-3 text-slate-500">
              <RefreshCw size={20} className="animate-spin text-emerald-500" />
              <span className="text-sm">Carregando utilizadores do Supabase...</span>
            </div>
          )}

          {/* ── Empty State ── */}
          {!loading && !error && filtered.length === 0 && (
            <div className="text-center py-20 bg-slate-900/50 rounded-2xl border border-slate-800">
              <Users size={40} className="mx-auto mb-3 text-slate-700" />
              <p className="font-semibold text-slate-400">
                {search
                  ? 'Nenhum utilizador corresponde à pesquisa.'
                  : activeTab === 'pending'
                    ? '✅ Nenhuma conta aguardando aprovação no momento.'
                    : 'Nenhum utilizador encontrado na tabela profiles.'}
              </p>
              {activeTab === 'all' && !search && (
                <p className="text-slate-600 text-sm mt-2">
                  Os utilizadores aparecem aqui após o primeiro login/signup.
                </p>
              )}
            </div>
          )}

          {/* ── Tabela ── */}
          {!loading && !error && filtered.length > 0 && (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden">
              <div className="overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead className="bg-slate-800/60 text-slate-400 text-xs uppercase tracking-wider">
                    <tr>
                      <th className="py-3.5 px-5 text-left">Utilizador</th>
                      <th className="py-3.5 px-5 text-left">Contato / Local</th>
                      <th className="py-3.5 px-5 text-left">Role</th>
                      <th className="py-3.5 px-5 text-left">Status</th>
                      <th className="py-3.5 px-5 text-left">Cadastro</th>
                      <th className="py-3.5 px-5 text-left">Ações</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/50">
                    {filtered.map(u => <UserRow key={u.id}
                      user={u} myLevel={myLevel}
                      actionLoading={actionLoading}
                      onApprove={(role) => setConfirm({ type: 'approve', userId: u.id, role })}
                      onReject={() => setConfirm({ type: 'reject', userId: u.id })}
                      onSuspend={() => setConfirm({ type: 'suspend', userId: u.id })}
                      onReactivate={() => setConfirm({ type: 'reactivate', userId: u.id })}
                      onEdit={() => setEditUser(u)}
                    />)}
                  </tbody>
                </table>
              </div>
              <div className="px-5 py-3 bg-slate-800/30 border-t border-slate-800 text-xs text-slate-500 flex justify-between items-center">
                <span>{filtered.length} de {users.length} utilizador(es)</span>
                {search && (
                  <button onClick={() => setSearch('')} className="text-emerald-400 hover:text-emerald-300 text-xs font-medium">
                    Limpar filtro
                  </button>
                )}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ─── Linha de Utilizador ─────────────────────────────────────────────────────
function UserRow({ user: u, myLevel, actionLoading, onApprove, onReject, onSuspend, onReactivate, onEdit }) {
  const [approveRole, setApproveRole] = useState('viewer');
  const isPending   = u.status === 'PENDING';
  const isSuspended = u.status === 'SUSPENDED';
  const isActioning = actionLoading === u.id;
  const isSuperadmin = u.role === 'superadmin';
  const targetLevel  = ROLE_LEVELS[u.role] || 0;
  const canModify    = myLevel > targetLevel || myLevel >= 4;

  const roleMeta   = ROLE_META[u.role?.toLowerCase()] || ROLE_META.viewer;
  const statusMeta = STATUS_META[u.status] || STATUS_META.PENDING;
  const RoleIcon   = roleMeta.icon;

  return (
    <tr className="hover:bg-slate-800/30 transition-colors">
      {/* Utilizador */}
      <td className="py-4 px-5">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-emerald-600 to-teal-700 flex items-center justify-center text-xs font-bold text-white uppercase flex-shrink-0">
            {(u.full_name || u.email || '?')[0]}
          </div>
          <div>
            <div className="font-semibold text-slate-200 text-sm">{u.full_name || '—'}</div>
            <div className="text-slate-500 text-xs mt-0.5">{u.email}</div>
            {u.cpf && <div className="text-slate-600 text-[10px]">CPF: {u.cpf}</div>}
          </div>
        </div>
      </td>

      {/* Contato */}
      <td className="py-4 px-5 text-slate-400 text-xs">
        {u.phone    && <div>📞 {u.phone}</div>}
        {u.location && <div>📍 {u.location}</div>}
        {u.age      && <div>🎂 {u.age} anos</div>}
        {!u.phone && !u.location && <span className="text-slate-600">—</span>}
      </td>

      {/* Role */}
      <td className="py-4 px-5">
        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold uppercase border ${roleMeta.cls}`}>
          <RoleIcon size={10} />
          {roleMeta.label}
        </span>
      </td>

      {/* Status */}
      <td className="py-4 px-5">
        <span className={`px-2.5 py-1 rounded-full text-xs font-bold uppercase border ${statusMeta.cls}`}>
          {statusMeta.icon} {u.status || 'PENDING'}
        </span>
      </td>

      {/* Data */}
      <td className="py-4 px-5 text-slate-400 text-xs">
        {u.created_at ? new Date(u.created_at).toLocaleDateString('pt-BR') : '—'}
      </td>

      {/* Ações */}
      <td className="py-4 px-5">
        <div className="flex items-center gap-2 flex-wrap">
          {/* Botão Editar Perfil — sempre visível para quem tem permissão */}
          {canModify && !isSuperadmin && (
            <button onClick={onEdit} disabled={isActioning}
              className="flex items-center gap-1.5 bg-slate-700/50 hover:bg-slate-600/60 text-slate-300 text-xs font-bold px-3 py-1.5 rounded-lg border border-slate-600/50 transition-all disabled:opacity-30 whitespace-nowrap">
              <Settings size={12} />
              Editar
            </button>
          )}

          {isPending && canModify && (
            <>
              <select value={approveRole} onChange={e => setApproveRole(e.target.value)}
                className="bg-slate-950 border border-slate-700 text-slate-300 rounded-lg px-2 py-1.5 text-xs outline-none focus:border-emerald-500 cursor-pointer">
                <option value="viewer">VIEWER</option>
                <option value="operator">OPERATOR</option>
                <option value="admin" disabled={myLevel < 3}>ADMIN</option>
              </select>
              <button disabled={isActioning} onClick={() => onApprove(approveRole)}
                className="flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold px-3 py-1.5 rounded-lg transition-all disabled:opacity-50 shadow shadow-emerald-500/20 whitespace-nowrap">
                {isActioning ? <RefreshCw size={12} className="animate-spin" /> : <UserCheck size={12} />}
                Aprovar
              </button>
              <button disabled={isActioning} onClick={onReject}
                className="flex items-center gap-1.5 bg-red-900/40 hover:bg-red-600/50 text-red-300 text-xs font-bold px-3 py-1.5 rounded-lg border border-red-700/50 transition-all disabled:opacity-50 whitespace-nowrap">
                <XCircle size={12} />
                Rejeitar
              </button>
            </>
          )}

          {!isPending && canModify && !isSuperadmin && (
            isSuspended ? (
              <button disabled={isActioning} onClick={onReactivate}
                className="flex items-center gap-1.5 bg-emerald-600/20 hover:bg-emerald-600/40 text-emerald-400 text-xs font-bold px-3 py-1.5 rounded-lg border border-emerald-500/30 transition-all disabled:opacity-30 whitespace-nowrap">
                {isActioning ? <RefreshCw size={12} className="animate-spin" /> : <CheckCircle2 size={12} />}
                Reativar
              </button>
            ) : (
              <button disabled={isActioning} onClick={onSuspend}
                className="flex items-center gap-1.5 bg-amber-600/20 hover:bg-amber-600/40 text-amber-400 text-xs font-bold px-3 py-1.5 rounded-lg border border-amber-500/30 transition-all disabled:opacity-30 whitespace-nowrap">
                {isActioning ? <RefreshCw size={12} className="animate-spin" /> : <AlertCircle size={12} />}
                Suspender
              </button>
            )
          )}

          {isSuperadmin && (
            <span className="flex items-center gap-1 text-xs text-rose-400/60 font-semibold px-2">
              <ShieldOff size={12} /> Protegido
            </span>
          )}
        </div>
      </td>
    </tr>
  );
}
