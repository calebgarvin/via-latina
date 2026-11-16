// Tiny key-value store: IndexedDB first, localStorage fallback. Values are structured-cloned
// (so a CryptoKey can be stored in IndexedDB); the localStorage fallback stores JSON only.
const DB = 'via-latina', OS = 'kv';
let dbp = null;
function open() {
  if (dbp) return dbp;
  dbp = new Promise((res, rej) => {
    if (!('indexedDB' in self)) return rej(new Error('no idb'));
    const r = indexedDB.open(DB, 1);
    r.onupgradeneeded = () => r.result.createObjectStore(OS);
    r.onsuccess = () => res(r.result);
    r.onerror = () => rej(r.error);
  }).catch(e => { dbp = null; throw e; });
  return dbp;
}
async function tx(mode, fn) {
  const db = await open();
  return new Promise((res, rej) => {
    const t = db.transaction(OS, mode); const s = t.objectStore(OS);
    const r = fn(s);
    t.oncomplete = () => res(r && 'result' in r ? r.result : undefined);
    t.onerror = () => rej(t.error); t.onabort = () => rej(t.error);
  });
}
export async function get(key) {
  try { const v = await tx('readonly', s => s.get(key)); if (v !== undefined) return v; } catch (e) { /* fall through */ }
  try { const j = localStorage.getItem('vl:' + key); return j == null ? undefined : JSON.parse(j); } catch (e) { return undefined; }
}
export async function set(key, val) {
  let ok = false;
  try { await tx('readwrite', s => s.put(val, key)); ok = true; } catch (e) { /* fall through */ }
  // mirror JSON-able values to localStorage as a second copy (small values only)
  try {
    if (!(val instanceof CryptoKey)) {
      const j = JSON.stringify(val);
      if (j.length < 1_500_000) localStorage.setItem('vl:' + key, j);
    }
    ok = true;
  } catch (e) { /* quota / private mode */ }
  return ok;
}
export async function del(key) {
  try { await tx('readwrite', s => s.delete(key)); } catch (e) {}
  try { localStorage.removeItem('vl:' + key); } catch (e) {}
}
export async function persist() {
  try {
    if (navigator.storage && navigator.storage.persist) {
      if (await navigator.storage.persisted()) return true;
      return await navigator.storage.persist();
    }
  } catch (e) {}
  return false;
}
