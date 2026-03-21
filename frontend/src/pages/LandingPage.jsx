import React from 'react';
import { LogIn, ArrowRight } from 'lucide-react';

export default function LandingPage({ onLoginClick }) {
  return (
    <div className="min-h-screen bg-slate-950 text-white flex flex-col relative overflow-hidden">
      <div className="absolute top-0 left-0 w-full h-full pointer-events-none">
        <div className="absolute top-[-10%] right-[-5%] w-[500px] h-[500px] bg-emerald-500/10 rounded-full blur-[120px]" />
        <div className="absolute bottom-[-10%] left-[-10%] w-[600px] h-[600px] bg-blue-600/10 rounded-full blur-[120px]" />
      </div>
      <nav className="relative z-10 flex justify-between items-center p-6 max-w-7xl mx-auto w-full">
        <div className="flex items-center gap-2">
          <div className="bg-emerald-500/10 p-1 rounded-lg border border-emerald-500/30 w-11 h-11 flex items-center justify-center overflow-hidden">
            <img src="/logo.jpeg" alt="ChikGuard Logo" className="w-8 h-8 object-contain" />
          </div>
          <span className="text-xl font-bold tracking-tight">ChickGuard AI</span>
        </div>
        <button onClick={onLoginClick} className="bg-slate-800 hover:bg-slate-700 text-white px-5 py-2 rounded-full font-medium border border-slate-700 hover:border-emerald-500/50 flex items-center gap-2">
          <LogIn size={16} /> Acesso
        </button>
      </nav>
      <main className="relative z-10 flex-1 flex flex-col items-center justify-center text-center px-4 max-w-5xl mx-auto">
        <h1 className="text-4xl md:text-5xl lg:text-7xl font-bold tracking-tight mb-6 bg-clip-text text-transparent bg-gradient-to-b from-white to-slate-400">Plataforma profissional para monitoramento da granja</h1>
        <p className="text-base md:text-lg text-slate-400 max-w-2xl mb-10 leading-relaxed">Tela de abertura, painel em tempo real e configuracoes operacionais centralizadas.</p>
        <button onClick={onLoginClick} className="bg-emerald-600 hover:bg-emerald-500 text-white px-8 py-4 rounded-xl font-bold text-lg shadow-lg shadow-emerald-500/20 flex items-center gap-2 group">
          Entrar no sistema <ArrowRight className="group-hover:translate-x-1 transition-transform" />
        </button>
      </main>
    </div>
  );
}
