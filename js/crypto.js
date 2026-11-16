// Decrypts content.enc (format written by content-src/build.mjs).
import * as store from './store.js';

function parse(buf) {
  const u = new Uint8Array(buf);
  const magic = new TextDecoder().decode(u.slice(0, 5));
  if (magic !== 'LLPC1') throw new Error('Unrecognised content file');
  const iter = new DataView(u.buffer, u.byteOffset).getUint32(5);
  return { iter, salt: u.slice(9, 25), iv: u.slice(25, 37), ct: u.slice(37) };
}

export async function deriveKey(passphrase, buf) {
  const { iter, salt } = parse(buf);
  const base = await crypto.subtle.importKey('raw', new TextEncoder().encode(passphrase.normalize('NFC')), 'PBKDF2', false, ['deriveKey']);
  return crypto.subtle.deriveKey({ name: 'PBKDF2', salt, iterations: iter, hash: 'SHA-256' }, base,
    { name: 'AES-GCM', length: 256 }, true, ['decrypt']);
}

async function gunzip(bytes) {
  if ('DecompressionStream' in self) {
    const s = new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'));
    return new Response(s).text();
  }
  throw new Error('This browser cannot decompress (needs iOS 16.4 or newer).');
}

export async function decrypt(key, buf) {
  const { iv, ct } = parse(buf);
  const plain = await crypto.subtle.decrypt({ name: 'AES-GCM', iv }, key, ct);
  return JSON.parse(await gunzip(new Uint8Array(plain)));
}

// Cache the key on this device. IndexedDB can hold the CryptoKey object itself; as a fallback
// (e.g. when IndexedDB is unavailable) the raw key bytes are kept in localStorage.
export async function saveKey(key) {
  try { await store.set('contentKey', key); } catch (e) {}
  try {
    const raw = new Uint8Array(await crypto.subtle.exportKey('raw', key));
    localStorage.setItem('vl:contentKeyRaw', btoa(String.fromCharCode(...raw)));
  } catch (e) {}
}
export async function loadKey() {
  try { const k = await store.get('contentKey'); if (k && k.type === 'secret') return k; } catch (e) {}
  try {
    const b = localStorage.getItem('vl:contentKeyRaw');
    if (b) {
      const raw = Uint8Array.from(atob(b), c => c.charCodeAt(0));
      return crypto.subtle.importKey('raw', raw, { name: 'AES-GCM' }, true, ['decrypt']);
    }
  } catch (e) {}
  return null;
}
export async function forgetKey() {
  await store.del('contentKey');
  try { localStorage.removeItem('vl:contentKeyRaw'); } catch (e) {}
}
