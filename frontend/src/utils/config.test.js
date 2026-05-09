import { describe, it, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert';
import { readPrefs, DEFAULT_PREFS, STORAGE } from './config.js';

describe('config.js - readPrefs', () => {
  let originalLocalStorage;

  beforeEach(() => {
    // Save original if it exists, though in Node.js it usually doesn't
    originalLocalStorage = global.localStorage;

    // Create a fresh mock for each test
    global.localStorage = {
      getItem: () => null,
      setItem: () => {},
      removeItem: () => {},
      clear: () => {}
    };
  });

  afterEach(() => {
    // Restore original
    global.localStorage = originalLocalStorage;
  });

  it('should return DEFAULT_PREFS when localStorage has no data', () => {
    global.localStorage.getItem = (key) => {
      assert.strictEqual(key, STORAGE.prefs);
      return null;
    };

    const result = readPrefs();
    assert.deepStrictEqual(result, DEFAULT_PREFS);
  });

  it('should return parsed preferences merged with DEFAULT_PREFS when valid JSON is present', () => {
    const validData = { statusMs: 5000, newSetting: true };
    global.localStorage.getItem = (key) => {
      assert.strictEqual(key, STORAGE.prefs);
      return JSON.stringify(validData);
    };

    const result = readPrefs();
    assert.deepStrictEqual(result, { ...DEFAULT_PREFS, ...validData });
  });

  it('should catch error and return DEFAULT_PREFS when JSON parsing fails', () => {
    global.localStorage.getItem = (key) => {
      assert.strictEqual(key, STORAGE.prefs);
      return '{ malformed json, this will throw an error }';
    };

    const result = readPrefs();
    assert.deepStrictEqual(result, DEFAULT_PREFS);
  });
});
