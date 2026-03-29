const crypto = require('crypto');
const { syncBuiltinESMExports } = require('module');
const { deserialize, serialize } = require('v8');

if (typeof crypto.getRandomValues !== 'function' && crypto.webcrypto) {
  crypto.getRandomValues = crypto.webcrypto.getRandomValues.bind(crypto.webcrypto);
}

if (typeof crypto.randomUUID !== 'function' && crypto.webcrypto?.randomUUID) {
  crypto.randomUUID = crypto.webcrypto.randomUUID.bind(crypto.webcrypto);
}

syncBuiltinESMExports();

if (!globalThis.crypto || typeof globalThis.crypto.getRandomValues !== 'function') {
  globalThis.crypto = crypto.webcrypto;
}

if (typeof globalThis.structuredClone !== 'function') {
  // ESLint plugins only need plain-object cloning in this repo's Node 16 fallback path.
  globalThis.structuredClone = function structuredClonePolyfill(value, options) {
    if (options && Array.isArray(options.transfer) && options.transfer.length > 0) {
      throw new Error('structuredClone transfer is not supported by this compatibility polyfill.');
    }

    return deserialize(serialize(value));
  };
}
