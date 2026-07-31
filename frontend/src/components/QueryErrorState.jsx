import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

export default function QueryErrorState({ message, onRetry, className = "" }) {
  return (
    <div className={`flex flex-col items-center justify-center p-8 bg-slate-900/70 backdrop-blur-lg rounded-2xl border border-rose-500/20 text-center max-w-md mx-auto my-6 animate-fade-in shadow-2xl ${className}`}>
      <div className="p-4 bg-rose-500/10 rounded-full border border-rose-500/30 text-rose-400 mb-4 animate-pulse">
        <AlertTriangle size={36} />
      </div>
      <h3 className="text-lg font-bold text-slate-100 mb-2 font-outfit tracking-wide">
        Erro de Conexão ou Consulta
      </h3>
      <p className="text-sm text-slate-400 mb-6 max-w-xs leading-relaxed">
        {message || "Não foi possível carregar os dados. Verifique a conexão com o servidor da granja e tente novamente."}
      </p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="flex items-center gap-2 px-5 py-2.5 bg-rose-500 hover:bg-rose-600 transition-all duration-300 text-white font-medium rounded-xl shadow-lg shadow-rose-500/10 hover:shadow-rose-500/20 text-sm active:scale-95 cursor-pointer"
        >
          <RefreshCw size={16} className="animate-spin-hover" />
          Tentar Novamente
        </button>
      )}
    </div>
  );
}
