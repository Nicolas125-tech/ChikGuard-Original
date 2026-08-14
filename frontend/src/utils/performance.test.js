import assert from 'node:assert';
import { describe, it } from 'node:test';
import { isDeepEqual } from './performance.js';

describe('isDeepEqual', () => {
  it('should return true for identical primitive values', () => {
    assert.strictEqual(isDeepEqual(1, 1), true);
    assert.strictEqual(isDeepEqual('test', 'test'), true);
    assert.strictEqual(isDeepEqual(true, true), true);
    assert.strictEqual(isDeepEqual(null, null), true);
    assert.strictEqual(isDeepEqual(undefined, undefined), true);
  });

  it('should return false for different primitive values', () => {
    assert.strictEqual(isDeepEqual(1, 2), false);
    assert.strictEqual(isDeepEqual('test', 'test2'), false);
    assert.strictEqual(isDeepEqual(true, false), false);
    assert.strictEqual(isDeepEqual(1, '1'), false);
    assert.strictEqual(isDeepEqual(null, undefined), false);
  });

  it('should return true for deeply equal arrays', () => {
    assert.strictEqual(isDeepEqual([], []), true);
    assert.strictEqual(isDeepEqual([1, 2, 3], [1, 2, 3]), true);
    assert.strictEqual(isDeepEqual([{ a: 1 }, { b: 2 }], [{ a: 1 }, { b: 2 }]), true);
    assert.strictEqual(isDeepEqual([[1, 2], [3, 4]], [[1, 2], [3, 4]]), true);
  });

  it('should return false for different arrays', () => {
    assert.strictEqual(isDeepEqual([1, 2], [1, 2, 3]), false);
    assert.strictEqual(isDeepEqual([1, 2, 3], [1, 3, 2]), false);
    assert.strictEqual(isDeepEqual([{ a: 1 }], [{ a: 2 }]), false);
  });

  it('should return true for deeply equal objects', () => {
    assert.strictEqual(isDeepEqual({}, {}), true);
    assert.strictEqual(isDeepEqual({ a: 1, b: 2 }, { a: 1, b: 2 }), true);
    assert.strictEqual(isDeepEqual({ a: { b: 1 } }, { a: { b: 1 } }), true);
    assert.strictEqual(isDeepEqual({ a: [1, 2] }, { a: [1, 2] }), true);
  });

  it('should return false for different objects', () => {
    assert.strictEqual(isDeepEqual({ a: 1 }, { a: 2 }), false);
    assert.strictEqual(isDeepEqual({ a: 1 }, { b: 1 }), false);
    assert.strictEqual(isDeepEqual({ a: 1 }, { a: 1, b: 2 }), false);
    assert.strictEqual(isDeepEqual({ a: { b: 1 } }, { a: { b: 2 } }), false);
  });

  it('should return false when comparing array to object', () => {
    assert.strictEqual(isDeepEqual([], {}), false);
    assert.strictEqual(isDeepEqual([1, 2], { 0: 1, 1: 2 }), false);
  });

  it('should return false when one argument is null and the other is an object', () => {
    assert.strictEqual(isDeepEqual(null, {}), false);
    assert.strictEqual(isDeepEqual({}, null), false);
  });

  it('should handle Date objects correctly', () => {
    const d1 = new Date('2023-01-01');
    const d2 = new Date('2023-01-01');
    const d3 = new Date('2024-01-01');
    assert.strictEqual(isDeepEqual(d1, d2), true);
    assert.strictEqual(isDeepEqual(d1, d3), false);
    assert.strictEqual(isDeepEqual(d1, {}), false);
  });

  it('should handle RegExp objects correctly', () => {
    const r1 = /abc/i;
    const r2 = /abc/i;
    const r3 = /def/i;
    const r4 = /abc/g;
    assert.strictEqual(isDeepEqual(r1, r2), true);
    assert.strictEqual(isDeepEqual(r1, r3), false);
    assert.strictEqual(isDeepEqual(r1, r4), false);
    assert.strictEqual(isDeepEqual(r1, {}), false);
  });

  it('should handle Map objects correctly', () => {
    const m1 = new Map([['a', 1], ['b', 2]]);
    const m2 = new Map([['a', 1], ['b', 2]]);
    const m3 = new Map([['a', 1]]);
    const m4 = new Map([['a', 1], ['c', 3]]);
    const m5 = new Map([['a', { nested: true }]]);
    const m6 = new Map([['a', { nested: true }]]);
    const m7 = new Map([['a', { nested: false }]]);

    assert.strictEqual(isDeepEqual(m1, m2), true);
    assert.strictEqual(isDeepEqual(m1, m3), false);
    assert.strictEqual(isDeepEqual(m1, m4), false);
    assert.strictEqual(isDeepEqual(m5, m6), true);
    assert.strictEqual(isDeepEqual(m5, m7), false);
    assert.strictEqual(isDeepEqual(m1, {}), false);
  });

  it('should handle Set objects correctly', () => {
    const s1 = new Set([1, 2, 3]);
    const s2 = new Set([1, 2, 3]);
    const s3 = new Set([1, 2]);
    const s4 = new Set([1, 2, 4]);

    assert.strictEqual(isDeepEqual(s1, s2), true);
    assert.strictEqual(isDeepEqual(s1, s3), false);
    assert.strictEqual(isDeepEqual(s1, s4), false);
  });
});
