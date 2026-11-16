export const $ = (s, el = document) => el.querySelector(s);
export const $$ = (s, el = document) => [...el.querySelectorAll(s)];
export function esc(s) { return String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])); }
export function h(html) { const t = document.createElement('template'); t.innerHTML = html.trim(); return t.content.firstElementChild; }

// ---- dates are local calendar dates as 'YYYY-MM-DD'
export function ymd(d = new Date()) {
  const z = n => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${z(d.getMonth() + 1)}-${z(d.getDate())}`;
}
export function parseYmd(s) { const [y, m, d] = s.split('-').map(Number); return new Date(y, m - 1, d, 12); }
export function addDays(s, n) { const d = parseYmd(s); d.setDate(d.getDate() + n); return ymd(d); }
export function diffDays(a, b) { return Math.round((parseYmd(b) - parseYmd(a)) / 86400000); } // b - a
export function weekday(s) { return parseYmd(s).getDay(); }
export const WD = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
export const WD_LAT = ['diēs Sōlis', 'diēs Lūnae', 'diēs Mārtis', 'diēs Mercuriī', 'diēs Iovis', 'diēs Veneris', 'diēs Sāturnī'];
export function fmtDate(s, opts = { month: 'short', day: 'numeric', year: 'numeric' }) {
  return parseYmd(s).toLocaleDateString(undefined, opts);
}
export function roman(n) {
  let out = '';
  for (const [v, s] of [[1000, 'M'], [900, 'CM'], [500, 'D'], [400, 'CD'], [100, 'C'], [90, 'XC'], [50, 'L'], [40, 'XL'], [10, 'X'], [9, 'IX'], [5, 'V'], [4, 'IV'], [1, 'I']])
    while (n >= v) { out += s; n -= v; }
  return out;
}
export function shuffle(a, rnd = Math.random) { a = a.slice(); for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; }
export function seeded(seed) { let s = seed >>> 0 || 1; return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296); }
let toastT;
export function toast(msg, ms = 2600) {
  const t = document.getElementById('toast'); t.textContent = msg; t.hidden = false;
  clearTimeout(toastT); toastT = setTimeout(() => { t.hidden = true; }, ms);
}
export function vibrate(ms = 8) { try { navigator.vibrate && navigator.vibrate(ms); } catch (e) {} }
