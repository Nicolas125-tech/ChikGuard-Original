import React, { useState, useEffect, useCallback } from 'react';
import { Camera, Plus, Trash2, Edit2, PlayCircle, RefreshCw } from 'lucide-react';
import { toast } from 'sonner';
import QueryErrorState from './QueryErrorState';

export default function CamerasManager({ serverIP, token }) {
  const [cameras, setCameras] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [formData, setFormData] = useState({ camera_id: '', name: '', connection_type: 'url', connection_url: '' });
  const [editingId, setEditingId] = useState(null);
  const [isSaving, setIsSaving] = useState(false);
  const [deletingId, setDeletingId] = useState(null);

  // Close modal on escape key
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && showModal) {
        setShowModal(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [showModal]);

  const fetchCameras = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetch(`${serverIP}/api/cameras`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (!res.ok) throw new Error('Não foi possível carregar a lista de granjas.');
      const data = await res.json();
      setCameras(data.items);
    } catch (err) {
      console.error(err);
      setError(err.message || 'Erro ao carregar granjas.');
    } finally {
      setLoading(false);
    }
  }, [serverIP, token]);

  useEffect(() => {
    (async () => { fetchCameras(); })();
  }, [serverIP, token, fetchCameras]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSaving(true);
    const method = editingId ? 'PUT' : 'POST';
    const url = editingId ? `${serverIP}/api/cameras/${editingId}` : `${serverIP}/api/cameras`;
    
    try {
      const res = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify(formData)
      });
      
      if (res.ok) {
        setShowModal(false);
        setFormData({ camera_id: '', name: '', connection_type: 'url', connection_url: '' });
        setEditingId(null);
        fetchCameras();
        toast.success(editingId ? "Câmera editada com sucesso" : "Câmera adicionada com sucesso");
      } else {
        const err = await res.json();
        toast.error(err.msg || "Erro ao salvar");
      }
    } catch (err) {
      console.error(err);
      toast.error("Erro de conexão");
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Deseja realmente excluir esta câmera?")) return;
    setDeletingId(id);
    try {
      const res = await fetch(`${serverIP}/api/cameras/${id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        fetchCameras();
        toast.success("Câmera excluída");
      } else {
        toast.error("Erro ao excluir câmera");
      }
    } catch (err) { console.error(err);
      toast.error("Erro ao conectar");
    } finally {
      setDeletingId(null);
    }
  };

  const openEdit = (cam) => {
    setFormData({ camera_id: cam.camera_id, name: cam.name, connection_type: cam.connection_type, connection_url: cam.connection_url });
    setEditingId(cam.id);
    setShowModal(true);
  };

  return (
    <div className="bg-slate-800 p-6 rounded-xl border border-slate-700/50 shadow-2xl">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-2xl font-bold text-white flex items-center gap-2">
            <Camera className="text-emerald-400" />
            Gestão de Granjas e Câmeras
          </h2>
          <p className="text-slate-400 text-sm mt-1">Conecte múltiplas granjas via RTSP/IP para gerenciar diferentes lotes.</p>
        </div>
        <button 
          onClick={() => { setEditingId(null); setFormData({ camera_id: '', name: '', connection_type: 'url', connection_url: '' }); setShowModal(true); }}
          className="bg-emerald-500 hover:bg-emerald-600 text-white px-4 py-2 rounded-lg flex items-center gap-2 transition-all shadow-lg shadow-emerald-500/20 focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900 focus:outline-none"
        >
          <Plus size={18} /> Nova Câmera
        </button>
      </div>

      <div className="bg-slate-900 rounded-lg overflow-hidden border border-slate-700">
        <table className="w-full text-left">
          <thead className="bg-slate-800 border-b border-slate-700 text-slate-300">
            <tr>
              <th className="p-4 font-semibold">ID</th>
              <th className="p-4 font-semibold">Nome</th>
              <th className="p-4 font-semibold">Conexão</th>
              <th className="p-4 font-semibold">Status</th>
              <th className="p-4 font-semibold">Ações</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800">
            {error ? (
              <tr>
                <td colSpan="5" className="p-8 text-center text-slate-400">
                  <QueryErrorState message={error} onRetry={fetchCameras} />
                </td>
              </tr>
            ) : loading ? (
              <tr>
                <td colSpan="5" className="p-8 text-center text-slate-400">
                  <RefreshCw className="animate-spin inline-block mr-2" size={18} /> Carregando...
                </td>
              </tr>
            ) : cameras.length === 0 ? (
              <tr>
                <td colSpan="5" className="p-12">
                  <div className="flex flex-col items-center justify-center text-center">
                    <div className="bg-slate-800/50 p-5 rounded-full mb-4 border border-slate-700/50 shadow-inner">
                      <Camera size={32} className="text-slate-500" />
                    </div>
                    <h3 className="text-lg font-bold text-slate-200 mb-2 tracking-tight">Nenhuma câmera configurada</h3>
                    <p className="text-slate-400 max-w-md mx-auto mb-6 text-sm leading-relaxed">
                      Adicione sua primeira câmera IP (RTSP), link de vídeo ou câmera USB para iniciar o monitoramento inteligente por IA.
                    </p>
                    <button 
                      onClick={() => { setEditingId(null); setFormData({ camera_id: '', name: '', connection_type: 'url', connection_url: '' }); setShowModal(true); }}
                      className="bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/20 px-5 py-2.5 rounded-lg flex items-center gap-2 transition-all font-semibold shadow-sm focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900 focus:outline-none"
                    >
                      <Plus size={18} /> Cadastrar Primeira Câmera
                    </button>
                  </div>
                </td>
              </tr>
            ) : (
              cameras.map(cam => (
                <tr key={cam.id} className="hover:bg-slate-800/50 transition-colors">
                  <td className="p-4 text-slate-300 font-mono text-sm">{cam.camera_id}</td>
                  <td className="p-4 text-white font-medium">{cam.name}</td>
                  <td className="p-4">
                    <span className="bg-slate-800 text-slate-300 px-2 py-1 rounded text-xs border border-slate-600 flex items-center w-max gap-1">
                      <PlayCircle size={12} /> {cam.connection_type.toUpperCase()}
                    </span>
                  </td>
                  <td className="p-4">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium border ${cam.status === 'online' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 'bg-rose-500/10 text-rose-400 border-rose-500/20'}`}>
                      {cam.status.toUpperCase()}
                    </span>
                  </td>
                  <td className="p-4 flex gap-2">
                    <button aria-label={`Editar câmera ${cam.name}`} onClick={() => openEdit(cam)} className="p-2 text-blue-400 hover:bg-blue-400/10 rounded transition-colors focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900 focus:outline-none" title="Editar">
                      <Edit2 size={16} aria-hidden="true" />
                    </button>
                    <button aria-label={`Excluir câmera ${cam.name}`} disabled={deletingId === cam.id} onClick={() => handleDelete(cam.id)} className="p-2 text-rose-400 hover:bg-rose-400/10 rounded transition-colors focus-visible:ring-2 focus-visible:ring-rose-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900 focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed" title="Excluir">
                      {deletingId === cam.id ? <RefreshCw size={16} className="animate-spin" aria-hidden="true" /> : <Trash2 size={16} aria-hidden="true" />}
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {showModal && (
        <div
          className="fixed inset-0 bg-slate-900/80 backdrop-blur-sm flex items-center justify-center z-50 p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="modal-title"
        >
          <div className="bg-slate-800 rounded-xl p-6 w-full max-w-md border border-slate-700 shadow-2xl">
            <h3 id="modal-title" className="text-xl font-bold text-white mb-4">{editingId ? 'Editar Câmera' : 'Adicionar Câmera'}</h3>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label htmlFor="camera_id" className="block text-slate-400 text-sm mb-1">ID Único (Ex: galpao-1) <span className="text-red-500">*</span></label>
                <input id="camera_id" required type="text" value={formData.camera_id} onChange={e => setFormData({...formData, camera_id: e.target.value})} disabled={!!editingId} className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-emerald-500 disabled:opacity-50" />
              </div>
              <div>
                <label htmlFor="name" className="block text-slate-400 text-sm mb-1">Nome de Exibição (Ex: Granja Norte) <span className="text-red-500">*</span></label>
                <input id="name" required type="text" value={formData.name} onChange={e => setFormData({...formData, name: e.target.value})} className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-emerald-500" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label htmlFor="connection_type" className="block text-slate-400 text-sm mb-1">Tipo</label>
                  <select id="connection_type" value={formData.connection_type} onChange={e => setFormData({...formData, connection_type: e.target.value})} className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-emerald-500">
                    <option value="url">URL de Vídeo</option>
                    <option value="rtsp">RTSP (Câmera IP)</option>
                    <option value="usb">USB Local</option>
                  </select>
                </div>
                <div className="col-span-2">
                  <label htmlFor="connection_url" className="block text-slate-400 text-sm mb-1">Link/URL de Conexão</label>
                  <input id="connection_url" type="text" value={formData.connection_url} onChange={e => setFormData({...formData, connection_url: e.target.value})} placeholder="rtsp://admin:pass@ip:554/stream" className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-emerald-500" />
                </div>
              </div>
              <div className="flex justify-end gap-3 mt-6">
                <button aria-label="Cancelar edição de câmera" type="button" onClick={() => setShowModal(false)} className="px-4 py-2 text-slate-400 hover:text-white transition-colors focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900 focus:outline-none">Cancelar</button>
                <button type="submit" disabled={isSaving} className="bg-emerald-500 hover:bg-emerald-600 text-white px-6 py-2 rounded-lg font-medium transition-colors focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900 focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2">
                  {isSaving && <RefreshCw size={16} aria-hidden="true" className="animate-spin" />}
                  {isSaving ? 'Salvando...' : 'Salvar Câmera'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
