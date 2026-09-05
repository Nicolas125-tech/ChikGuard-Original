export function isDeepEqual(a, b) {
  if (a === b) return true;
  if (a !== a && b !== b) return true;
  if (a === null || b === null || typeof a !== 'object' || typeof b !== 'object') return false;

  if (Array.isArray(a) && Array.isArray(b)) {
    if (a.length !== b.length) return false;
    for (let i = 0; i < a.length; i++) {
      if ((i in a) !== (i in b)) return false;
      if (!isDeepEqual(a[i], b[i])) return false;
    }
    return true;
  }

  if (Array.isArray(a) !== Array.isArray(b)) return false;

  if (a.constructor !== b.constructor) return false;

  if (a instanceof Date) return a.getTime() === b.getTime();
  if (a instanceof RegExp) return a.toString() === b.toString();

  if (a instanceof Map) {
    if (a.size !== b.size) return false;
    for (let [key, val] of a) {
      if (!b.has(key) || !isDeepEqual(val, b.get(key))) return false;
    }
    return true;
  }

  if (a instanceof Set) {
    if (a.size !== b.size) return false;
    for (let val of a) {
      if (!b.has(val)) return false;
    }
    return true;
  }

  const keysA = Object.keys(a);
  const keysB = Object.keys(b);

  if (keysA.length !== keysB.length) return false;

  for (let key of keysA) {
    if (!Object.prototype.hasOwnProperty.call(b, key) || !isDeepEqual(a[key], b[key])) return false;
  }

  return true;
}
