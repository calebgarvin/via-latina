// Persistent progress + schedule logic + spaced repetition (SM-2 style).
import * as store from './store.js';
import { ymd, addDays, diffDays, weekday } from './util.js';

export const TOTAL = 312;
let S = null;
let saveT = null;

export function defaults() {
  const today = ymd();
  return {
    v: 1, createdAt: today,
    settings: { startDate: today, restWeekday: 0, theme: 'auto', readSize: 22, showNotes: true, notesInline: true },
    done: {},        // reading day -> date completed
    reviews: {},     // date -> { n: items answered, rest: bool }
    restDone: {},    // week number (1..52) -> date of the rest-stop review
    srs: {},         // lemma id -> card state
    outfit: ['cloak', 'toga', 'satchel', 'laurel'], // equipped when unlocked
    bestStreak: 0, compress: false, lastExport: null, lastExportNag: null, seenChapter: 0,
  };
}
export async function load() {
  S = (await store.get('state')) || defaults();
  const d = defaults();
  S.settings = { ...d.settings, ...(S.settings || {}) };
  for (const k of Object.keys(d)) if (S[k] === undefined) S[k] = d[k];
  return S;
}
export function get() { return S; }
export function save(now = false) {
  clearTimeout(saveT);
  const go = () => store.set('state', S);
  if (now) return go();
  saveT = setTimeout(go, 250);
}
export function replace(newState) { S = newState; return save(true); }

// ---------------------------------------------------------------- schedule
export function isRest(date) { return weekday(date) === S.settings.restWeekday; }
/** number of reading days scheduled from startDate through `date` inclusive */
export function expectedBy(date) {
  const n = diffDays(S.settings.startDate, date) + 1;
  if (n <= 0) return 0;
  const full = Math.floor(n / 7), rem = n % 7;
  let c = full * 6;
  for (let i = 0; i < rem; i++) if (!isRest(addDays(S.settings.startDate, full * 7 + i))) c++;
  return Math.min(TOTAL, c);
}
export function completedCount() { let n = 0; while (S.done[n + 1]) n++; return n; }
export function nextDay() { return Math.min(TOTAL, completedCount() + 1); }
export function behind(today = ymd()) { return Math.max(0, expectedBy(addDays(today, -1)) - completedCount()); }
/** calendar date on which reading day k is scheduled */
export function dateOfDay(k) {
  let d = S.settings.startDate, c = 0;
  // fast-forward whole weeks
  const weeks = Math.floor((k - 1) / 6);
  d = addDays(d, weeks * 7); c = weeks * 6;
  for (;;) { if (!isRest(d)) { c++; if (c >= k) return d; } d = addDays(d, 1); }
}
export function targetDate() { return dateOfDay(TOTAL); }
export function readToday(today = ymd()) { return Object.values(S.done).filter(x => x === today).length; }

/** what the home screen should offer today */
export function todayPlan(today = ymd()) {
  const comp = completedCount();
  if (comp >= TOTAL) return { kind: 'finished' };
  if (comp === 0 && readToday(today) === 0) return { kind: 'read', day: 1, late: 0 };
  const exp = expectedBy(today);
  const late = behind(today);
  const restDay = isRest(today);
  const doneToday = readToday(today);
  const reviewedToday = !!(S.reviews[today] && S.reviews[today].rest);
  if (restDay) {
    if (late > 0) return { kind: 'catchup', day: comp + 1, late };
    if (!reviewedToday) return { kind: 'restreview', day: comp + 1 };
    return { kind: 'ahead', day: comp + 1 };
  }
  if (comp < exp) {
    if (doneToday > 0 && !S.compress && late === 0) return { kind: 'ahead', day: comp + 1 };
    return { kind: 'read', day: comp + 1, late };
  }
  return { kind: 'ahead', day: comp + 1 };
}
/** move the whole plan later by n days (keeps everything done) */
export function pushPlan(n) {
  S.settings.startDate = addDays(S.settings.startDate, n);
  S.compress = false; save();
}

