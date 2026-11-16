#!/usr/bin/env node
// Validates the course and the art pipeline.
//   node tools/validate.mjs                 uses content-src/work/content.json if present
//   LL_PASSPHRASE=... node tools/validate.mjs --enc   decrypts content.enc instead (checks the shipped file)
// Checks: every day 1-312 has text, vocabulary and review items; no reading ends mid-sentence;
// every asset in assets/assets.json exists and has the declared pixel size. Exit code 1 on failure.
import { readFileSync, existsSync } from 'node:fs';
import { gunzipSync } from 'node:zlib';
import { webcrypto as crypto } from 'node:crypto';
import { createInterface } from 'node:readline';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const errors = [], warnings = [];
const err = m => errors.push(m), warn = m => warnings.push(m);

async function loadContent() {
  const plain = path.join(root, 'content-src', 'work', 'content.json');
  if (!process.argv.includes('--enc') && existsSync(plain)) { console.log('Using', path.relative(root, plain)); return JSON.parse(readFileSync(plain, 'utf8')); }
  const buf = new Uint8Array(readFileSync(path.join(root, 'content.enc')));
  const pass = process.env.LL_PASSPHRASE || await new Promise(r => { const rl = createInterface({ input: process.stdin, output: process.stdout }); rl.question('Passphrase: ', a => { rl.close(); r(a); }); });
  const iter = new DataView(buf.buffer).getUint32(5);
  const salt = buf.slice(9, 25), iv = buf.slice(25, 37), ct = buf.slice(37);
  const base = await crypto.subtle.importKey('raw', new TextEncoder().encode(pass.normalize('NFC')), 'PBKDF2', false, ['deriveKey']);
  const key = await crypto.subtle.deriveKey({ name: 'PBKDF2', salt, iterations: iter, hash: 'SHA-256' }, base, { name: 'AES-GCM', length: 256 }, false, ['decrypt']);
  const pt = new Uint8Array(await crypto.subtle.decrypt({ name: 'AES-GCM', iv }, key, ct));
  console.log('Decrypted content.enc');
  return JSON.parse(gunzipSync(pt).toString('utf8'));
}

function pngSize(file) {
  const b = readFileSync(file);
  if (b.readUInt32BE(0) !== 0x89504e47) return null;
  return [b.readUInt32BE(16), b.readUInt32BE(20)];
}

