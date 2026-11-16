// Review sessions: flashcards (SM-2), grammar/ending drills, comprehension questions.
import * as S from './state.js';
import * as C from './content.js';
import { esc, h, shuffle, ymd, vibrate } from './util.js';

/** items for the review after reading day n */
export function sessionForDay(n) {
  const d = C.day(n);
  const today = ymd();
  for (const lid of d.new) S.introduce(lid, today);
  const fresh = d.new.filter(l => !S.card(l).s);
  const older = S.unseenCards().filter(l => !d.new.includes(l));
  const due = S.dueCards(today).filter(l => !d.new.includes(l));
  const newPool = [...fresh, ...older];
  const newTake = Math.min(newPool.length, due.length ? 4 : 6);
  const dueTake = Math.min(due.length, Math.max(2, 6 - newTake));
  const cards = [...newPool.slice(0, newTake), ...due.slice(0, dueTake)];
  let drills = shuffle(d.dr).slice(0, 2);
  let comp = shuffle(d.cq).slice(0, 2);
  if (drills.length < 2 && n > 1) drills = drills.concat(shuffle(C.day(n - 1).dr).slice(0, 2 - drills.length));
  if (comp.length < 2 && n > 1) comp = comp.concat(shuffle(C.day(n - 1).cq).slice(0, 2 - comp.length));
  const items = [
    ...cards.map(l => ({ type: 'card', lid: l, isNew: newPool.includes(l) && !S.card(l).s })),
    ...drills.map(x => ({ type: 'mc', q: x })),
    ...comp.map(x => ({ type: 'mc', q: x })),
  ];
  // interleave: cards first (they warm up the vocabulary), then mix drills & comprehension
  return { items, extraDue: due.slice(dueTake) };
}

/** cumulative review for a rest stop (catch-up day when caught up) */
export function sessionForRest(lastDay) {
  const today = ymd();
  // words queued for this rest stop
  for (let k = Math.max(1, lastDay - 5); k <= lastDay; k++) for (const l of (C.day(k).rn || [])) S.introduce(l, today);
  const unseen = S.unseenCards();
  const due = S.dueCards(today);
  let cards = [...unseen.slice(0, 8), ...due.slice(0, 12)];
  if (cards.length < 8) {
    const seen = Object.keys(S.get().srs).map(Number).filter(l => !cards.includes(l));
    cards = cards.concat(shuffle(seen).slice(0, 8 - cards.length));
  }
  const pool = [];
  for (let k = Math.max(1, lastDay - 12); k <= lastDay; k++) { const d = C.day(k); pool.push(...d.dr.map(q => ({ q })), ...d.cq.map(q => ({ q }))); }
  const mcs = shuffle(pool).slice(0, 5).map(x => ({ type: 'mc', q: x.q }));
  return { items: [...cards.map(l => ({ type: 'card', lid: l, isNew: !S.card(l).s })), ...mcs], extraDue: due.slice(12) };
}

export function extraSession(lids) { return { items: lids.slice(0, 20).map(l => ({ type: 'card', lid: l })), extraDue: lids.slice(20) }; }

const DAYS = n => n <= 1 ? '1 day' : n < 30 ? `${n} days` : n < 365 ? `${Math.round(n / 30)} mo` : '1 yr';

function headword(L) {
  const p = L.h.split(' ');
  if (L.p === 'n' || L.p === 'name') return p.length >= 3 ? `${p[0]}, ${p[1]} <i>${p.slice(2).join(' ')}</i>` : esc(L.h);
  if (L.p === 'v' || L.p === 'd') return p.filter(x => x !== '-').join(', ');
  if (L.p === 'a') return p.join(', ');
  return esc(L.h);
}
const POS = { n: 'noun', a: 'adjective', v: 'verb', d: 'deponent verb', adv: 'adverb', prep: 'preposition', conj: 'conjunction', pron: 'pronoun', num: 'numeral', interj: 'interjection', part: 'particle', name: 'name', abbr: 'abbreviation' };
export function describeLemma(L) {
  const p = L.h.split(' ');
  let info = POS[L.p] || L.p;
  if (L.p === 'n') {
    const g = { m: 'masculine', f: 'feminine', n: 'neuter', mf: 'm./f.', fm: 'f./m.' }[p[2]] || p[2];
    const gen = p[1] || '';
    const decl = gen.endsWith('ae') || gen.endsWith('ārum') ? 1 : gen.endsWith('ūs') || gen.endsWith('uum') ? 4 : gen.endsWith('ēī') || gen.endsWith('eī') ? 5 : gen.endsWith('ī') || gen.endsWith('ōrum') ? 2 : 3;
    info += ` · ${g} · ${['', '1st', '2nd', '3rd', '4th', '5th'][decl]} declension${p.includes('pl') ? ' · plural only' : ''}`;
  } else if (L.p === 'v' || L.p === 'd') {
    const inf = p[1] || '';
    const cj = inf.endsWith('āre') || inf.endsWith('ārī') || inf === 'dare' ? '1st' : inf.endsWith('ēre') || inf.endsWith('ērī') ? '2nd' : inf.endsWith('īre') || inf.endsWith('īrī') ? '4th' : p[0].endsWith('iō') || p[0].endsWith('ior') ? '3rd (-iō)' : '3rd';
    const irr = /^(sum|possum|volō|nōlō|mālō|eō|ferō|fīō|edō)$/.test(p[0]) || /(sum|eō|ferō)$/.test(p[0]) && /(esse|īre|ferre)$/.test(inf);
    info += irr ? ' · irregular' : ` · ${cj} conjugation`;
  } else if (L.p === 'a') {
    info += p.length === 3 && (p[1].endsWith('a')) ? ' · 1st/2nd declension' : ' · 3rd declension';
  }
  return info;
}
export { headword };

