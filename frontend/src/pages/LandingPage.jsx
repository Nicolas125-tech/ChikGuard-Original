import React, { useEffect, useRef, useState } from 'react';
import { LogIn, ArrowRight, ShieldCheck, Activity, BrainCircuit, Eye, Zap, BarChart3 } from 'lucide-react';

function AnimatedCounter({ target, suffix = '', duration = 2000 }) {
  const [count, setCount] = useState(0);
  const ref = useRef(null);
  const started = useRef(false);

  useEffect(() => {
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting && !started.current) {
        started.current = true;
        const startTime = performance.now();
        const animate = (now) => {
          const elapsed = now - startTime;
          const progress = Math.min(elapsed / duration, 1);
          const eased = 1 - Math.pow(1 - progress, 3);
          setCount(Math.floor(eased * target));
          if (progress < 1) requestAnimationFrame(animate);
        };
        requestAnimationFrame(animate);
      }
    }, { threshold: 0.3 });

    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, [target, duration]);

  return <span ref={ref}>{count}{suffix}</span>;
}

export default function LandingPage({ onLoginClick }) {
  return (
    <div className="min-h-screen bg-slate-950 text-white flex flex-col relative overflow-hidden">
      {/* Background */}
      <div className="absolute inset-0 z-0">
        <div className="absolute inset-0 bg-grid-pattern opacity-40"></div>
        <div className="absolute left-1/2 -translate-x-1/2 top-0 -z-10 m-auto h-[400px] w-[400px] rounded-full bg-emerald-500 opacity-[0.12] blur-[120px]"></div>
        <div className="absolute bottom-0 right-0 -z-10 h-[400px] w-[400px] rounded-full bg-blue-600 opacity-[0.06] blur-[120px]"></div>
        <div className="absolute bottom-1/4 left-0 -z-10 h-[250px] w-[250px] rounded-full bg-purple-600 opacity-[0.04] blur-[100px]"></div>
      </div>

      {/* Navbar */}
      <nav className="relative z-10 flex justify-between items-center px-6 lg:px-8 py-5 max-w-7xl mx-auto w-full">
        <div className="flex items-center gap-3">
          <div className="bg-slate-900/60 p-2 rounded-xl border border-emerald-500/20 shadow-lg shadow-emerald-500/5 glass flex items-center justify-center">
            <img src="/logo.jpeg" alt="ChikGuard Logo" className="w-8 h-8 object-contain rounded-md" />
          </div>
          <span className="text-xl lg:text-2xl font-extrabold tracking-tight text-white">
            Chick<span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 to-teal-300">Guard</span> AI
          </span>
        </div>
        <button
          onClick={onLoginClick}
          className="bg-slate-900/80 hover:bg-slate-800 text-slate-200 px-5 py-2.5 rounded-full font-medium border border-slate-700/50 hover:border-emerald-500/40 hover:text-white transition-all flex items-center gap-2 glass text-sm hover-lift"
        >
          <LogIn size={16} /> Acesso Restrito
        </button>
      </nav>

      {/* Hero */}
      <main className="relative z-10 flex-1 flex flex-col items-center justify-center text-center px-4 max-w-6xl mx-auto w-full mt-4 md:mt-8 mb-16">
        {/* Version Badge */}
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full glass border-emerald-500/20 text-emerald-400 text-sm font-medium mb-8 animate-fade-in-down">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
          </span>
          Sistema Operacional v3.0 — Enterprise
        </div>

        {/* Headline */}
        <h1 className="text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-extrabold tracking-tight mb-8 leading-[1.1] animate-fade-in-up">
          Inteligência Artificial para <br className="hidden md:block" />
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 via-emerald-300 to-teal-200 animate-gradient">
            Avicultura de Precisão
          </span>
        </h1>

        <p className="text-base sm:text-lg md:text-xl text-slate-400 max-w-3xl mb-12 leading-relaxed animate-fade-in-up stagger-2">
          Monitoramento comportamental 24/7, controle de ambiência integrado e predição de anomalias na granja. Centralize sua operação com visão computacional de ponta.
        </p>

        {/* CTA */}
        <button
          onClick={onLoginClick}
          className="bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-slate-950 px-10 py-4 rounded-full font-bold text-lg shadow-[0_0_40px_-10px_rgba(16,185,129,0.5)] hover:shadow-[0_0_60px_-15px_rgba(16,185,129,0.7)] transition-all flex items-center gap-3 group hover-lift animate-fade-in-up stagger-3"
        >
          Acessar Dashboard
          <ArrowRight className="group-hover:translate-x-1 transition-transform" size={20} />
        </button>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4 mt-16 w-full max-w-3xl animate-fade-in-up stagger-4">
          {[
            { value: 99.7, suffix: '%', label: 'Uptime' },
            { value: 24, suffix: '/7', label: 'Monitoramento' },
            { value: 50, suffix: 'ms', label: 'Latência IA' },
            { value: 98, suffix: '%', label: 'Precisão YOLO' },
          ].map((stat, i) => (
            <div key={i} className="glass rounded-2xl p-4 text-center hover-lift">
              <div className="text-2xl md:text-3xl font-extrabold text-white mb-1">
                <AnimatedCounter target={stat.value} suffix={stat.suffix} />
              </div>
              <div className="text-xs text-slate-400 font-medium uppercase tracking-wider">{stat.label}</div>
            </div>
          ))}
        </div>

        {/* Feature Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mt-20 w-full text-left">
          {[
            {
              icon: BrainCircuit, color: 'blue',
              title: 'Visão Computacional',
              desc: 'Detecção YOLO SOTA + ByteTrack. Identificação de anomalias e análise comportamental do lote em tempo real.',
            },
            {
              icon: Activity, color: 'emerald',
              title: 'Controle de Ambiência',
              desc: 'Telemetria IoT unificada e controle autônomo de ventilação, nebulização e aquecimento baseados em IA.',
            },
            {
              icon: ShieldCheck, color: 'purple',
              title: 'Auditoria e Segurança',
              desc: 'RBAC enterprise, audit trail completo, alertas push multicanal e controle de acesso Zero-Trust.',
            },
          ].map((card, i) => {
            const colors = {
              blue: 'bg-blue-500/10 border-blue-500/20 text-blue-400',
              emerald: 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400',
              purple: 'bg-purple-500/10 border-purple-500/20 text-purple-400',
            };
            const Icon = card.icon;

            return (
              <div
                key={i}
                className={`card-premium p-6 hover-lift animate-fade-in-up stagger-${i + 4}`}
              >
                <div className={`${colors[card.color]} w-12 h-12 rounded-xl flex items-center justify-center mb-4 border`}>
                  <Icon size={24} />
                </div>
                <h3 className="text-lg font-bold text-white mb-2">{card.title}</h3>
                <p className="text-slate-400 text-sm leading-relaxed">{card.desc}</p>
              </div>
            );
          })}
        </div>
      </main>

      {/* Footer */}
      <footer className="relative z-10 border-t border-slate-800/40 py-6 text-center text-xs text-slate-600">
        © {new Date().getFullYear()} ChickGuard AI — Todos os direitos reservados
      </footer>
    </div>
  );
}
