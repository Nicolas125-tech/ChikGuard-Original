import React, { useState, useEffect } from 'react';
import { User, Mail, Lock, Shield, CheckCircle, AlertCircle, Camera, Database } from 'lucide-react';
import { supabase, isSupabaseConfigured } from '../utils/supabaseClient';

export default function ProfilePanel({ role, cameras = [] }) {
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState('');
  const [error, setError] = useState('');
  
  const [formData, setFormData] = useState({
    fullName: localStorage.getItem('cg_username') || '',
    email: '',
    password: '',
    newPassword: '',
  });

  useEffect(() => {
    // Busca dados do Supabase se configurado
    const fetchUser = async () => {
      if (!isSupabaseConfigured) return;
      try {
        const { data: { user } } = await supabase.auth.getUser();
        if (user) {
          setFormData(prev => ({
            ...prev,
            email: user.email || '',
            fullName: user.user_metadata?.full_name || localStorage.getItem('cg_username') || ''
          }));
        }
      } catch (err) {
        console.error("Falha ao buscar usuário:", err);
      }
    };
    fetchUser();
  }, []);

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setSuccess('');

    try {
      if (isSupabaseConfigured) {
        const updates = {};
        if (formData.newPassword) updates.password = formData.newPassword;
        if (formData.fullName) updates.data = { full_name: formData.fullName };
        // Para mudar o email no Supabase, é necessário enviar verificação, faremos o request se alterado
        
        const { error: updateError } = await supabase.auth.updateUser(updates);
        
        if (updateError) throw updateError;
      }
      
      localStorage.setItem('cg_username', formData.fullName);
      
      setSuccess('Perfil atualizado com sucesso! Algumas alterações podem requerer um novo login.');
      setTimeout(() => setSuccess(''), 5000);
      setFormData(prev => ({ ...prev, password: '', newPassword: '' }));
    } catch (err) {
      setError(err.message || 'Erro ao atualizar o perfil. Verifique seus dados.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h2 className="text-3xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 to-teal-200 tracking-tight">Meu Perfil</h2>
          <p className="text-slate-400 mt-1">Gerencie suas informações pessoais e segurança da conta.</p>
        </div>
        <div className="hidden sm:flex items-center gap-2 bg-slate-800/50 px-4 py-2 rounded-full border border-slate-700/50 backdrop-blur-md">
          <Shield className="w-4 h-4 text-emerald-400" />
          <span className="text-sm font-medium text-slate-300 uppercase tracking-widest">{role}</span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Coluna da Esquerda - Avatar e Status */}
        <div className="lg:col-span-1 space-y-6">
          <div className="bg-slate-900/60 backdrop-blur-xl border border-slate-800 rounded-3xl p-6 shadow-2xl flex flex-col items-center text-center relative overflow-hidden group">
            <div className="absolute inset-0 bg-gradient-to-b from-emerald-500/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
            
            <div className="relative w-32 h-32 rounded-full bg-gradient-to-br from-slate-800 to-slate-900 border-4 border-slate-800 shadow-xl flex items-center justify-center mb-4 overflow-hidden group-hover:border-emerald-500/30 transition-colors duration-300">
              <span className="text-5xl font-bold text-transparent bg-clip-text bg-gradient-to-br from-emerald-400 to-teal-600">
                {formData.fullName ? formData.fullName.charAt(0).toUpperCase() : role.charAt(0).toUpperCase()}
              </span>
              <button
                aria-label="Alterar foto de perfil"
                className="absolute inset-0 bg-black/60 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-300"
              >
                <Camera className="w-8 h-8 text-white/80" />
              </button>
            </div>
            
            <h3 className="text-xl font-bold text-white mb-1">{formData.fullName || 'Usuário do Sistema'}</h3>
            <p className="text-emerald-400 text-sm font-medium mb-4">{formData.email || 'email@exemplo.com'}</p>
            
            <div className="w-full bg-slate-950/50 rounded-xl p-3 border border-slate-800/50 flex items-center justify-between">
              <span className="text-xs text-slate-400">Status da Conta</span>
              <span className="flex items-center gap-1.5 text-xs font-bold text-emerald-400">
                <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                Ativa
              </span>
            </div>

            <div className="w-full mt-4 bg-slate-950/50 rounded-xl p-4 border border-slate-800/50 text-left">
              <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                <Database size={14} /> Minhas Granjas
              </h4>
              {cameras.length > 0 ? (
                <ul className="space-y-2">
                  {cameras.map(cam => (
                    <li key={cam.camera_id} className="flex items-center justify-between text-sm bg-slate-900/50 px-3 py-2 rounded-lg border border-slate-800">
                      <span className="text-slate-300 font-medium truncate">{cam.name}</span>
                      <span className="text-[10px] bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded-full border border-emerald-500/20">{cam.status}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-slate-500 italic">Nenhuma granja vinculada.</p>
              )}
            </div>

          </div>
        </div>

        {/* Coluna da Direita - Formulário de Edição */}
        <div className="lg:col-span-2">
          <form onSubmit={handleSubmit} className="bg-slate-900/60 backdrop-blur-xl border border-slate-800 rounded-3xl p-6 sm:p-8 shadow-2xl relative">
            <div className="space-y-6">
              
              {/* Notificações */}
              {error && (
                <div className="bg-rose-500/10 border border-rose-500/20 text-rose-400 px-4 py-3 rounded-xl flex items-center gap-3 animate-in fade-in slide-in-from-top-2">
                  <AlertCircle className="w-5 h-5 shrink-0" />
                  <p className="text-sm">{error}</p>
                </div>
              )}
              {success && (
                <div className="bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 px-4 py-3 rounded-xl flex items-center gap-3 animate-in fade-in slide-in-from-top-2">
                  <CheckCircle className="w-5 h-5 shrink-0" />
                  <p className="text-sm">{success}</p>
                </div>
              )}

              {/* Informações Básicas */}
              <div>
                <h4 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                  <User className="w-5 h-5 text-emerald-500" />
                  Informações Pessoais
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                  <div className="space-y-1.5">
                    <label htmlFor="fullName" className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Nome Completo</label>
                    <div className="relative">
                      <input 
                        id="fullName"
                        name="fullName"
                        value={formData.fullName}
                        onChange={handleChange}
                        className="w-full bg-slate-950/50 border border-slate-700/50 rounded-xl pl-11 pr-4 py-3 text-sm text-slate-200 placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500/50 transition-all"
                        placeholder="Seu nome completo"
                      />
                      <User className="w-5 h-5 text-slate-500 absolute left-3.5 top-3" />
                    </div>
                  </div>
                  
                  <div className="space-y-1.5">
                    <label htmlFor="email" className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Endereço de E-mail</label>
                    <div className="relative">
                      <input 
                        id="email"
                        name="email"
                        value={formData.email}
                        onChange={handleChange}
                        type="email"
                        disabled={true} // Desabilitado para MVP, alterar email no supabase exige fluxo complexo
                        className="w-full bg-slate-950/30 border border-slate-800 rounded-xl pl-11 pr-4 py-3 text-sm text-slate-400 cursor-not-allowed"
                        placeholder="seu@email.com"
                      />
                      <Mail className="w-5 h-5 text-slate-600 absolute left-3.5 top-3" />
                    </div>
                  </div>
                </div>
              </div>

              <div className="h-px w-full bg-gradient-to-r from-transparent via-slate-700/50 to-transparent my-6" />

              {/* Segurança */}
              <div>
                <h4 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                  <Lock className="w-5 h-5 text-emerald-500" />
                  Segurança
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                  <div className="space-y-1.5">
                    <label htmlFor="newPassword" className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Nova Senha (Opcional)</label>
                    <div className="relative">
                      <input 
                        id="newPassword"
                        name="newPassword"
                        value={formData.newPassword}
                        onChange={handleChange}
                        type="password"
                        className="w-full bg-slate-950/50 border border-slate-700/50 rounded-xl pl-11 pr-4 py-3 text-sm text-slate-200 placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500/50 transition-all"
                        placeholder="••••••••"
                      />
                      <Lock className="w-5 h-5 text-slate-500 absolute left-3.5 top-3" />
                    </div>
                  </div>
                  
                  <div className="space-y-1.5">
                    <label htmlFor="confirmPassword" className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Confirmar Nova Senha</label>
                    <div className="relative">
                      <input 
                        id="confirmPassword"
                        type="password"
                        className="w-full bg-slate-950/50 border border-slate-700/50 rounded-xl pl-11 pr-4 py-3 text-sm text-slate-200 placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500/50 transition-all"
                        placeholder="••••••••"
                      />
                      <Shield className="w-5 h-5 text-slate-500 absolute left-3.5 top-3" />
                    </div>
                  </div>
                </div>
              </div>

              {/* Botões de Ação */}
              <div className="pt-6 mt-6 border-t border-slate-800/50 flex items-center justify-end gap-4">
                <button 
                  type="button" 
                  className="px-6 py-2.5 rounded-xl text-sm font-medium text-slate-300 hover:text-white hover:bg-slate-800 transition-colors"
                  onClick={() => window.location.reload()}
                >
                  Cancelar
                </button>
                <button 
                  type="submit" 
                  disabled={loading}
                  className="relative group overflow-hidden px-8 py-2.5 rounded-xl font-bold text-white bg-gradient-to-r from-emerald-600 to-teal-500 hover:from-emerald-500 hover:to-teal-400 shadow-lg shadow-emerald-500/20 transition-all disabled:opacity-70 disabled:cursor-not-allowed"
                >
                  <span className="relative z-10">{loading ? 'Salvando...' : 'Salvar Alterações'}</span>
                  <div className="absolute inset-0 h-full w-full bg-gradient-to-r from-transparent via-white/20 to-transparent -translate-x-full group-hover:animate-[shimmer_1.5s_infinite]" />
                </button>
              </div>

            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
