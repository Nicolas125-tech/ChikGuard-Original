import React, { useState, useEffect } from 'react';

const BOOT_STEPS = [
  { label: 'Inicializando Kernel de IA', icon: '🧠' },
  { label: 'Conectando sensores IoT', icon: '📡' },
  { label: 'Carregando modelos YOLO', icon: '🎯' },
  { label: 'Verificando câmeras', icon: '📹' },
  { label: 'Sistema operacional', icon: '✅' },
];

export default function OpeningScreen() {
  const [step, setStep] = useState(0);
  const [progress, setProgress] = useState(0);
  const [showLogo, setShowLogo] = useState(false);

  useEffect(() => {
    // Logo entrance
    const logoTimer = setTimeout(() => setShowLogo(true), 100);

    // Step progression
    const stepInterval = setInterval(() => {
      setStep(s => {
        if (s < BOOT_STEPS.length - 1) return s + 1;
        clearInterval(stepInterval);
        return s;
      });
    }, 280);

    // Smooth progress bar
    const progressInterval = setInterval(() => {
      setProgress(p => {
        if (p >= 100) {
          clearInterval(progressInterval);
          return 100;
        }
        return p + 1.2;
      });
    }, 14);

    return () => {
      clearTimeout(logoTimer);
      clearInterval(stepInterval);
      clearInterval(progressInterval);
    };
  }, []);

  return (
    <div className="min-h-screen bg-slate-950 text-white flex items-center justify-center p-8 relative overflow-hidden">
      {/* Background glow orbs */}
      <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full bg-emerald-500/5 blur-[150px] pointer-events-none"></div>
      <div className="absolute top-0 right-0 w-[300px] h-[300px] rounded-full bg-blue-600/5 blur-[100px] pointer-events-none"></div>
      <div className="absolute inset-0 bg-grid-pattern opacity-30"></div>

      <div className="w-full max-w-md text-center relative z-10">
        {/* Logo with scale-in animation */}
        <div
          className={`mx-auto mb-8 w-28 h-28 rounded-3xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center overflow-hidden shadow-2xl shadow-emerald-500/10 transition-all duration-700 ease-out ${
            showLogo ? 'opacity-100 scale-100' : 'opacity-0 scale-75'
          }`}
        >
          <img src="/logo.jpeg" alt="ChikGuard Logo" className="w-22 h-22 object-contain" />
        </div>

        {/* Title */}
        <h1
          className={`text-4xl font-extrabold tracking-tight mb-2 bg-gradient-to-r from-emerald-400 via-emerald-300 to-teal-200 text-transparent bg-clip-text transition-all duration-500 delay-200 ${
            showLogo ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'
          }`}
        >
          ChickGuard AI
        </h1>
        <p
          className={`text-slate-500 text-sm mb-10 transition-all duration-500 delay-300 ${
            showLogo ? 'opacity-100' : 'opacity-0'
          }`}
        >
          Avicultura de Precisão
        </p>

        {/* Progress bar */}
        <div className="h-1.5 rounded-full bg-slate-800/80 overflow-hidden mb-6 mx-auto max-w-xs border border-slate-800/50">
          <div
            className="h-full rounded-full bg-gradient-to-r from-emerald-500 via-emerald-400 to-teal-300 transition-all duration-100 ease-linear shadow-lg shadow-emerald-500/30"
            style={{ width: `${Math.min(progress, 100)}%` }}
          />
        </div>

        {/* Status Step */}
        <div className="h-8 flex items-center justify-center">
          <p
            key={step}
            className="text-slate-400 text-sm animate-fade-in-up flex items-center gap-2"
          >
            <span>{BOOT_STEPS[step]?.icon}</span>
            <span>{BOOT_STEPS[step]?.label}...</span>
          </p>
        </div>
      </div>
    </div>
  );
}
