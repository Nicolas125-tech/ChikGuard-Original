import React, { useEffect, useState } from 'react';

export default function AdminPanel({ token, serverIP }) {
  const [pendingUsers, setPendingUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchPendingUsers = async () => {
    setLoading(true);
    try {
      const res = await fetch(`http://${serverIP}:5000/api/admin/pending-users`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (res.ok) {
        const d = await res.json();
        setPendingUsers(d.items || []);
      } else {
        const d = await res.json();
        setError(`Erro: ${d.msg || 'Desconhecido'}`);
      }
      setLoading(false);
    } catch (e) {
      console.error(e);
      setError('Acesso negado ou erro no servidor.');
      setLoading(false);
    }
  };

  useEffect(() => {
    setTimeout(fetchPendingUsers, 0);
  }, [token, serverIP]);

  const handleApprove = async (userId, targetRole) => {
    const confirmApproval = window.confirm(`Aprovar utilizador como ${targetRole}?`);
    if (!confirmApproval) return;

    try {
      const res = await fetch(`http://${serverIP}:5000/api/admin/approve-user`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ target_user_id: userId, target_role: targetRole })
      });

      if (!res.ok) {
        const d = await res.json();
        alert(`Erro ao aprovar: ${d.msg || d.error || 'Desconhecido'}`);
        return;
      }
      alert('Utilizador aprovado com sucesso!');
      setPendingUsers(pendingUsers.filter((user) => user.id !== userId));
    } catch (e) {
      alert(`Erro de rede: ${e.message}`);
    }
  };

  if (loading) return <p className="text-emerald-500 p-6">A carregar painel admin...</p>;
  if (error) return <p className="text-red-500 p-6">{error}</p>;

  return (
    <div className="bg-slate-900 text-white rounded-lg min-h-full">
      <h2 className="text-2xl text-emerald-500 font-bold mb-6">Aprovação de Contas IAM</h2>

      {pendingUsers.length === 0 ? (
        <p>Não há utilizadores aguardando aprovação.</p>
      ) : (
        <table className="min-w-full bg-slate-950 rounded overflow-hidden shadow-lg border border-slate-700">
          <thead className="bg-slate-800 text-emerald-500">
            <tr>
              <th className="py-3 px-4 text-left">Email / Usuário</th>
              <th className="py-3 px-4 text-left">ID (UUID)</th>
              <th className="py-3 px-4 text-left">Data de Criação</th>
              <th className="py-3 px-4 text-left">Ação</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800">
            {pendingUsers.map((user) => (
              <tr key={user.id} className="hover:bg-slate-800 transition-colors">
                <td className="py-4 px-4">{user.email}</td>
                <td className="py-4 px-4 font-mono text-slate-400 text-sm">{user.id.substring(0, 13)}...</td>
                <td className="py-4 px-4">{new Date(user.created_at).toLocaleDateString()}</td>
                <td className="py-4 px-4 flex gap-2 items-center">
                  <select
                    id={`role-${user.id}`}
                    className="bg-slate-900 border border-slate-600 rounded px-2 py-2 text-white outline-none"
                    defaultValue="VIEWER"
                  >
                    <option value="VIEWER">VIEWER</option>
                    <option value="OPERATOR">OPERATOR</option>
                    <option value="FARM_ADMIN">FARM_ADMIN</option>
                    <option value="SUPERADMIN">SUPERADMIN</option>
                  </select>
                  <button
                    onClick={() => {
                      const selectElement = document.getElementById(`role-${user.id}`);
                      if (selectElement) {
                        handleApprove(user.id, selectElement.value);
                      }
                    }}
                    className="bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-2 px-4 rounded"
                  >
                    Aprovar
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
