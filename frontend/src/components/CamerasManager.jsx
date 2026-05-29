import React, { useState, useEffect } from 'react';
import { Camera, Plus, Trash2, Edit2, PlayCircle, RefreshCw } from 'lucide-react';

export default function CamerasManager({ serverIP, token }) {
  const [cameras, setCameras] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [formData, setFormData] = useState({ camera_id: '', name: '', connection_type: 'url', connection_url: '' });
  const [editingId, setEditingId] = useState(null);

  const fetchCameras = async () => {
    try {
      setLoading(true);
      const res = await fetch(`${serverIP}/api/cameras`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setCameras(data.items);
      }
    } catch (err) {
      console.error("Failed to load cameras", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCameras();
  }, [serverIP, token]);

  const handleSubmit = async (e) => {
    e.preventDefault();
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
      } else {
        const err = await res.json();
        alert(err.msg || "Erro ao salvar");
      }
    } catch (err) {
      alert("Erro de conexão");
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Deseja realmente excluir esta câmera?")) return;
    try {
      const res = await fetch(`${serverIP}/api/cameras/${id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        fetchCameras();
      }
    } catch (err) {
      console.error(err);
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
            Gestão de Câmeras Cloud
          </h2>
          <p className="text-slate-400 text-sm mt-1">Conecte múltiplas granjas via RTSP/IP.</p>
        </div>
        <button 
          onClick={() => { setEditingId(null); setFormData({ camera_id: '', name: '', connection_type: 'url', connection_url: '' }); setShowModal(true); }}
          className="bg-emerald-500 hover:bg-emerald-600 text-white px-4 py-2 rounded-lg flex items-center gap-2 transition-all shadow-lg shadow-emerald-500/20"
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
            {loading ? (
              <tr>
                <td colSpan="5" className="p-8 text-center text-slate-400">
                  <RefreshCw className="animate-spin inline-block mr-2" size={18} /> Carregando...
                </td>
              </tr>
            ) : cameras.length === 0 ? (
              <tr>
                <td colSpan="5" className="p-8 text-center text-slate-400">
                  Nenhuma câmera conectada.
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
                    <button onClick={() => openEdit(cam)} className="p-2 text-blue-400 hover:bg-blue-400/10 rounded transition-colors"><Edit2 size={16} /></button>
                    <button onClick={() => handleDelete(cam.id)} className="p-2 text-rose-400 hover:bg-rose-400/10 rounded transition-colors"><Trash2 size={16} /></button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {showModal && (
        <div className="fixed inset-0 bg-slate-900/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-slate-800 rounded-xl p-6 w-full max-w-md border border-slate-700 shadow-2xl">
            <h3 className="text-xl font-bold text-white mb-4">{editingId ? 'Editar Câmera' : 'Adicionar Câmera'}</h3>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-slate-400 text-sm mb-1">ID Único (Ex: galpao-1)</label>
                <input required type="text" value={formData.camera_id} onChange={e => setFormData({...formData, camera_id: e.target.value})} disabled={!!editingId} className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-emerald-500 disabled:opacity-50" />
              </div>
              <div>
                <label className="block text-slate-400 text-sm mb-1">Nome de Exibição (Ex: Granja Norte)</label>
                <input required type="text" value={formData.name} onChange={e => setFormData({...formData, name: e.target.value})} className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-emerald-500" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-slate-400 text-sm mb-1">Tipo</label>
                  <select value={formData.connection_type} onChange={e => setFormData({...formData, connection_type: e.target.value})} className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-emerald-500">
                    <option value="url">URL de Vídeo</option>
                    <option value="rtsp">RTSP (Câmera IP)</option>
                    <option value="usb">USB Local</option>
                  </select>
                </div>
                <div className="col-span-2">
                  <label className="block text-slate-400 text-sm mb-1">Link/URL de Conexão</label>
                  <input type="text" value={formData.connection_url} onChange={e => setFormData({...formData, connection_url: e.target.value})} placeholder="rtsp://admin:pass@ip:554/stream" className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-emerald-500" />
                </div>
              </div>
              <div className="flex justify-end gap-3 mt-6">
                <button type="button" onClick={() => setShowModal(false)} className="px-4 py-2 text-slate-400 hover:text-white transition-colors">Cancelar</button>
                <button type="submit" className="bg-emerald-500 hover:bg-emerald-600 text-white px-6 py-2 rounded-lg font-medium transition-colors">Salvar Câmera</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
