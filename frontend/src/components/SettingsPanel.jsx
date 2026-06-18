import React, { useState } from 'react';
import { Settings, Save, CheckCircle, RefreshCw, Plus } from 'lucide-react';
import { toast } from 'sonner';
import { DEFAULT_PREFS } from '../utils/config';

export default function SettingsPanel({ serverIP, prefs, onSavePrefs, onSaveServer, onRestartTour }) {
  const [serverDraft, setServerDraft] = useState(serverIP);
  const [draft, setDraft] = useState(prefs);
  const [saved, setSaved] = useState(false);
  const [isCreatingFarm, setIsCreatingFarm] = useState(false);

  const saveAll = () => {
    onSaveServer(serverDraft);
    onSavePrefs({
      statusMs: Number(draft.statusMs) || DEFAULT_PREFS.statusMs,
      historyMs: Number(draft.historyMs) || DEFAULT_PREFS.historyMs,
      devicesMs: Number(draft.devicesMs) || DEFAULT_PREFS.devicesMs,
      countMs: Number(draft.countMs) || DEFAULT_PREFS.countMs,
    });
    setSaved(true);
    toast.success('Configurações salvas com sucesso!');
    setTimeout(() => setSaved(false), 1600);
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 sm:p-8 max-w-4xl mx-auto shadow-sm backdrop-blur-sm">
      <div className="flex items-center gap-3 mb-2">
        <div className="bg-slate-800 p-2.5 rounded-xl border border-slate-700 shadow-inner">
          <Settings size={24} className="text-slate-300" />
        </div>
        <h2 className="text-2xl font-bold text-white tracking-tight">Configurações Avançadas</h2>
      </div>
      <p className="text-slate-400 text-sm mb-8 leading-relaxed ml-1">Ajuste os parâmetros de conexão com o backend e os intervalos de atualização dos painéis.</p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6">
        <div className="md:col-span-2">
          <Field label="Endereço do Servidor Backend" id="serverAddress" description="URL base da API (ex: http://192.168.1.100:5000 ou domínio).">
            <input
              id="serverAddress"
              value={serverDraft}
              onChange={(e) => setServerDraft(e.target.value)}
              className="w-full bg-slate-950/80 border border-slate-700 rounded-xl px-4 py-3 font-mono text-sm text-slate-200 focus:ring-2 focus:ring-emerald-500/50 outline-none transition-all placeholder:text-slate-600 shadow-inner"
              placeholder="http://127.0.0.1:5000"
            />
          </Field>
        </div>

        <Field label="Atualização de Status (ms)" id="statusMs" description="Intervalo de polling para temperatura, resumo geral, etc.">
          <input
            id="statusMs"
            type="number"
            value={draft.statusMs}
            onChange={(e) => setDraft((p) => ({ ...p, statusMs: e.target.value }))}
            className="w-full bg-slate-950/80 border border-slate-700 rounded-xl px-4 py-3 font-mono text-sm text-slate-200 focus:ring-2 focus:ring-emerald-500/50 outline-none transition-all shadow-inner"
            min="1000"
            step="500"
          />
        </Field>

        <Field label="Atualização do Histórico (ms)" id="historyMs" description="Frequência com que o gráfico e a tabela de histórico recarregam.">
          <input
            id="historyMs"
            type="number"
            value={draft.historyMs}
            onChange={(e) => setDraft((p) => ({ ...p, historyMs: e.target.value }))}
            className="w-full bg-slate-950/80 border border-slate-700 rounded-xl px-4 py-3 font-mono text-sm text-slate-200 focus:ring-2 focus:ring-emerald-500/50 outline-none transition-all shadow-inner"
            min="2000"
            step="1000"
          />
        </Field>

        <Field label="Atualização de Dispositivos (ms)" id="devicesMs" description="Polling para o estado dos relés (exaustores, aquecedores).">
          <input
            id="devicesMs"
            type="number"
            value={draft.devicesMs}
            onChange={(e) => setDraft((p) => ({ ...p, devicesMs: e.target.value }))}
            className="w-full bg-slate-950/80 border border-slate-700 rounded-xl px-4 py-3 font-mono text-sm text-slate-200 focus:ring-2 focus:ring-emerald-500/50 outline-none transition-all shadow-inner"
            min="1000"
            step="500"
          />
        </Field>

        <Field label="Atualização de Contagem (ms)" id="countMs" description="Polling para o número de aves detectadas pela IA no quadro.">
          <input
            id="countMs"
            type="number"
            value={draft.countMs}
            onChange={(e) => setDraft((p) => ({ ...p, countMs: e.target.value }))}
            className="w-full bg-slate-950/80 border border-slate-700 rounded-xl px-4 py-3 font-mono text-sm text-slate-200 focus:ring-2 focus:ring-emerald-500/50 outline-none transition-all shadow-inner"
            min="1000"
            step="500"
          />
        </Field>
      </div>

      <div className="mt-8 pt-6 border-t border-slate-800/80 flex flex-col sm:flex-row items-center justify-between gap-4">
        {saved ? (
          <div className="text-sm font-semibold text-emerald-400 bg-emerald-500/10 px-4 py-2.5 rounded-xl border border-emerald-500/20 flex items-center gap-2 w-full sm:w-auto justify-center transition-all animate-in zoom-in duration-200">
            <CheckCircle size={18} /> Salvo com sucesso!
          </div>
        ) : (
          <div className="text-sm font-medium text-slate-400 bg-slate-800/30 px-4 py-2.5 rounded-xl border border-slate-700/50 hidden sm:flex items-center">
            Pressione Salvar para aplicar
          </div>
        )}
        
        <div className="flex gap-3 w-full sm:w-auto">
          {onRestartTour && (
            <button
              onClick={onRestartTour}
              className="flex-1 sm:flex-none flex items-center justify-center gap-2 bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-400 font-semibold px-6 py-2.5 rounded-xl border border-indigo-500/20 hover:border-indigo-500/40 transition-all shadow-sm group"
            >
              Repetir Tutorial
            </button>
          )}
          <button
            onClick={saveAll}
            className="flex-1 sm:flex-none flex items-center justify-center gap-2 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold px-6 py-2.5 rounded-xl transition-all shadow-lg shadow-emerald-600/20 hover:shadow-emerald-500/30 transform hover:-translate-y-0.5"
          >
            <Save size={18} className="mr-1" /> Salvar Configurações
          </button>
        </div>
      </div>

      <div className="mt-12 pt-8 border-t border-slate-800">
        <h3 className="text-xl font-bold text-white mb-4">Adicionar Nova Granja</h3>
        <p className="text-slate-400 text-sm mb-6">Registre um novo galpão ou granja na sua conta para alternar facilmente no menu superior.</p>
        
        <form onSubmit={async (e) => {
          e.preventDefault();
          const nome = e.target.farmName.value;
          const url = e.target.cameraUrlNew.value;
          if (!nome) return;
          
          setIsCreatingFarm(true);
          try {
            const baseUrl = serverIP.replace(/\/$/, '');
            const finalUrl = baseUrl.startsWith('http') ? baseUrl : `http://${baseUrl}`;
            
            const payload = {
              camera_id: `granja-${Math.floor(Math.random() * 10000)}`,
              name: nome,
              connection_type: url.startsWith('rtsp') ? 'rtsp' : 'url',
              connection_url: url || ''
            };

            const res = await fetch(`${finalUrl}/api/cameras`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                Authorization: `Bearer ${localStorage.getItem('token')}`
              },
              body: JSON.stringify(payload)
            });

            if (res.ok) {
              e.target.reset();
              toast.success('Nova granja adicionada com sucesso! Atualize a página para vê-la no menu superior.');
            } else {
              toast.error('Falha ao adicionar a granja.');
            }
          } catch (err) {
            console.error(err);
            toast.error('Erro de conexão ao adicionar granja.');
          } finally {
            setIsCreatingFarm(false);
          }
        }} className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Field label="Nome da Nova Granja" id="farmName" description="Ex: Galpão Sul 2">
            <input
              id="farmName"
              name="farmName"
              required
              className="w-full bg-slate-950/80 border border-slate-700 rounded-xl px-4 py-3 font-mono text-sm text-slate-200 focus:ring-2 focus:ring-emerald-500/50 outline-none transition-all shadow-inner"
              placeholder="Digite o nome..."
            />
          </Field>
          <Field label="URL da Câmera (Opcional)" id="cameraUrlNew" description="URL HTTP/MJPEG ou RTSP">
            <input
              id="cameraUrlNew"
              name="cameraUrlNew"
              className="w-full bg-slate-950/80 border border-slate-700 rounded-xl px-4 py-3 font-mono text-sm text-slate-200 focus:ring-2 focus:ring-emerald-500/50 outline-none transition-all shadow-inner"
              placeholder="http://..."
            />
          </Field>
          <div className="md:col-span-2 flex justify-end mt-2">
            <button disabled={isCreatingFarm} type="submit" className="bg-slate-800 hover:bg-slate-700 text-white font-bold py-2.5 px-6 rounded-xl border border-slate-700 transition-all flex items-center gap-2 hover:-translate-y-0.5 shadow-sm disabled:opacity-50 disabled:hover:translate-y-0 disabled:cursor-not-allowed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900">
              {isCreatingFarm ? <RefreshCw size={18} className="animate-spin" /> : <Plus size={18} />}
              {isCreatingFarm ? 'Criando...' : 'Criar Nova Granja'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function Field({ label, id, description, children }) {
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-sm font-bold text-slate-200 tracking-wide">{label}</label>
      {description && <span className="text-xs text-slate-500 mb-1">{description}</span>}
      {children}
    </div>
  );
}
