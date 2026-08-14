const procEnv = typeof globalThis !== 'undefined' && globalThis.process && globalThis.process.env ? globalThis.process.env : {};

export const STORAGE = {
  token: (import.meta.env && import.meta.env.VITE_STORAGE_TOKEN) || procEnv.VITE_STORAGE_TOKEN,
  role: (import.meta.env && import.meta.env.VITE_STORAGE_ROLE) || procEnv.VITE_STORAGE_ROLE,
  username: (import.meta.env && import.meta.env.VITE_STORAGE_USERNAME) || procEnv.VITE_STORAGE_USERNAME,
  server: (import.meta.env && import.meta.env.VITE_STORAGE_SERVER) || procEnv.VITE_STORAGE_SERVER,
  prefs: (import.meta.env && import.meta.env.VITE_STORAGE_PREFS) || procEnv.VITE_STORAGE_PREFS,
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
  
  if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    return 'http://127.0.0.1:5000';
  }

  const target = ipOrUrl || (import.meta.env && import.meta.env.VITE_API_URL) || procEnv.VITE_API_URL;
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
