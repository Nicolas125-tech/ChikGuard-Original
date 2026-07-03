/* global global */
// Mock import.meta.env BEFORE importing the file
global.import = {
  meta: {
    env: {}
  }
};

import assert from 'node:assert';
import { describe, it } from 'node:test';
import { supabaseStub, isSupabaseConfigured } from './supabaseClient.js';

describe('supabaseClient Stub', () => {
  it('isSupabaseConfigured should default to false when env vars are missing', () => {
    assert.strictEqual(isSupabaseConfigured, false);
  });

  describe('auth methods', () => {
    it('signUp should return a safe error object', async () => {
      const result = await supabaseStub.auth.signUp();
      assert.strictEqual(result.data, null);
      assert.strictEqual(result.error.message, 'Supabase não configurado neste ambiente.');
    });

    it('signInWithPassword should return a safe error object', async () => {
      const result = await supabaseStub.auth.signInWithPassword();
      assert.strictEqual(result.data, null);
      assert.strictEqual(result.error.message, 'Supabase não configurado neste ambiente.');
    });

    it('signInWithOAuth should return a safe error object', async () => {
      const result = await supabaseStub.auth.signInWithOAuth();
      assert.strictEqual(result.data, null);
      assert.strictEqual(result.error.message, 'Supabase não configurado neste ambiente.');
    });

    it('signOut should return an empty object', async () => {
      const result = await supabaseStub.auth.signOut();
      assert.deepStrictEqual(result, {});
    });

    it('getSession should return a session data object with no error', async () => {
      const result = await supabaseStub.auth.getSession();
      assert.deepStrictEqual(result.data, { session: null });
      assert.strictEqual(result.error, null);
    });

    it('onAuthStateChange should return an unsubscribe function', () => {
      const result = supabaseStub.auth.onAuthStateChange();
      assert.ok(typeof result.data.subscription.unsubscribe === 'function');

      // Execute the unsubscribe function to ensure it doesn't throw
      assert.doesNotThrow(() => result.data.subscription.unsubscribe());
    });
  });

  describe('from methods (database stub)', () => {
    it('select().eq().single() should return safe data and error object', async () => {
      const result = await supabaseStub.from('table').select('col').eq('col', 'val').single();
      assert.strictEqual(result.data, null);
      assert.strictEqual(result.error, null);
    });

    it('update().eq().execute() should return safe data and error object', async () => {
      const result = await supabaseStub.from('table').update({}).eq('col', 'val').execute();
      assert.strictEqual(result.data, null);
      assert.strictEqual(result.error, null);
    });
  });
});
