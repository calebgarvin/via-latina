// Loads and decrypts the course content; small helpers to slice readings.
import { deriveKey, decrypt, saveKey, loadKey, forgetKey } from './crypto.js';

let C = null, buf = null;
async function fetchEnc() {
  if (buf) return buf;
  const r = await fetch('content.enc', { cache: 'no-cache' }).catch(() => fetch('content.enc'));
  if (!r.ok) throw new Error('Could not load content.enc');
  buf = await r.arrayBuffer();
  return buf;
}
export async function tryCachedKey() {
  const key = await loadKey();
  if (!key) return false;
  try { C = await decrypt(key, await fetchEnc()); index(); return true; }
  catch (e) { console.warn('cached key failed', e); return false; }
}
export async function unlock(passphrase) {
  const b = await fetchEnc();
  const key = await deriveKey(passphrase, b);
  C = await decrypt(key, b); // throws on a wrong passphrase
  index();
  await saveKey(key);
  return true;
}
export async function lock() { await forgetKey(); C = null; }
export function data() { return C; }

function index() {
  C.byDay = {}; for (const d of C.days) C.byDay[d.d] = d;
  C.chap = {}; for (const c of C.chapters) C.chap[c.n] = c;
}
export const day = n => C.byDay[n];
export const chapter = n => C.chap[n];
export const lemma = id => C.lemmas[id];
export const days = () => C.days;

/** paragraphs (with token lists, re-based) that make up reading day n */
export function readingOf(n) {
  const d = C.byDay[n]; const ch = C.chap[d.c];
  const out = [];
  for (const [sec, pi, a, b] of d.r) {
    const p = sec === 'r' ? ch.paras[pi] : ch.gram[pi];
    const s = p.s.slice(a, b);
    const toks = p.t.filter(t => t[0] >= a && t[0] < b).map(t => [t[0] - a, ...t.slice(1)]);
    const prevSame = out.length && out[out.length - 1].sec === sec && out[out.length - 1].pi === pi;
    out.push({ sec, pi, h: !!p.h, s, t: toks, cont: a > 0, prevSame, ln: p.ln, lec: p.lec });
  }
  return out;
}
export function notesFor(chap, lnFrom, lnTo) {
  return C.chap[chap].notes.filter(n => n.ln >= lnFrom && n.ln <= lnTo);
}
