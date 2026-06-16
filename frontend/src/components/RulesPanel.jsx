import React, { useState, useEffect } from 'react';
import { getBaseUrl } from '../utils/config';
import { ServerCog, Plus, Trash2, ShieldCheck, Thermometer } from 'lucide-react';
import { toast } from 'sonner';

export default function RulesPanel({ serverIP }) {
  const [rules, setRules] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // Form state
  const [name, setName] = useState('');
  const [variable, setVariable] = useState('temp_c');
  const [operator, setOperator] = useState('>');
  const [value, setValue] = useState('');
  const [device, setDevice] = useState('exhaust_fan');
  const [state, setState] = useState('on');

  useEffect(() => {
    const fetchRules = async () => {
      setLoading(true);
      try {
        const res = await fetch(`${getBaseUrl(serverIP)}/api/rules`);
        if (res.ok) {
          const data = await res.json();
          setRules(data);
        }
      } catch (err) {
        console.error('Failed to fetch rules', err);
      } finally {
        setLoading(false);
      }
    };
    fetchRules();
  }, [serverIP]);

  const reloadRules = async () => {
    try {
      const res = await fetch(`${getBaseUrl(serverIP)}/api/rules`);
      if (res.ok) {
        const data = await res.json();
        setRules(data);
      }
    } catch (err) {
      console.error('Failed to reload rules', err);
    }
  };

  const handleAddRule = async (e) => {
    e.preventDefault();
    if (!name || !value) {
      toast.error('Preencha os campos obrigatórios');
      return;
    }

    try {
      const res = await fetch(`${getBaseUrl(serverIP)}/api/rules`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name,
          condition_variable: variable,
          condition_operator: operator,
          condition_value: parseFloat(value),
          action_device: device,
          action_state: state
        })
      });

      if (res.ok) {
        toast.success('Regra criada com sucesso!');
        setName('');
        setValue('');
        reloadRules();
      } else {
        toast.error('Erro ao criar regra');
      }
    } catch (err) {
      console.error(err);
      toast.error('Falha de conexão');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Excluir esta regra?')) return;
    try {
      const res = await fetch(`${getBaseUrl(serverIP)}/api/rules/${id}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        toast.success('Regra removida!');
        reloadRules();
      }
    } catch (err) {
      console.error(err);
      toast.error('Falha de conexão');
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 sm:p-8 shadow-sm backdrop-blur-sm">
      <div className="flex items-center gap-3 mb-2">
        <div className="bg-indigo-500/20 p-2.5 rounded-xl border border-indigo-500/30">
          <ServerCog size={24} className="text-indigo-400" />
        </div>
        <h2 className="text-2xl font-bold text-white tracking-tight">Motor de Regras (No-Code)</h2>
      </div>
      <p className="text-slate-400 text-sm mb-8 leading-relaxed ml-1">
        Crie lógicas de automação customizadas para que o ChikGuard tome decisões sozinho com base nos sensores.
      </p>

      {/* Form Section */}
      <div className="bg-slate-950/50 p-6 rounded-2xl border border-slate-800 mb-8">
        <h3 className="text-lg font-semibold text-slate-200 mb-4 flex items-center gap-2">
          <Plus size={18} className="text-emerald-400" /> Nova Regra
        </h3>
        <form onSubmit={handleAddRule} className="grid grid-cols-1 md:grid-cols-6 gap-4 items-end">
          <div className="md:col-span-2">
            <label className="block text-xs font-medium text-slate-400 mb-1">Nome da Regra</label>
            <input 
              value={name} onChange={(e) => setName(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 outline-none focus:border-indigo-500" 
              placeholder="Ex: Ligar Ventilação Calor"
            />
          </div>
          
          <div className="md:col-span-4 grid grid-cols-5 gap-2 bg-slate-800/30 p-3 rounded-xl border border-slate-700/50">
            <div className="col-span-1">
              <label className="block text-[10px] font-medium text-slate-400 mb-1 uppercase tracking-wider">SE</label>
              <select value={variable} onChange={(e) => setVariable(e.target.value)} className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2 py-2 text-sm text-slate-200 outline-none">
                <option value="temp_c">Temperatura</option>
                <option value="humidity_pct">Umidade</option>
                <option value="ammonia_ppm">Amônia</option>
              </select>
            </div>
            
            <div className="col-span-1">
              <label className="block text-[10px] font-medium text-slate-400 mb-1 uppercase tracking-wider">FOR</label>
              <select value={operator} onChange={(e) => setOperator(e.target.value)} className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2 py-2 text-sm text-slate-200 outline-none">
                <option value=">">Maior que</option>
                <option value="<">Menor que</option>
                <option value="==">Igual a</option>
              </select>
            </div>
            
            <div className="col-span-1">
              <label className="block text-[10px] font-medium text-slate-400 mb-1 uppercase tracking-wider">VALOR</label>
              <input 
                type="number" step="0.1" value={value} onChange={(e) => setValue(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2 py-2 text-sm text-slate-200 outline-none text-center" 
                placeholder="Ex: 30.5"
              />
            </div>
            
            <div className="col-span-1">
              <label className="block text-[10px] font-medium text-slate-400 mb-1 uppercase tracking-wider">ENTÃO</label>
              <select value={device} onChange={(e) => setDevice(e.target.value)} className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2 py-2 text-sm text-slate-200 outline-none">
                <option value="exhaust_fan">Ventilador</option>
                <option value="heater">Aquecedor</option>
              </select>
            </div>
            
            <div className="col-span-1">
              <label className="block text-[10px] font-medium text-slate-400 mb-1 uppercase tracking-wider">AÇÃO</label>
              <select value={state} onChange={(e) => setState(e.target.value)} className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2 py-2 text-sm text-slate-200 outline-none">
                <option value="on">LIGAR</option>
                <option value="off">DESLIGAR</option>
              </select>
            </div>
          </div>

          <div className="md:col-span-6 flex justify-end mt-2">
            <button type="submit" className="bg-indigo-600 hover:bg-indigo-500 text-white font-medium py-2 px-6 rounded-lg shadow-lg shadow-indigo-900/20 transition-all flex items-center gap-2">
              <ShieldCheck size={18} />
              Salvar Regra
            </button>
          </div>
        </form>
      </div>

      {/* Rules List */}
      <div>
        <h3 className="text-lg font-semibold text-slate-200 mb-4 flex items-center gap-2">
          <Thermometer size={18} className="text-blue-400" /> Regras Ativas
        </h3>
        {loading ? (
          <div className="text-center py-8 text-slate-500 animate-pulse">Carregando regras...</div>
        ) : rules.length === 0 ? (
          <div className="text-center py-10 bg-slate-950/30 rounded-xl border border-slate-800/50">
            <ServerCog size={32} className="mx-auto text-slate-600 mb-3" />
            <p className="text-slate-400">Nenhuma regra de automação configurada.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {rules.map((r) => (
              <div key={r.id} className="flex flex-col sm:flex-row sm:items-center justify-between p-4 bg-slate-800/40 border border-slate-700/50 rounded-xl hover:bg-slate-800/60 transition-colors">
                <div>
                  <h4 className="text-slate-200 font-medium">{r.name}</h4>
                  <div className="flex flex-wrap gap-2 mt-2 text-xs">
                    <span className="bg-slate-900 px-2 py-1 rounded border border-slate-700 text-slate-300">
                      SE <b className="text-blue-400">{r.condition_variable}</b>
                    </span>
                    <span className="bg-slate-900 px-2 py-1 rounded border border-slate-700 text-emerald-400 font-bold">
                      {r.condition_operator} {r.condition_value}
                    </span>
                    <span className="bg-slate-900 px-2 py-1 rounded border border-slate-700 text-slate-300">
                      ENTÃO <b className="text-amber-400">{r.action_device}</b> = <b className={r.action_state === 'on' ? 'text-emerald-400' : 'text-rose-400'}>{r.action_state.toUpperCase()}</b>
                    </span>
                  </div>
                </div>
                <button 
                  aria-label="Excluir regra"
                  onClick={() => handleDelete(r.id)}
                  className="mt-3 sm:mt-0 p-2 text-slate-500 hover:text-rose-400 hover:bg-rose-400/10 rounded-lg transition-colors focus-visible:ring-2 focus-visible:ring-rose-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900 focus:outline-none"
                  title="Excluir"
                >
                  <Trash2 size={18} aria-hidden="true" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
