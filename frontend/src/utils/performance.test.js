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
});
