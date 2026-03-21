import React from 'react';

export default function OpeningScreen() {
  return (
    <div className="min-h-screen bg-slate-950 text-white flex items-center justify-center p-8">
      <div className="w-full max-w-md text-center">
        <div className="mx-auto mb-6 w-24 h-24 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center overflow-hidden">
          <img src="/logo.jpeg" alt="ChikGuard Logo" className="w-20 h-20 object-contain" />
        </div>
        <h1 className="text-3xl font-bold tracking-tight">ChickGuard AI</h1>
        <p className="text-slate-400 mt-2">Inicializando sistema...</p>
        <div className="mt-8 h-2 rounded-full bg-slate-800 overflow-hidden">
          <div className="h-full w-full bg-gradient-to-r from-emerald-500 to-blue-500 animate-pulse" />
        </div>
      </div>
    </div>
  );
}