const C = await loadContent();
const chap = Object.fromEntries(C.chapters.map(c => [c.n, c]));
const days = C.days;
if (days.length !== 312) err(`expected 312 days, found ${days.length}`);
const END_OK = /[.?!:;"'”’)\]—–…]\s*$/;
let words = 0, cutWarn = 0;
const seen = new Set();
for (let k = 1; k <= 312; k++) {
  const d = days[k - 1];
  if (!d || d.d !== k) { err(`day ${k} missing or out of order`); continue; }
  const ch = chap[d.c];
  if (!ch) { err(`day ${k}: unknown chapter ${d.c}`); continue; }
  let text = '', toks = 0, glossed = 0;
  for (const [sec, pi, a, b] of d.r) {
    const p = sec === 'r' ? ch.paras[pi] : ch.gram[pi];
    if (!p) { err(`day ${k}: missing paragraph ${sec}${pi}`); continue; }
    const s = p.s.slice(a, b); text += s + ' ';
    for (const t of p.t) if (t[0] >= a && t[0] < b) { toks++; if (t[2] != null) glossed++; }
    const key = `${d.c}:${sec}:${pi}:${a}`;
    if (seen.has(key)) err(`day ${k}: text slice ${key} is used twice`); seen.add(key);
  }
  words += toks;
  if (!text.trim()) err(`day ${k}: no text`);
  if (toks < 20) warn(`day ${k}: only ${toks} words`);
  if (glossed / Math.max(1, toks) < 0.85) warn(`day ${k}: only ${Math.round(glossed / toks * 100)}% of words have a gloss`);
  // vocabulary: the day must teach or review words
  const vocab = d.new.length + (d.rn || []).length;
  if (glossed === 0) err(`day ${k}: no glossable vocabulary`);
  if (vocab === 0) warn(`day ${k}: introduces no new flashcards (reviews due cards only)`);
  for (const l of [...d.new, ...(d.rn || [])]) if (!C.lemmas[l] || !C.lemmas[l].g) err(`day ${k}: card ${l} has no gloss`);
  // review items
  const items = d.dr.length + d.cq.length;
  if (items === 0) warn(`day ${k}: no drills/comprehension of its own (the app borrows from the previous day)`);
  for (const q of [...d.dr, ...d.cq]) {
    if (!Array.isArray(q.opts) || q.opts.length < 2 || q.a < 0 || q.a >= q.opts.length) err(`day ${k}: malformed question ${JSON.stringify(q).slice(0, 80)}`);
    if (new Set(q.opts).size !== q.opts.length) err(`day ${k}: duplicate options in ${q.q.slice(0, 50)}`);
  }
  // mid-sentence cut: the last slice must end at a paragraph end or a sentence/clause end
  const [sec, pi, a, b] = d.r[d.r.length - 1];
  const p = sec === 'r' ? ch.paras[pi] : ch.gram[pi];
  const atParaEnd = b >= p.s.length;
  if (!atParaEnd && !END_OK.test(p.s.slice(a, b))) { err(`day ${k}: reading ends mid-sentence: "…${p.s.slice(Math.max(a, b - 40), b)}"`); cutWarn++; }
  // and starts at a sentence start
  const [s0, p0, a0] = d.r[0];
  const P0 = s0 === 'r' ? ch.paras[p0] : ch.gram[p0];
  if (a0 > 0 && !END_OK.test(P0.s.slice(0, a0))) err(`day ${k}: reading starts mid-sentence`);
}
// coverage: every paragraph of every chapter belongs to some day
for (const c of C.chapters) {
  c.paras.forEach((p, i) => { if (![...seen].some(k => k.startsWith(`${c.n}:r:${i}:`))) err(`chapter ${c.n} paragraph ${i} is not scheduled`); });
}
// flashcards: every card-eligible lemma that appears is introduced exactly once
const intro = new Map();
for (const d of days) for (const l of [...d.new, ...(d.rn || [])]) { if (intro.has(l)) err(`card ${l} introduced twice`); intro.set(l, d.d); }
const cards = C.lemmas.filter(l => l.card);
for (const l of cards) if (!intro.has(l.i)) warn(`card ${l.h} never introduced`);

// ------------------------------------------------------------ assets
const M = JSON.parse(readFileSync(path.join(root, 'assets', 'assets.json'), 'utf8'));
let bytes = 0, nAssets = 0;
for (const [id, a] of Object.entries(M.assets)) {
  nAssets++;
  const f = path.join(root, 'assets', a.file);
  if (!existsSync(f)) { err(`asset ${id}: file missing (${a.file})`); continue; }
  bytes += readFileSync(f).length;
  const sz = pngSize(f);
  if (!sz) { err(`asset ${id}: not a PNG`); continue; }
  let ew = a.w * (a.frames || 1), eh = a.h * ((a.rows && a.rows.length) || 1);
  if (id === 'font_roman') { ew = a.glyphs.length * a.advance; eh = a.h; }
  if (sz[0] !== ew || sz[1] !== eh) err(`asset ${id}: size ${sz[0]}x${sz[1]}, assets.json expects ${ew}x${eh}`);
}
for (const [k, d] of Object.entries(M.districts)) {
  if (!M.assets[d.bg]) err(`district ${k}: background ${d.bg} not in assets`);
  for (const p of d.props) if (!M.assets[p]) err(`district ${k}: prop ${p} not in assets`);
}
if (M.chapterDistricts.length !== 35) err('chapterDistricts must list 35 chapters');
for (const req of ['hero_base', 'tile_via', 'landmark_milestone', 'landmark_arch', 'landmark_capitolium', 'landmark_fountain', 'landmark_shrine', 'wp_done', 'wp_current', 'wp_locked', 'wp_rest', 'ui_frame', 'font_roman'])
  if (!M.assets[req]) err(`required asset ${req} missing from assets.json`);
if (bytes > 5 * 1024 * 1024) err(`assets total ${(bytes / 1048576).toFixed(1)} MB > 5 MB`);

console.log(`Days: ${days.length} · words scheduled: ${words} · avg ${Math.round(words / days.length)}/day · cards: ${cards.length}`);
console.log(`Assets: ${nAssets} files, ${(bytes / 1024).toFixed(0)} KB`);
if (warnings.length) { console.log(`\n${warnings.length} warning(s):`); for (const w of warnings.slice(0, 40)) console.log('  ⚠ ' + w); if (warnings.length > 40) console.log(`  … ${warnings.length - 40} more`); }
if (errors.length) { console.log(`\n${errors.length} error(s):`); for (const e of errors.slice(0, 60)) console.log('  ✗ ' + e); process.exit(1); }
console.log('\n✓ All checks passed.');