export function markDone(day, today = ymd()) {
  S.done[day] = today;
  logActivity(today, 0);
  if (S.compress && behind(today) === 0) S.compress = false;
  save();
}
export function logActivity(date, n, rest = false) {
  const r = S.reviews[date] || { n: 0 };
  r.n += n; if (rest) r.rest = true;
  S.reviews[date] = r;
  const st = streak();
  if (st > S.bestStreak) S.bestStreak = st;
  save();
}
export function activeOn(date) {
  return Object.values(S.done).includes(date) || !!(S.reviews[date] && (S.reviews[date].n > 0 || S.reviews[date].rest));
}
/** consecutive active days; scheduled rest days never break a streak */
export function streak(today = ymd()) {
  let d = activeOn(today) ? today : addDays(today, -1);
  let n = 0;
  const floor = [S.settings.startDate, S.createdAt, ...Object.values(S.done)].sort()[0];
  for (let guard = 0; guard < 2000 && d >= floor; guard++) {
    if (activeOn(d)) n++;
    else if (!isRest(d)) break;
    d = addDays(d, -1);
  }
  return n;
}
export function projectedFinish(today = ymd()) {
  const comp = completedCount();
  const remaining = TOTAL - comp;
  if (remaining <= 0) return today;
  const since = Math.max(1, Math.min(28, diffDays(S.settings.startDate, today) + 1));
  const from = addDays(today, -since + 1);
  const recent = Object.values(S.done).filter(x => x >= from && x <= today).length;
  const pace = since >= 7 && recent > 0 ? recent / since : 6 / 7;
  return addDays(today, Math.ceil(remaining / pace));
}

// ---------------------------------------------------------------- rewards
export const COINS = [
  { id: 'as', at: 3, name: 'As', note: '3-day streak' },
  { id: 'dupondius', at: 7, name: 'Dupondius', note: '7-day streak' },
  { id: 'sestertius', at: 14, name: 'Sēstertius', note: '14-day streak' },
  { id: 'quinarius', at: 30, name: 'Quīnārius', note: '30-day streak' },
  { id: 'denarius', at: 60, name: 'Dēnārius', note: '60-day streak' },
  { id: 'aureus', at: 120, name: 'Aureus', note: '120-day streak' },
];
export const OUTFITS = [
  { id: 'cloak', afterChapter: 6, name: 'Paenula', note: 'travelling cloak — after Cap. VI (Via Latīna)' },
  { id: 'toga', afterChapter: 14, name: 'Toga', note: 'after Cap. XIV' },
  { id: 'satchel', afterChapter: 15, name: 'Capsa', note: 'school satchel — after Cap. XV' },
  { id: 'laurel', afterChapter: 35, name: 'Corōna laurea', note: 'laurel wreath — the end of the road' },
];
export function chaptersDone(days) {
  const comp = completedCount(); const set = new Set();
  for (const d of days) if (d.chEnd && d.d <= comp) set.add(d.c);
  return set;
}
export function unlockedOutfits(days) {
  const done = chaptersDone(days);
  return OUTFITS.filter(o => done.has(o.afterChapter)).map(o => o.id);
}
export function wornOutfits(days) {
  const un = new Set(unlockedOutfits(days));
  return ['cloak', 'toga', 'satchel', 'laurel'].filter(id => un.has(id) && S.outfit.includes(id));
}

// ---------------------------------------------------------------- SRS (SM-2 variant)
// card: { e: ease, i: interval days, r: successful reps in a row, d: due date, l: lapses, s: last seen }
export function card(lid) { return S.srs[lid]; }
export function introduce(lid, today = ymd()) {
  if (!S.srs[lid]) S.srs[lid] = { e: 2.5, i: 0, r: 0, d: today, l: 0, s: null, n: 1 };
}
export function preview(c) {
  const out = {};
  for (const g of [1, 2, 3, 4]) out[g] = schedule({ ...(c || { e: 2.5, i: 0, r: 0, l: 0 }) }, g).i;
  return out;
}
function schedule(c, grade) { // grade: 1 again, 2 hard, 3 good, 4 easy
  const q = { 1: 1, 2: 3, 3: 4, 4: 5 }[grade];
  c.e = Math.max(1.3, c.e + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02)));
  if (grade === 1) { c.r = 0; c.i = 1; c.l = (c.l || 0) + 1; return c; }
  if (c.r === 0) c.i = { 2: 1, 3: 2, 4: 4 }[grade];
  else if (c.r === 1) c.i = { 2: 3, 3: 6, 4: 9 }[grade];
  else c.i = Math.round(grade === 2 ? c.i * 1.2 : grade === 4 ? c.i * c.e * 1.3 : c.i * c.e);
  c.i = Math.max(1, Math.min(365, c.i));
  c.r += 1;
  return c;
}
export function grade(lid, g, today = ymd()) {
  const c = S.srs[lid] || { e: 2.5, i: 0, r: 0, l: 0 };
  schedule(c, g);
  c.d = addDays(today, c.i); c.s = today;
  S.srs[lid] = c; save();
  return c;
}
export function dueCards(today = ymd()) {
  return Object.entries(S.srs).filter(([, c]) => c.s && c.d <= today).sort((a, b) => a[1].d.localeCompare(b[1].d)).map(([k]) => +k);
}
export function unseenCards() { return Object.entries(S.srs).filter(([, c]) => !c.s).map(([k]) => +k); }
export function wordsLearned() { return Object.values(S.srs).filter(c => c.s && c.r >= 1).length; }
export function wordsSeen() { return Object.values(S.srs).filter(c => c.s).length; }
