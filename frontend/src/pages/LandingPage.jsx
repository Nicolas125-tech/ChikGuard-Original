import React from 'react';
import { LogIn, ArrowRight, ShieldCheck, Activity, BrainCircuit } from 'lucide-react';

export default function LandingPage({ onLoginClick }) {
  return (
    <div className="min-h-screen bg-slate-950 text-white flex flex-col relative overflow-hidden font-sans">
      {/* Modern Background */}
      <div className="absolute inset-0 z-0">
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:24px_24px]"></div>
        <div className="absolute left-0 right-0 top-0 -z-10 m-auto h-[310px] w-[310px] rounded-full bg-emerald-500 opacity-20 blur-[100px]"></div>
        <div className="absolute bottom-0 right-0 -z-10 h-[400px] w-[400px] rounded-full bg-blue-600 opacity-10 blur-[120px]"></div>
      </div>

      {/* Navbar */}
      <nav className="relative z-10 flex justify-between items-center px-8 py-6 max-w-7xl mx-auto w-full">
        <div className="flex items-center gap-3">
          <div className="bg-slate-900/50 p-2 rounded-xl border border-emerald-500/20 shadow-lg shadow-emerald-500/10 backdrop-blur-sm flex items-center justify-center">
            <img src="/logo.jpeg" alt="ChikGuard Logo" className="w-8 h-8 object-contain rounded-md" />
          </div>
          <span className="text-2xl font-bold tracking-tight text-white">
            Chick<span className="text-emerald-400">Guard</span> AI
          </span>
        </div>
        <button
          onClick={onLoginClick}
          className="bg-slate-900/80 hover:bg-slate-800 text-slate-200 px-6 py-2.5 rounded-full font-medium border border-slate-700/50 hover:border-emerald-500/50 hover:text-white transition-all flex items-center gap-2 backdrop-blur-md shadow-sm"
        >
          <LogIn size={18} /> Acesso Restrito
        </button>
      </nav>

      {/* Main Content */}
      <main className="relative z-10 flex-1 flex flex-col items-center justify-center text-center px-4 max-w-6xl mx-auto w-full mt-8 md:mt-16 mb-20">
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-sm font-medium mb-8">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
          </span>
          Sistema Operacional v2.0
        </div>

        <h1 className="text-5xl md:text-6xl lg:text-7xl font-extrabold tracking-tight mb-8 leading-[1.1]">
          Inteligência Artificial para <br className="hidden md:block" />
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 via-emerald-300 to-teal-200">
            Avicultura de Precisão
          </span>
        </h1>

        <p className="text-lg md:text-xl text-slate-400 max-w-3xl mb-12 leading-relaxed">
          Monitoramento comportamental 24/7, controle de ambiência integrado e predição de anomalias na granja. Centralize sua operação com visão computacional de ponta.
        </p>

        <button
          onClick={onLoginClick}
          className="bg-emerald-500 hover:bg-emerald-400 text-slate-950 px-10 py-4 rounded-full font-bold text-lg shadow-[0_0_40px_-10px_rgba(16,185,129,0.5)] hover:shadow-[0_0_60px_-15px_rgba(16,185,129,0.7)] transition-all flex items-center gap-3 group transform hover:-translate-y-1"
        >
          Acessar Dashboard
          <ArrowRight className="group-hover:translate-x-1 transition-transform" size={20} />
        </button>

        {/* Feature Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-24 w-full text-left">
          <div className="bg-slate-900/40 border border-slate-800/60 p-6 rounded-2xl backdrop-blur-sm hover:bg-slate-900/60 transition-colors">
            <div className="bg-blue-500/10 w-12 h-12 rounded-lg flex items-center justify-center mb-4 border border-blue-500/20">
              <BrainCircuit className="text-blue-400" size={24} />
            </div>
            <h3 className="text-xl font-bold text-white mb-2">Visão Computacional</h3>
            <p className="text-slate-400 text-sm leading-relaxed">Identificação de anomalias térmicas e análise comportamental do lote em tempo real sem intervenção humana.</p>
          </div>

          <div className="bg-slate-900/40 border border-slate-800/60 p-6 rounded-2xl backdrop-blur-sm hover:bg-slate-900/60 transition-colors">
            <div className="bg-emerald-500/10 w-12 h-12 rounded-lg flex items-center justify-center mb-4 border border-emerald-500/20">
              <Activity className="text-emerald-400" size={24} />
            </div>
            <h3 className="text-xl font-bold text-white mb-2">Controle de Ambiência</h3>
            <p className="text-slate-400 text-sm leading-relaxed">Telemetria IoT unificada e controle autônomo de ventilação, nebulização e aquecimento baseados em IA.</p>
          </div>

          <div className="bg-slate-900/40 border border-slate-800/60 p-6 rounded-2xl backdrop-blur-sm hover:bg-slate-900/60 transition-colors">
            <div className="bg-purple-500/10 w-12 h-12 rounded-lg flex items-center justify-center mb-4 border border-purple-500/20">
              <ShieldCheck className="text-purple-400" size={24} />
            </div>
            <h3 className="text-xl font-bold text-white mb-2">Auditoria e Segurança</h3>
            <p className="text-slate-400 text-sm leading-relaxed">Registros em blockchain, controle de acesso Zero-Trust (mTLS) e notificações imediatas via push/email.</p>
          </div>
        </div>
      </main>
    </div>
  );
}
