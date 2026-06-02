/* global global */
import assert from 'node:assert';
import { describe, it, beforeEach, afterEach } from 'node:test';
import { readPrefs, DEFAULT_PREFS, STORAGE } from './config.js';

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

  it('deve retornar DEFAULT_PREFS quando o localStorage estiver vazio', () => {
    const prefs = readPrefs();
    assert.deepStrictEqual(prefs, DEFAULT_PREFS);
  });

  it('deve fazer o merge parcial (incluindo defaults faltantes) se os dados locais estiverem incompletos', () => {
    global.localStorage.getItem = (key) => {
      if (key === STORAGE.prefs || key === STORAGE) return JSON.stringify({ theme: 'light' });
      return null;
    };

    const prefs = readPrefs();
    assert.strictEqual(prefs.theme, 'light');
    assert.strictEqual(prefs.statusMs, DEFAULT_PREFS.statusMs);
  });

  it('deve retornar DEFAULT_PREFS e logar alerta em caso de JSON inválido', () => {
    global.localStorage.getItem = (key) => {
      if (key === STORAGE.prefs || key === STORAGE) return '{ inválido_json';
      return null;
    };

    // Suprime erro do console.warn no log de testes (opcional)
    const oldWarn = console.warn;
    console.warn = () => {};

    const prefs = readPrefs();
    assert.deepStrictEqual(prefs, DEFAULT_PREFS);

    console.warn = oldWarn;
  });
});
