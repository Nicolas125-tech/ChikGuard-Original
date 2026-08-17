import React, { useState, useEffect } from 'react';
import { FileText, Download, QrCode, ShieldCheck, Activity, Thermometer, Droplets, Medal } from 'lucide-react';
import { getBaseUrl } from '../utils/config';

export default function BatchPassport({ token, serverIP }) {
  const [passport, setPassport] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchPassport() {
      try {
        const res = await fetch(`${getBaseUrl(serverIP)}/api/reports/passport`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          setPassport(data);
        }
      } catch (e) {
        console.error("Failed to fetch passport", e);
      } finally {
        setLoading(false);
      }
    }
    fetchPassport();
  }, [token, serverIP]);

  if (loading) return <div className="p-8 text-center text-slate-400 animate-pulse">Gerando passaporte...</div>;
  if (!passport) return <div className="p-8 text-center text-rose-400">Falha ao carregar o passaporte.</div>;

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-3xl p-8 shadow-xl max-w-4xl mx-auto my-6" id="passport-container">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center border-b border-slate-800 pb-6 mb-6">
        <div className="flex items-center gap-4">
          <div className="bg-indigo-500/20 p-3 rounded-2xl border border-indigo-500/30">
            <Medal size={32} className="text-indigo-400" />
          </div>
          <div>
            <h1 className="text-2xl font-black text-white uppercase tracking-wider">Passaporte de Rastreabilidade</h1>
            <p className="text-slate-400 font-medium">ChikGuard Analytics &bull; Certificado de Qualidade</p>
          </div>
        </div>
        <div className="mt-4 md:mt-0 flex flex-col items-end">
          <span className="text-xs text-slate-500 uppercase font-bold tracking-widest">ID do Documento</span>
          <span className="text-lg font-mono font-bold text-slate-200 bg-slate-950 px-3 py-1 rounded border border-slate-800 mt-1">{passport.passport_id}</span>
        </div>
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        
        {/* Left Col: Info */}
        <div className="md:col-span-2 space-y-6">
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-slate-950/50 p-4 rounded-xl border border-slate-800/50">
              <span className="text-xs text-slate-500 uppercase font-bold block mb-1">Lote / Granja</span>
              <span className="text-lg font-bold text-white">{passport.batch_name}</span>
            </div>
            <div className="bg-slate-950/50 p-4 rounded-xl border border-slate-800/50">
              <span className="text-xs text-slate-500 uppercase font-bold block mb-1">Data de Início</span>
              <span className="text-lg font-bold text-white">{passport.start_date} ({passport.current_age_days} dias)</span>
            </div>
            <div className="bg-slate-950/50 p-4 rounded-xl border border-slate-800/50">
              <span className="text-xs text-slate-500 uppercase font-bold block mb-1">Plantel Inicial</span>
              <span className="text-lg font-bold text-white">{passport.initial_count.toLocaleString()} aves</span>
            </div>
            <div className="bg-slate-950/50 p-4 rounded-xl border border-slate-800/50">
              <span className="text-xs text-slate-500 uppercase font-bold block mb-1">Taxa de Mortalidade</span>
              <span className={`text-lg font-bold ${passport.mortality_rate < 3 ? 'text-emerald-400' : 'text-rose-400'}`}>
                {passport.mortality_rate}%
              </span>
            </div>
          </div>

          <div>
            <h3 className="text-sm font-bold text-slate-300 uppercase mb-3 flex items-center gap-2">
              <Activity size={16} className="text-indigo-400"/> Indicadores de Bem-Estar (Média da Vida)
            </h3>
            <div className="bg-slate-950 rounded-xl border border-slate-800 p-4 space-y-3">
               <div className="flex justify-between items-center">
                 <span className="text-slate-400 flex items-center gap-2"><Thermometer size={14}/> Temperatura Média</span>
                 <span className="text-white font-bold">{passport.avg_temperature}°C</span>
               </div>
               <div className="w-full h-px bg-slate-800/50"></div>
               <div className="flex justify-between items-center">
                 <span className="text-slate-400 flex items-center gap-2"><ShieldCheck size={14}/> Eventos de Estresse</span>
                 <span className="text-white font-bold">{passport.stress_events} alertas registrados</span>
               </div>
               <div className="w-full h-px bg-slate-800/50"></div>
               <div className="flex justify-between items-center">
                 <span className="text-slate-400 flex items-center gap-2"><Droplets size={14}/> Protocolo Sanitário</span>
                 <span className="text-white font-bold text-right text-xs">
                   {passport.medications.join(", ")}
                 </span>
               </div>
            </div>
          </div>
        </div>

        {/* Right Col: QR & Certification */}
        <div className="flex flex-col items-center justify-center bg-gradient-to-br from-indigo-900/20 to-slate-900 border border-indigo-500/20 rounded-2xl p-6 relative overflow-hidden">
          <div className="absolute top-0 right-0 p-4 opacity-10 pointer-events-none">
             <QrCode size={120} />
          </div>
          
          <h3 className="text-xs font-bold text-indigo-300 uppercase tracking-widest mb-6 text-center">Verificação via Blockchain</h3>
          
          {/* A fake QR Code for visualization using a public API to generate a QR of the passport ID */}
          <div className="bg-white p-3 rounded-xl shadow-lg mb-6 z-10 border-4 border-indigo-500/20">
             <img src={`https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=https://chikguard.com/verify/${passport.passport_id}`} alt="QR Code" className="w-32 h-32" />
          </div>
          
          <div className="text-center z-10 w-full">
            <span className="block text-xs text-slate-400 uppercase mb-1">Status de Exportação</span>
            <div className="bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 px-3 py-2 rounded-lg font-bold text-sm w-full">
               {passport.certification}
            </div>
          </div>
        </div>

      </div>

      {/* Footer / Actions */}
      <div className="mt-8 pt-6 border-t border-slate-800 flex justify-between items-center">
        <p className="text-xs text-slate-500 font-mono">ChikGuard Enterprise - Gerado em {new Date().toLocaleDateString()}</p>
        <button 
           aria-label="Exportar passaporte do lote para PDF"
           onClick={() => window.print()}
           className="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-lg text-sm font-bold flex items-center gap-2 transition-colors shadow-lg shadow-indigo-500/20 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900 focus:outline-none"
        >
          <Download size={16} aria-hidden="true" /> Exportar PDF
        </button>
      </div>
    </div>
  );
}