/** run a session inside `root`; calls onDone({answered, correct}) */
export function runSession(root, session, { title, onDone, onExtra }) {
  const queue = session.items.slice();
  const total = queue.length;
  let idx = 0, answered = 0, correct = 0, again = new Set();
  const today = ymd();

  function dots() {
    return `<div class="progressdots">${session.items.map((_, i) => `<i class="${i < idx ? 'done' : i === idx ? 'on' : ''}"></i>`).join('')}</div>`;
  }
  function next() {
    if (!queue.length) return finish();
    const it = queue.shift();
    if (it.type === 'card') showCard(it); else showMC(it.q);
  }
  function frame(inner) {
    root.innerHTML = `<div class="topbar"><button class="iconbtn" data-x aria-label="Close">✕</button><h1>${esc(title)}</h1><span class="iconbtn"></span></div>${dots()}${inner}`;
    root.querySelector('[data-x]').onclick = () => { if (confirm('Leave this review? Your answers so far are saved.')) onDone({ answered, correct, aborted: true }); };
  }
  function showCard(it) {
    const L = C.lemma(it.lid); const c = S.card(it.lid);
    const prev = S.preview(c);
    const src = L.s ? esc(L.s).replace(esc(L.sf || ''), `<mark>${esc(L.sf || '')}</mark>`) : '';
    frame(`<div class="card flash" data-flip>
      <div class="kind">${it.isNew ? 'Novum vocābulum · new word' : 'Repetītiō · review'}</div>
      <div class="lat">${headword(L)}</div>
      <div class="back" hidden>
        <div class="eng">${esc(L.g)}</div>
        <div class="small muted" style="margin-top:6px">${esc(describeLemma(L))}</div>
        ${src ? `<div class="src">${src}</div><div class="small muted">Cap. ${L.c}</div>` : ''}
      </div>
      <div class="tap">Tap to show the meaning</div>
    </div>
    <div class="grades" hidden>
      <button class="again" data-g="1">Again<small>${DAYS(prev[1])}</small></button>
      <button data-g="2">Hard<small>${DAYS(prev[2])}</small></button>
      <button class="good" data-g="3">Good<small>${DAYS(prev[3])}</small></button>
      <button class="easy" data-g="4">Easy<small>${DAYS(prev[4])}</small></button>
    </div>`);
    const fl = root.querySelector('[data-flip]');
    fl.onclick = () => { fl.querySelector('.back').hidden = false; fl.querySelector('.tap').hidden = true; root.querySelector('.grades').hidden = false; };
    root.querySelectorAll('[data-g]').forEach(b => b.onclick = () => {
      const g = +b.dataset.g; vibrate();
      S.grade(it.lid, g, today); answered++; if (g > 1) correct++;
      if (g === 1 && !again.has(it.lid)) { again.add(it.lid); queue.push({ ...it, isNew: false }); }
      else idx++;
      next();
    });
  }
  function showMC(q) {
    const kinds = { end: 'Terminātiō · choose the ending', case: 'Quis cāsus? · which case?', conj: 'Verbum · conjugate', tf: 'Vērum an falsum?', cloze: 'Quid deest? · what is missing?' };
    let qhtml = esc(q.q);
    if (q.k === 'case' && q.hl) qhtml = esc(q.q).replace(esc(q.hl), `<mark>${esc(q.hl)}</mark>`);
    const opts = q.opts.map((o, i) => `<button data-i="${i}">${esc(o)}${q.en ? `<small>${esc(q.en[i])}</small>` : ''}</button>`).join('');
    frame(`<div class="card">
      <div class="qkind">${kinds[q.k] || ''}</div>
      <div class="q">${qhtml}</div>
      ${q.hint ? `<button class="hintbtn" data-hint>English hint</button><div class="hint" hidden>${esc(q.hint)}</div>` : ''}
      <div class="opts">${opts}</div>
      <div class="why" hidden></div>
    </div>
    <button class="btn" data-next hidden>Continue</button>`);
    const hb = root.querySelector('[data-hint]');
    if (hb) hb.onclick = () => { root.querySelector('.hint').hidden = false; hb.hidden = true; };
    let locked = false;
    root.querySelectorAll('.opts button').forEach(b => b.onclick = () => {
      if (locked) return; locked = true;
      const i = +b.dataset.i; const ok = i === q.a; vibrate(ok ? 8 : 20);
      answered++; if (ok) correct++;
      b.classList.add(ok ? 'right' : 'wrong');
      root.querySelectorAll('.opts button')[q.a].classList.add('right');
      const w = root.querySelector('.why');
      w.innerHTML = (ok ? '<b>Rēctē!</b> ' : '<b>Nōn rēctē.</b> ') + esc(q.why || (q.full ? q.full : ''));
      w.hidden = false;
      const nb = root.querySelector('[data-next]'); nb.hidden = false; nb.onclick = () => { idx++; next(); };
    });
  }
  function finish() {
    S.logActivity(today, answered);
    const extra = session.extraDue.filter(l => { const c = S.card(l); return c && c.d <= today; });
    root.innerHTML = `<div class="celebrate">
      <div class="small muted">RECĒNSIŌ PERFECTA</div>
      <div class="big">${correct} / ${answered}</div>
      <p class="muted">Review complete.</p>
    </div>
    <button class="btn" data-done>Continue</button>
    ${extra.length ? `<button class="btn ghost" style="margin-top:10px" data-extra>Extra practice (${extra.length} more due — optional)</button>` : ''}`;
    root.querySelector('[data-done]').onclick = () => onDone({ answered, correct });
    const eb = root.querySelector('[data-extra]');
    if (eb) eb.onclick = () => onExtra && onExtra(extra);
  }
  next();
}
