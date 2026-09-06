/* global global */
import assert from 'node:assert';
import { describe, it, beforeEach, afterEach } from 'node:test';
import { readPrefs, getBaseUrl, DEFAULT_PREFS, STORAGE } from './config.js';

describe('Config Utilities', () => {
  beforeEach(() => {
    // Limpa o mock do localStorage
    global.localStorage = {
      getItem: () => null,
      setItem: () => {}
    };
  });

  afterEach(() => {
    delete global.localStorage;
  });

  it('should return DEFAULT_PREFS when localStorage is empty', () => {
    const prefs = readPrefs();
    assert.deepStrictEqual(prefs, DEFAULT_PREFS);
  });

  it('should do a partial merge (including missing defaults) if local data is incomplete', () => {
    global.localStorage.getItem = (key) => {
      if (key === STORAGE.prefs || key === STORAGE) return JSON.stringify({ theme: 'light' });
      return null;
    };

    const prefs = readPrefs();
    assert.strictEqual(prefs.theme, 'light');
    assert.strictEqual(prefs.statusMs, DEFAULT_PREFS.statusMs);
  });

  it('should return DEFAULT_PREFS in case of invalid JSON', () => {
    global.localStorage.getItem = (key) => {
      if (key === STORAGE.prefs || key === STORAGE) return '{ invalid_json';
      return null;
    };

    // Suprime erro do console.warn no log de testes (opcional)
    const oldWarn = console.warn;
    console.warn = () => {};

    const prefs = readPrefs();
    assert.deepStrictEqual(prefs, DEFAULT_PREFS);

    console.warn = oldWarn;
  });

  it('should return DEFAULT_PREFS if an error occurs when accessing localStorage', () => {
    const originalGetItem = global.localStorage.getItem;
    global.localStorage.getItem = () => {
      throw new Error('Access denied');
    };

    const prefs = readPrefs();
    assert.deepStrictEqual(prefs, DEFAULT_PREFS);
    global.localStorage.getItem = originalGetItem;
  });
});

describe('getBaseUrl', () => {
  let originalWindow;

  beforeEach(() => {
    originalWindow = global.window;
    global.window = {
      location: {
        hostname: 'example.com',
        origin: 'https://example.com'
      }
    };

    // Node.js test runner doesn't naturally support importing Vite's import.meta.env
    // We can conditionally mock it by temporarily defining import.meta.env if needed
    // However, since we refactored config.js to (import.meta.env || {}).VITE_API_URL
    // We can just test without explicitly throwing TypeError.
  });

  afterEach(() => {
    global.window = originalWindow;
  });

  it('should return origin if hostname is a tunnel host', () => {
    global.window.location.hostname = 'random-trycloudflare.com';
    global.window.location.origin = 'https://random-trycloudflare.com';
    assert.strictEqual(getBaseUrl(), 'https://random-trycloudflare.com');
  });

  it('should return origin if hostname matches trycloudflare but not origin', () => {
    global.window.location.hostname = 'example-trycloudflare.com';
    global.window.location.origin = 'https://different-origin.com';
    assert.strictEqual(getBaseUrl(), 'https://different-origin.com');
  });

  it('should ignore ipOrUrl and return origin if hostname matches a tunnel host like cfargotunnel', () => {
    global.window.location.hostname = 'test-cfargotunnel.com';
    global.window.location.origin = 'https://cfargotunnel.com';
    assert.strictEqual(getBaseUrl('http://192.168.1.1:5000'), 'https://cfargotunnel.com');
  });

  it('should return local backend URL if hostname is localhost', () => {
    global.window.location.hostname = 'localhost';
    assert.strictEqual(getBaseUrl('192.168.1.100'), 'http://127.0.0.1:5000');
  });

  it('should return local backend URL if hostname is 127.0.0.1', () => {
    global.window.location.hostname = '127.0.0.1';
    assert.strictEqual(getBaseUrl('https://custom-url.com'), 'http://127.0.0.1:5000');
  });

  it('should return default local backend URL if neither ipOrUrl nor VITE_API_URL is provided', () => {
    // Tests the fallback line: if (!target) return 'http://127.0.0.1:5000';
    assert.strictEqual(getBaseUrl(), 'http://127.0.0.1:5000');
  });

  it('should preserve protocols (http://, https://) provided in ipOrUrl', () => {
    assert.strictEqual(getBaseUrl('https://custom.com'), 'https://custom.com');
    assert.strictEqual(getBaseUrl('http://custom.com'), 'http://custom.com');
  });

  it('should append https:// for recognized domains', () => {
    assert.strictEqual(getBaseUrl('api.vercel.app'), 'https://api.vercel.app');
    assert.strictEqual(getBaseUrl('app.ngrok.app'), 'https://app.ngrok.app');
    assert.strictEqual(getBaseUrl('custom.onrender.com'), 'https://custom.onrender.com');
    assert.strictEqual(getBaseUrl('app.herokuapp.com'), 'https://app.herokuapp.com');
    assert.strictEqual(getBaseUrl('site.cfargotunnel.com'), 'https://site.cfargotunnel.com');
  });

  it('should append http:// and :5000 for standard IPs or domains', () => {
    assert.strictEqual(getBaseUrl('192.168.1.100'), 'http://192.168.1.100:5000');
    assert.strictEqual(getBaseUrl('my-internal-server'), 'http://my-internal-server:5000');
  });

  it('should strip trailing slashes before processing', () => {
    assert.strictEqual(getBaseUrl('https://custom.com/'), 'https://custom.com');
    assert.strictEqual(getBaseUrl('192.168.1.100/'), 'http://192.168.1.100:5000');
  });
});
