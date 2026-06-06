export const STORAGE = {
  token: 'cg_token',
  role: 'cg_role',
  username: 'cg_username',
  server: 'cg_ip',
  prefs: 'cg_prefs',
};

export const DEFAULT_PREFS = {
  statusMs: 3000,
  historyMs: 12000,
  devicesMs: 5000,
  countMs: 3000,
};

export const isTunnelHost = (value = '') => /trycloudflare|cfargotunnel/i.test(value);

export const getBaseUrl = (ipOrUrl) => {
  if (isTunnelHost(window.location.hostname)) return window.location.origin;
  
  // Se estiver rodando localmente no navegador, force o uso do backend local
  // para evitar que configs velhas apontem para o Vercel.
  if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    return 'http://127.0.0.1:5000';
  }

  const target = ipOrUrl || import.meta.env.VITE_API_URL;
  if (!target) return 'http://127.0.0.1:5000';
  const clean = target.replace(/\/$/, '');
  
  if (clean.startsWith('http://') || clean.startsWith('https://')) return clean;
  
  if (/(trycloudflare|cfargotunnel|ngrok|onrender|herokuapp|vercel\.app)/i.test(clean)) {
    return `https://${clean}`;
  }
  
  return `http://${clean}:5000`;
};

export const readPrefs = () => {
  try {
    const raw = localStorage.getItem(STORAGE.prefs);
    return raw ? { ...DEFAULT_PREFS, ...JSON.parse(raw) } : DEFAULT_PREFS;
  } catch {
    return DEFAULT_PREFS;
  }
};
