import React, { useState } from 'react';
import { Settings, Save, CheckCircle } from 'lucide-react';
import { DEFAULT_PREFS } from '../utils/config';

export default function SettingsPanel({ serverIP, prefs, onSavePrefs, onSaveServer }) {
  const [serverDraft, setServerDraft] = useState(serverIP);
  const [draft, setDraft] = useState(prefs);
  const [saved, setSaved] = useState(false);

  const saveAll = () => {
    onSaveServer(serverDraft);
    onSavePrefs({
      statusMs: Number(draft.statusMs) || DEFAULT_PREFS.statusMs,
      historyMs: Number(draft.historyMs) || DEFAULT_PREFS.historyMs,
      devicesMs: Number(draft.devicesMs) || DEFAULT_PREFS.devicesMs,
      countMs: Number(draft.countMs) || DEFAULT_PREFS.countMs,
    });
    setSaved(true);
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
          <Field label="Endereço do Servidor Backend" description="URL base da API (ex: http://192.168.1.100:5000 ou domínio).">
            <input
              value={serverDraft}
              onChange={(e) => setServerDraft(e.target.value)}
              className="w-full bg-slate-950/80 border border-slate-700 rounded-xl px-4 py-3 font-mono text-sm text-slate-200 focus:ring-2 focus:ring-emerald-500/50 outline-none transition-all placeholder:text-slate-600 shadow-inner"
              placeholder="http://127.0.0.1:5000"
            />
          </Field>
        </div>

        <Field label="Atualização de Status (ms)" description="Intervalo de polling para temperatura, resumo geral, etc.">
          <input
            type="number"
            value={draft.statusMs}
            onChange={(e) => setDraft((p) => ({ ...p, statusMs: e.target.value }))}
            className="w-full bg-slate-950/80 border border-slate-700 rounded-xl px-4 py-3 font-mono text-sm text-slate-200 focus:ring-2 focus:ring-emerald-500/50 outline-none transition-all shadow-inner"
            min="1000"
            step="500"
          />
        </Field>

        <Field label="Atualização do Histórico (ms)" description="Frequência com que o gráfico e a tabela de histórico recarregam.">
          <input
            type="number"
            value={draft.historyMs}
            onChange={(e) => setDraft((p) => ({ ...p, historyMs: e.target.value }))}
            className="w-full bg-slate-950/80 border border-slate-700 rounded-xl px-4 py-3 font-mono text-sm text-slate-200 focus:ring-2 focus:ring-emerald-500/50 outline-none transition-all shadow-inner"
            min="2000"
            step="1000"
          />
        </Field>

        <Field label="Atualização de Dispositivos (ms)" description="Polling para o estado dos relés (exaustores, aquecedores).">
          <input
            type="number"
            value={draft.devicesMs}
            onChange={(e) => setDraft((p) => ({ ...p, devicesMs: e.target.value }))}
            className="w-full bg-slate-950/80 border border-slate-700 rounded-xl px-4 py-3 font-mono text-sm text-slate-200 focus:ring-2 focus:ring-emerald-500/50 outline-none transition-all shadow-inner"
            min="1000"
            step="500"
          />
        </Field>

        <Field label="Atualização de Contagem (ms)" description="Polling para o número de aves detectadas pela IA no quadro.">
          <input
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
          <div className="text-sm text-slate-500 hidden sm:block">Recomendamos manter os intervalos acima de 3000ms.</div>
        )}

        <button
          onClick={saveAll}
          className="w-full sm:w-auto bg-emerald-600 hover:bg-emerald-500 text-white font-bold px-8 py-3.5 rounded-xl flex items-center justify-center gap-2 shadow-lg shadow-emerald-500/20 transition-all hover:-translate-y-0.5"
        >
          <Save size={18} />
          Salvar Configurações
        </button>
      </div>
    </div>
  );
}

function Field({ label, description, children }) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-sm font-bold text-slate-200 tracking-wide">{label}</label>
      {description && <span className="text-xs text-slate-500 mb-1">{description}</span>}
      {children}
    </div>
  );
}
