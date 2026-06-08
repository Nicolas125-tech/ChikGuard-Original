import React, { useState } from 'react';
import { STORAGE } from '../utils/config';

export default function SetupScreen({ token, onComplete }) {
  const [step, setStep] = useState(1);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formData, setFormData] = useState({
    serverIP: localStorage.getItem(STORAGE.server) || '127.0.0.1',
    cameraUrl: '',
    farmName: '',
    location: '',
  });

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const nextStep = () => setStep(s => s + 1);
  const prevStep = () => setStep(s => s - 1);

  const handleFinish = async () => {
    setIsSubmitting(true);
    try {
      // Salva as configurações de IP no localStorage
      const cleanIP = formData.serverIP.replace(/\/$/, '');
      const baseUrl = cleanIP.startsWith('http') ? cleanIP : `http://${cleanIP}`;
      localStorage.setItem(STORAGE.server, cleanIP);
      localStorage.setItem('cg_farm_name', formData.farmName);
      localStorage.setItem('cg_camera_url', formData.cameraUrl);
      localStorage.setItem('cg_setup_complete', 'true');

      // Tenta registrar a granja/câmera no backend, se o token e os dados estiverem disponíveis
      if (token && formData.farmName) {
        const payload = {
          camera_id: `granja-${Math.floor(Math.random() * 10000)}`,
          name: formData.farmName,
          connection_type: formData.cameraUrl.startsWith('rtsp') ? 'rtsp' : 'url',
          connection_url: formData.cameraUrl || ''
        };

        await fetch(`${baseUrl}/api/cameras`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
          },
          body: JSON.stringify(payload)
        });
      }
    } catch (e) {
      console.error("Erro ao registrar granja inicial no backend", e);
    } finally {
      setIsSubmitting(false);
      onComplete();
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-4 relative overflow-hidden">
      {/* Background elements */}
      <div className="absolute left-1/3 top-1/4 w-96 h-96 rounded-full bg-emerald-500/10 blur-[120px] pointer-events-none"></div>
      <div className="absolute right-1/3 bottom-1/4 w-96 h-96 rounded-full bg-teal-500/10 blur-[120px] pointer-events-none"></div>
      <div className="absolute inset-0 bg-[url('/grid.svg')] opacity-10 bg-repeat"></div>

      <div className="z-10 w-full max-w-lg bg-slate-900/80 backdrop-blur-xl border border-slate-700 rounded-3xl shadow-2xl p-8">
        
        {/* Header */}
        <div className="text-center mb-8">
          <div className="mx-auto mb-4 w-16 h-16 rounded-2xl bg-gradient-to-tr from-emerald-500 to-teal-400 flex items-center justify-center shadow-lg shadow-emerald-500/30">
            <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </div>
          <h2 className="text-2xl font-bold text-white tracking-tight">Bem-vindo ao ChikGuard</h2>
          <p className="text-slate-400 mt-2 text-sm">Vamos configurar seu sistema para a primeira utilização.</p>
        </div>

        {/* Steps */}
        <div className="flex items-center justify-between mb-8 relative">
          <div className="absolute top-1/2 left-0 w-full h-0.5 bg-slate-700 -z-10 -translate-y-1/2"></div>
          <div className={`absolute top-1/2 left-0 h-0.5 bg-emerald-500 -z-10 -translate-y-1/2 transition-all duration-500`} style={{ width: `${(step - 1) * 50}%` }}></div>
          
          {[1, 2, 3].map((num) => (
            <div key={num} className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold transition-all duration-300 ${
              step >= num ? 'bg-emerald-500 text-white shadow-[0_0_15px_rgba(16,185,129,0.5)]' : 'bg-slate-800 text-slate-500 border border-slate-700'
            }`}>
              {num}
            </div>
          ))}
        </div>

        {/* Form Content */}
        <div className="min-h-[220px]">
          {step === 1 && (
            <div className="animate-fade-in-up">
              <h3 className="text-lg font-semibold text-white mb-4">Informações do Servidor</h3>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-1">IP do Servidor (Backend)</label>
                  <input 
                    type="text" 
                    name="serverIP"
                    value={formData.serverIP}
                    onChange={handleChange}
                    className="w-full bg-slate-950/50 border border-slate-700 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 transition-colors"
                    placeholder="Ex: 192.168.1.100"
                  />
                </div>
              </div>
            </div>
          )}

          {step === 2 && (
            <div className="animate-fade-in-up">
              <h3 className="text-lg font-semibold text-white mb-4">Detalhes da Granja</h3>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-1">Nome da Granja</label>
                  <input 
                    type="text" 
                    name="farmName"
                    value={formData.farmName}
                    onChange={handleChange}
                    className="w-full bg-slate-950/50 border border-slate-700 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 transition-colors"
                    placeholder="Ex: Granja São José"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-1">Localização (Opcional)</label>
                  <input 
                    type="text" 
                    name="location"
                    value={formData.location}
                    onChange={handleChange}
                    className="w-full bg-slate-950/50 border border-slate-700 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 transition-colors"
                    placeholder="Ex: Cascavel, PR"
                  />
                </div>
              </div>
            </div>
          )}

          {step === 3 && (
            <div className="animate-fade-in-up">
              <h3 className="text-lg font-semibold text-white mb-4">Câmera (Opcional)</h3>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-1">URL RTSP ou IP da Câmera</label>
                  <input 
                    type="text" 
                    name="cameraUrl"
                    value={formData.cameraUrl}
                    onChange={handleChange}
                    className="w-full bg-slate-950/50 border border-slate-700 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 transition-colors"
                    placeholder="rtsp://admin:senha@192.168.1.10/stream1"
                  />
                  <p className="text-xs text-slate-500 mt-2">Pode ser configurado depois pelo Dashboard.</p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Buttons */}
        <div className="flex gap-3 mt-8">
          {step > 1 && (
            <button 
              onClick={prevStep}
              className="flex-1 py-3 px-4 rounded-xl border border-slate-700 text-white font-medium hover:bg-slate-800 transition-colors"
            >
              Voltar
            </button>
          )}
          
          {step < 3 ? (
            <button 
              onClick={nextStep}
              className="flex-2 w-full py-3 px-4 rounded-xl bg-gradient-to-r from-emerald-600 to-emerald-500 text-white font-medium hover:from-emerald-500 hover:to-emerald-400 transition-all shadow-lg shadow-emerald-500/25"
            >
              Avançar
            </button>
          ) : (
            <button 
              onClick={handleFinish}
              disabled={isSubmitting}
              className="flex-2 w-full py-3 px-4 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-500 text-white font-medium hover:from-emerald-500 hover:to-teal-400 transition-all shadow-lg shadow-emerald-500/25 disabled:opacity-50"
            >
              {isSubmitting ? 'Salvando...' : 'Concluir Configuração'}
            </button>
          )}
        </div>

      </div>
    </div>
  );
}
