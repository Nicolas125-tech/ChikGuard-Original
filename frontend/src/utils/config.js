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
  if (!ipOrUrl) return 'http://127.0.0.1:5000';
  const clean = ipOrUrl.replace(/\/$/, '');
  if (clean.startsWith('http://') || clean.startsWith('https://')) return clean;
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
