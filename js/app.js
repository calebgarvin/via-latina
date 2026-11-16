// Via Latina — main application (screens + routing).
import * as S from './state.js';
import * as C from './content.js';
import * as store from './store.js';
import { loadArt, url as artUrl } from './art.js';
import { mountMap, buildNodes, destroy as destroyMap } from './map.js';
import { sessionForDay, sessionForRest, extraSession, runSession, describeLemma, headword } from './review.js';
import { $, esc, h, ymd, addDays, diffDays, fmtDate, roman, toast, WD, parseYmd } from './util.js';

const app = document.getElementById('app');
const pct = c => { const v = c / S.TOTAL * 100; return v > 0 && v < 10 ? v.toFixed(1) : Math.round(v); };
const sheet = document.getElementById('sheet');
let mapApi = null, nodes = null;
let tab = 'via';

// ---------------------------------------------------------------- boot
async function boot() {
  if ('serviceWorker' in navigator) navigator.serviceWorker.register('sw.js').catch(() => {});
  await S.load();
  applySettings();
  const [ok] = await Promise.all([C.tryCachedKey().catch(() => false), loadArt().catch(e => console.warn(e))]);
  if (ok) start(); else lockScreen();
}
function applySettings() {
  const s = S.get().settings;
  if (s.theme === 'auto') delete document.documentElement.dataset.theme; else document.documentElement.dataset.theme = s.theme;
  document.documentElement.style.setProperty('--read-size', s.readSize + 'px');
}

function lockScreen(msg = '') {
  destroyMap();
  app.innerHTML = `<div class="lock">
    <img class="seal" src="${artUrl('app_icon_192') || 'icons/icon-192.png'}" alt="">
    <h1>VIA LATINA</h1>
    <p>Private reader. Enter your passphrase to unlock the book on this device.</p>
    <form id="lf">
      <input id="pw" type="password" autocomplete="current-password" placeholder="Passphrase" autocapitalize="off" autocorrect="off" spellcheck="false">
      <div class="err" id="err">${esc(msg)}</div>
      <button class="btn" id="go">Unlock</button>
    </form>
    <p class="small" style="margin-top:20px">You only need to do this once per device.</p>
  </div>`;
  $('#lf').onsubmit = async e => {
    e.preventDefault();
    const pw = $('#pw').value; if (!pw) return;
    $('#go').disabled = true; $('#go').textContent = 'Unlocking…'; $('#err').textContent = '';
    try { await C.unlock(pw); await store.persist(); start(); }
    catch (err) {
      console.warn(err);
      $('#go').disabled = false; $('#go').textContent = 'Unlock';
      $('#err').textContent = /content\.enc|fetch/i.test(String(err)) ? 'Could not load the content file. Check your connection for the first launch.' : 'That passphrase did not work.';
    }
  };
}

function start() {
  store.persist();
  nodes = buildNodes(C.days());
  const st = S.get();
  if (!st.settings.onboarded) return onboarding();
  go('via');
}

// ---------------------------------------------------------------- shell
function shell(inner, active) {
  destroyMap();
  app.innerHTML = `<div class="screen" id="scr">${inner}</div>${tabbar(active)}`;
  bindTabs();
  window.scrollTo(0, 0);
  return $('#scr');
}
function tabbar(active) {
  const T = [['via', '⛬', 'Via'], ['liber', '❧', 'Liber'], ['progressus', '⚱', 'Progressus'], ['optiones', '⚙', 'Optiōnēs']];
  return `<nav class="tabbar">${T.map(([id, ic, lb]) => `<button data-tab="${id}" ${active === id ? 'aria-current="page"' : ''}><span class="ti">${ic}</span>${lb}</button>`).join('')}</nav>`;
}
function bindTabs() { app.querySelectorAll('[data-tab]').forEach(b => b.onclick = () => go(b.dataset.tab)); }
function go(t, arg) {
  tab = t; closeSheet();
  if (t === 'via') return home(arg);
  if (t === 'liber') return library();
  if (t === 'progressus') return progress();
  if (t === 'optiones') return settings();
}

// ---------------------------------------------------------------- onboarding
function onboarding() {
  const st = S.get().settings;
  app.innerHTML = `<div class="screen"><div class="readhead" style="margin-top:24px"><div class="cap">SALVĒ!</div><div class="ttl">Familia Rōmāna in one year</div>
    <div class="meta">312 readings · 10–15 minutes a day</div></div>
    <div class="card">
      <label class="field"><span>Start date</span><input type="date" id="sd" value="${st.startDate}"></label>
      <label class="field"><span>Catch-up / review day</span><select id="rw">${WD.map((w, i) => `<option value="${i}" ${i === st.restWeekday ? 'selected' : ''}>${w}</option>`).join('')}</select></label>
      <p class="small muted" id="fin"></p>
    </div>
    <div class="card small">Each day: read a short passage (tap any word for its meaning), then a quick review of 6–10 items. Finish the review and your traveller walks one stop further along the road to the Capitol. On the catch-up day you catch up if you're behind, or do a relaxed cumulative review if you're not.</div>
    <button class="btn" id="go">Begin the journey</button></div>`;
  const upd = () => { S.get().settings.startDate = $('#sd').value || ymd(); S.get().settings.restWeekday = +$('#rw').value; $('#fin').textContent = 'Planned finish: ' + fmtDate(S.targetDate()); };
  $('#sd').onchange = upd; $('#rw').onchange = upd; upd();
  $('#go').onclick = () => { S.get().settings.onboarded = true; S.save(true); go('via', { titleCard: 1 }); };
}

// ---------------------------------------------------------------- home / map
function nodeIndexOfDay(d) { return nodes.findIndex(n => n.type === 'read' && n.day === d); }
function heroNodeIndex() {
  const comp = S.completedCount();
  if (comp >= S.TOTAL) return nodes.length - 1;
  return nodeIndexOfDay(comp + 1);
}
function statusOf(n) {
  const comp = S.completedCount(); const st = S.get();
  if (n.type === 'rest') return st.restDone[n.week] || comp > n.afterDay ? 'done' : 'locked';
  if (n.day <= comp) return 'done';
  if (n.day === comp + 1) return 'current';
  return 'locked';
}

function home(opts = {}) {
  const st = S.get();
  const plan = S.todayPlan();
  const comp = S.completedCount();
  const cur = C.day(Math.min(S.TOTAL, comp + 1));
  const ch = C.chapter(cur.c);
  const late = S.behind();
  app.innerHTML = `<div class="maphud"><div class="hudcard">
      <div class="hudrow">
        <div class="grow"><div class="hudtitle">Cap. ${roman(ch.n)} · ${esc(ch.title)}</div>
        <div class="hudsub">Diēs ${Math.min(comp + 1, S.TOTAL)} / ${S.TOTAL} · ${pct(comp)}%</div></div>
        <div class="hudstat"><b>${S.streak()}</b>streak</div>
        <div class="hudstat"><b>${S.wordsLearned()}</b>words</div>
      </div>
      <div id="banners"></div>
    </div></div>
    <button class="recenter" id="rc" aria-label="Show my position">◎</button>
    <div class="mapcta"><button class="btn" id="cta"></button></div>
    ${tabbar('via')}`;
  bindTabs();
  mapApi = mountMap(app, { days: C.days(), nodes, statusOf, heroNode: opts.fromNode ?? heroNodeIndex(),
    outfit: S.wornOutfits(C.days()), onTap: tapNode });
  $('#rc').onclick = () => mapApi.centerOn(heroNodeIndex());

  // call to action
  const cta = $('#cta');
  const labels = {
    read: [`Read today · Diēs ${plan.day}`, () => reader(plan.day, 'today')],
    catchup: [`Catch-up reading · Diēs ${plan.day}`, () => reader(plan.day, 'today')],
    restreview: ['Rest stop · cumulative review', () => restReview()],
    ahead: [`Done for today ✓ · read ahead (Diēs ${plan.day})`, () => reader(plan.day, 'today')],
    finished: ['FINIS · You reached the Capitol', () => go('progressus')],
  };
  const [lab, fn] = labels[plan.kind];
  cta.textContent = lab; cta.onclick = fn;
  if (plan.kind === 'ahead') cta.classList.add('secondary');

  // banners
  const bn = $('#banners');
  if (late > 6 && !st.compress) {
    bn.appendChild(h(`<div class="banner">You're ${late} readings behind — that's fine. Choose what suits you:
      <div class="row"><button class="btn secondary" id="cmp">Double up until caught up</button><button class="btn secondary" id="psh">Move the finish date</button></div></div>`));
    $('#cmp').onclick = () => { st.compress = true; S.save(); toast('Two readings a day until you catch up.'); home(); };
    $('#psh').onclick = () => { S.pushPlan(late); toast('Plan moved — new finish ' + fmtDate(S.targetDate())); home(); };
  } else if (st.compress) {
    bn.appendChild(h(`<div class="banner small">Catching up: two readings a day (${late} to go). <a href="#" id="stopc">Stop</a></div>`));
    $('#stopc').onclick = e => { e.preventDefault(); st.compress = false; S.save(); home(); };
  }
  const lastExp = st.lastExport || st.createdAt;
  if (diffDays(lastExp, ymd()) >= 30 && (!st.lastExportNag || diffDays(st.lastExportNag, ymd()) >= 7) && comp > 0) {
    bn.appendChild(h(`<div class="banner small">It's been a month since your last backup. A quick export keeps a year of progress safe.
      <div class="row"><button class="btn secondary" id="exp">Export backup</button><button class="btn ghost" id="later">Later</button></div></div>`));
    $('#exp').onclick = () => exportBackup().then(() => home());
    $('#later').onclick = () => { st.lastExportNag = ymd(); S.save(); home(); };
  }

  // walking animation after completing a day
  if (opts.walkTo != null) {
    setTimeout(() => mapApi.walkTo(opts.walkTo, () => {
      if (opts.after) opts.after();
    }), 350);
  } else if (opts.titleCard) {
    titleCard(opts.titleCard);
  }
}

function tapNode(n) {
  const s = statusOf(n);
  if (n.type === 'rest') {
    const w = S.get().restDone[n.week];
    toast(`Statiō ${roman(n.week)} · ${w ? 'reviewed ' + fmtDate(w) : s === 'done' ? 'passed' : 'rest stop ahead'}`);
    return;
  }
  if (s === 'done') return reader(n.day, 'browse');
  if (s === 'current') return reader(n.day, 'today');
  toast(`Diēs ${n.day} · Cap. ${roman(n.chap)} — not yet unlocked`);
}

function titleCard(chapN, done) {
  const ch = C.chapter(chapN);
  const el = h(`<div class="titlecard"><div class="tc">
    <div class="cap">${esc(ch.cap)}</div><div class="ttl">${esc(ch.title)}</div>
    <div class="sub">${chapN === 1 ? 'The road begins. Tap to continue.' : 'A new district of the road. Tap to continue.'}</div></div></div>`);
  document.body.appendChild(el);
  el.onclick = () => { el.remove(); done && done(); };
  S.get().seenChapter = Math.max(S.get().seenChapter || 0, chapN); S.save();
}

// ---------------------------------------------------------------- reader
function tokenSpans(par, newSet) {
  const s = par.s; let out = ''; let last = 0;
  for (const t of par.t) {
    const [a, len, lid, alts, ln] = t;
    out += esc(s.slice(last, a));
    const w = s.slice(a, a + len);
    if (lid == null) out += esc(w);
    else out += `<span class="w${newSet.has(lid) ? ' new' : ''}" data-l="${lid}" data-a="${(alts || []).join(',')}" data-ln="${ln}">${esc(w)}</span>`;
    last = a + len;
  }
  return out + esc(s.slice(last));
}
function renderReading(n, { notes = true, cls = '' } = {}) {
  const d = C.day(n); const ch = C.chapter(d.c);
  const pars = C.readingOf(n);
  const newSet = new Set(d.new);
  for (const p of pars) for (const t of p.t) if (t[2] != null && C.lemma(t[2]).fd === n && C.lemma(t[2]).p !== 'name') newSet.add(t[2]);
  const usedNotes = new Set();
  let html = `<div class="reader ${cls}" data-chap="${d.c}">`;
  let inGram = false;
  for (const p of pars) {
    if (p.sec === 'g' && !inGram) { html += `<div class="gramhead">GRAMMATICA LATINA</div><div class="gram">`; inGram = true; }
    const lns = p.t.map(t => t[4]);
    html += `<p class="${p.h ? 'h' : ''}" ${p.cont ? 'style="text-indent:0"' : ''}>${tokenSpans(p, newSet)}</p>`;
    if (notes && p.sec === 'r' && lns.length) {
      const lo = Math.min(...lns), hi = Math.max(...lns);
      for (const nt of C.notesFor(d.c, lo, hi)) {
        const key = nt.ln + nt.s; if (usedNotes.has(key)) continue; usedNotes.add(key);
        html += `<span class="note">${esc(nt.s.replace(/ \/ /g, '\n'))}</span>`;
      }
    }
  }
  if (inGram) html += '</div>';
  return html + '</div>';
}

function reader(n, mode) {
  const d = C.day(n); const ch = C.chapter(d.c);
  const st = S.get();
  const lec = d.lec === 9 ? 'Grammatica' : `Lectiō ${roman(d.lec)}`;
  const scr = shell(`<div class="topbar"><button class="iconbtn" id="back" aria-label="Back">‹</button><h1>Diēs ${n}</h1>
      <button class="iconbtn" id="aa" aria-label="Text size">Aa</button></div>
    <div class="readhead"><div class="cap">${esc(ch.cap)}</div><div class="ttl">${esc(ch.title)}</div>
      <div class="meta">${lec} · ${d.w} words${d.new.length ? ` · <span class="pill">${d.new.length} new words underlined</span>` : ''}</div></div>
    ${n > 1 ? `<button class="prevtoggle" id="prev">Show the previous reading (Diēs ${n - 1})</button><div id="prevbox"></div>` : ''}
    <div id="today">${renderReading(n, { notes: st.settings.showNotes })}</div>
    <p class="small muted center" style="margin-top:22px">Tap any word for its meaning and the margin note.</p>
    ${mode === 'today' ? `<button class="btn" id="rev">Ad recēnsiōnem · to the review →</button>` : `<button class="btn secondary" id="again">Practise this day again (optional)</button>`}
  `, tab);
  $('#back').onclick = () => go(mode === 'browse' && tab === 'liber' ? 'liber' : 'via');
  $('#aa').onclick = () => {
    const sizes = [18, 20, 22, 25, 28]; const i = (sizes.indexOf(st.settings.readSize) + 1) % sizes.length;
    st.settings.readSize = sizes[i]; S.save(); applySettings();
  };
  const pv = $('#prev');
  if (pv) pv.onclick = () => {
    const box = $('#prevbox');
    if (box.innerHTML) { box.innerHTML = ''; pv.textContent = `Show the previous reading (Diēs ${n - 1})`; return; }
    box.innerHTML = renderReading(n - 1, { notes: false, cls: 'prev' }) + '<hr style="border:0;border-top:1px solid var(--line);margin:18px 0">';
    pv.textContent = 'Hide the previous reading';
  };
  scr.addEventListener('click', e => {
    const w = e.target.closest('.w'); if (!w) return;
    scr.querySelectorAll('.w.sel').forEach(x => x.classList.remove('sel')); w.classList.add('sel');
    const chap = +w.closest('.reader').dataset.chap;
    showGloss(w.textContent, +w.dataset.l, (w.dataset.a || '').split(',').filter(Boolean).map(Number), chap, +w.dataset.ln);
  });
  const rv = $('#rev');
  if (rv) rv.onclick = () => review(n);
  const ag = $('#again');
  if (ag) ag.onclick = () => {
    const sess = sessionForDay(n);
    reviewScreen(sess, `Diēs ${n} · practice`, () => reader(n, 'browse'));
  };
}

function showGloss(form, lid, alts, chap, ln) {
  const L = C.lemma(lid);
  alts = alts.filter(a => C.lemma(a).c <= chap && C.lemma(a).p !== 'abbr');
  const notes = C.notesFor(chap, ln - 1, ln + 1);
  sheet.innerHTML = `<div class="grab"></div>
    <div class="form">${esc(form)}</div>
    <div class="head">${headword(L)}</div>
    <div class="gloss">${esc(L.g)}</div>
    <div class="pos">${esc(describeLemma(L))}${L.c ? ` · first in Cap. ${roman(L.c)}` : ''}</div>
    ${notes.map(n => `<div class="snote">${esc(n.s.replace(/ \/ /g, '\n'))}</div>`).join('')}
    ${alts.length ? `<div class="alt">Could also be: ${alts.map(a => { const A = C.lemma(a); return `<b>${esc(A.h.split(' ')[0])}</b> (${esc(A.g)})`; }).join('; ')}</div>` : ''}`;
  sheet.hidden = false;
  setTimeout(() => document.addEventListener('click', closeOnOutside, { once: true, capture: true }), 0);
}
function closeOnOutside(e) {
  if (sheet.contains(e.target)) { document.addEventListener('click', closeOnOutside, { once: true, capture: true }); return; }
  if (e.target.closest && e.target.closest('.w')) return; // another word: handler re-opens
  closeSheet();
}
function closeSheet() { sheet.hidden = true; document.querySelectorAll('.w.sel').forEach(x => x.classList.remove('sel')); }

// ---------------------------------------------------------------- review + completion
function reviewScreen(sess, title, onDone, onComplete) {
  const scr = shell('', tab);
  app.querySelector('.tabbar').remove();
  runSession(scr, sess, {
    title,
    onDone: r => (r.aborted ? onDone(r) : (onComplete || onDone)(r)),
    onExtra: lids => reviewScreen(extraSession(lids), 'Extra practice', onDone, onDone),
  });
}

function review(n) {
  const sess = sessionForDay(n);
  reviewScreen(sess, `Diēs ${n} · recēnsiō`, () => reader(n, 'today'), () => complete(n));
}

function complete(n) {
  const before = heroNodeIndex();
  const prevChap = C.day(n).c;
  S.markDone(n);
  const after = heroNodeIndex();
  const d = C.day(n);
  const nextDay = n < S.TOTAL ? C.day(n + 1) : null;
  const newChapter = nextDay && nextDay.c !== prevChap;
  const unlockedBefore = new Set(S.unlockedOutfits(C.days().filter(x => x.d < n)));
  go('via', {
    fromNode: before, walkTo: after,
    after: () => {
      const showSummary = () => summary(n, unlockedBefore);
      if (newChapter) titleCard(nextDay.c, showSummary); else showSummary();
    },
  });
}

function summary(n, unlockedBefore) {
  const comp = S.completedCount();
  const newly = S.unlockedOutfits(C.days()).filter(o => !unlockedBefore.has(o));
  const coin = S.COINS.filter(c => c.at === S.streak())[0];
  const d = C.day(n);
  const chDone = d.chEnd;
  const el = h(`<div class="titlecard"><div class="tc">
    <div class="cap">DIĒS ${n} PERFECTUS</div>
    <div class="ttl">${comp === S.TOTAL ? 'FINIS!' : 'Bene fēcistī!'}</div>
    <div class="sub">Streak: <b>${S.streak()}</b> · ${pct(comp)}% of the book · ${S.wordsLearned()} words learned</div>
    ${chDone ? `<div class="sub">Capitulum ${roman(d.c)} complete — an inscription has been added to your collection.</div>` : ''}
    ${newly.map(o => `<div class="sub">New garment unlocked: <b>${esc(S.OUTFITS.find(x => x.id === o).name)}</b></div>`).join('')}
    ${coin ? `<div class="sub">You earned a coin: <b>${esc(coin.name)}</b></div>` : ''}
    <div class="sub">Tap to continue</div></div></div>`);
  document.body.appendChild(el);
  el.onclick = () => { el.remove(); home(); };
}

function restReview() {
  const comp = S.completedCount();
  const sess = sessionForRest(comp);
  reviewScreen(sess, 'Statiō · cumulative review', () => go('via'), r => {
    const st = S.get(); const week = Math.max(1, Math.ceil(comp / 6));
    st.restDone[week] = ymd(); S.logActivity(ymd(), 0, true); S.save();
    toast('Rest stop complete. Requiēsce!');
    go('via');
  });
}

// ---------------------------------------------------------------- library (browse chapters & completed days)
function library() {
  const comp = S.completedCount();
  const days = C.days();
  const chs = C.data().chapters;
  const scr = shell(`<div class="topbar"><span class="iconbtn"></span><h1>Liber</h1><span class="iconbtn"></span></div>
    <p class="small muted">Completed readings can be reopened at any time. Future readings unlock as you travel.</p>
    <ul class="list chaplist">${chs.map(c => {
      const ds = days.filter(d => d.c === c.n);
      const doneN = ds.filter(d => d.d <= comp).length;
      return `<li data-c="${c.n}"><div><div class="latin"><b>${roman(c.n)}.</b> ${esc(c.title)}</div><div class="small muted">Diēs ${ds[0].d}–${ds[ds.length - 1].d}</div></div><span class="pill">${doneN}/${ds.length}</span></li>`;
    }).join('')}</ul>`, 'liber');
  scr.querySelectorAll('[data-c]').forEach(li => li.onclick = () => chapterDays(+li.dataset.c));
}
function chapterDays(cn) {
  const comp = S.completedCount();
  const ds = C.days().filter(d => d.c === cn); const ch = C.chapter(cn);
  const scr = shell(`<div class="topbar"><button class="iconbtn" id="back">‹</button><h1>Cap. ${roman(cn)}</h1><span class="iconbtn"></span></div>
    <div class="readhead"><div class="cap">${esc(ch.cap)}</div><div class="ttl">${esc(ch.title)}</div></div>
    <ul class="list chaplist">${ds.map(d => {
      const st = d.d <= comp ? 'done' : d.d === comp + 1 ? 'current' : 'locked';
      const first = C.readingOf(d.d).find(p => !p.h);
      const preview = st === 'locked' ? '' : esc((first ? first.s : '').slice(0, 70)) + '…';
      return `<li data-d="${d.d}" data-s="${st}"><div><b>Diēs ${d.d}</b> <span class="small muted">${d.lec === 9 ? 'Grammatica' : 'Lectiō ' + roman(d.lec)}</span><div class="small muted latin">${preview}</div></div><span class="pill">${st === 'done' ? '✓' : st === 'current' ? 'today' : '🔒'}</span></li>`;
    }).join('')}</ul>`, 'liber');
  $('#back').onclick = () => library();
  scr.querySelectorAll('[data-d]').forEach(li => li.onclick = () => {
    const s = li.dataset.s; const dn = +li.dataset.d;
    if (s === 'done') reader(dn, 'browse'); else if (s === 'current') reader(dn, 'today'); else toast('Not yet unlocked.');
  });
}

// ---------------------------------------------------------------- progress
let calMonth = null;
function progress() {
  const st = S.get(); const comp = S.completedCount();
  const cur = C.day(Math.min(S.TOTAL, comp + 1)); const ch = C.chapter(cur.c);
  const target = S.targetDate(), proj = S.projectedFinish();
  const delta = diffDays(target, proj);
  const days = C.days();
  const chDone = S.chaptersDone(days);
  const unlocked = new Set(S.unlockedOutfits(days));
  const best = Math.max(st.bestStreak, S.streak());
  const scr = shell(`<div class="topbar"><span class="iconbtn"></span><h1>Progressus</h1><span class="iconbtn"></span></div>
    <div class="stats">
      <div class="stat"><b>${S.streak()}</b><span>day streak (best ${best})</span></div>
      <div class="stat"><b>${pct(comp)}%</b><span>${comp} of ${S.TOTAL} readings</span></div>
      <div class="stat"><b>${S.wordsLearned()}</b><span>words learned (${S.wordsSeen()} seen)</span></div>
      <div class="stat"><b class="latin" style="font-size:20px">Cap. ${roman(cur.c)}</b><span>${esc(ch.title)} · ${cur.lec === 9 ? 'Grammatica' : 'Lectiō ' + roman(cur.lec)}</span></div>
    </div>
    <div class="card"><div class="bar"><i style="width:${(comp / S.TOTAL * 100).toFixed(1)}%"></i></div>
      <p class="small" style="margin:10px 0 0">Target finish: <b>${fmtDate(target)}</b><br>Projected at your recent pace: <b>${fmtDate(proj)}</b>
      <span class="muted">${delta > 3 ? `(${delta} days later — no rush)` : delta < -3 ? `(${-delta} days early)` : '(on track)'}</span></p></div>
    <h2 class="sect">Calendar</h2><div class="card" id="cal"></div>
    <h2 class="sect">Wardrobe</h2>
    <div class="wardrobe">${[{ id: 'tunic', name: 'Tunica', note: 'always worn' }, ...S.OUTFITS].map(o => {
      const un = o.id === 'tunic' || unlocked.has(o.id); const on = o.id === 'tunic' || st.outfit.includes(o.id);
      return `<button data-o="${o.id}" class="${un && on ? 'on' : ''}" ${un && o.id !== 'tunic' ? '' : 'disabled'}><img src="${artUrl('icon_' + o.id)}" alt="">${esc(o.name)}<div class="small muted">${un ? (on ? 'worn' : 'tap to wear') : esc(o.note)}</div></button>`;
    }).join('')}</div>
    <h2 class="sect">Coins (streaks)</h2>
    <div class="rewards">${S.COINS.map(c => `<div class="reward ${best >= c.at ? 'on' : 'locked'}"><img src="${artUrl('coin_' + c.id)}" alt="">${esc(c.name)}<br><span class="small">${esc(c.note)}</span></div>`).join('')}</div>
    <h2 class="sect">Inscriptions (chapters)</h2>
    <div class="rewards">${C.data().chapters.map(c => `<div class="tablet ${chDone.has(c.n) ? '' : 'locked'}" style="background-image:url('${artUrl('ui_tablet')}')">${chDone.has(c.n) ? esc(c.title.toUpperCase().replace(/U/g, 'V')) : roman(c.n)}</div>`).join('')}</div>
  `, 'progressus');
  scr.querySelectorAll('[data-o]').forEach(b => b.onclick = () => {
    const id = b.dataset.o; const i = st.outfit.indexOf(id);
    if (i >= 0) st.outfit.splice(i, 1); else st.outfit.push(id);
    S.save(); progress();
  });
  calMonth = calMonth || ymd().slice(0, 7);
  drawCal();
}
function drawCal() {
  const st = S.get(); const el = $('#cal'); if (!el) return;
  const [y, m] = calMonth.split('-').map(Number);
  const first = new Date(y, m - 1, 1); const daysIn = new Date(y, m, 0).getDate();
  const today = ymd();
  const readOn = new Set(Object.values(st.done));
  let cells = '';
  for (let i = 0; i < first.getDay(); i++) cells += '<div class="dd blank"></div>';
  for (let d = 1; d <= daysIn; d++) {
    const s = `${y}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
    const cls = readOn.has(s) ? 'read' : (st.reviews[s] && (st.reviews[s].n > 0 || st.reviews[s].rest)) ? 'rev' : S.isRest(s) ? 'rest' : '';
    cells += `<div class="dd ${cls} ${s === today ? 'today' : ''}">${d}</div>`;
  }
  el.innerHTML = `<div class="calhead"><button class="iconbtn" id="pm">‹</button><span>${first.toLocaleDateString(undefined, { month: 'long', year: 'numeric' })}</span><button class="iconbtn" id="nm">›</button></div>
    <div class="cal">${['S', 'M', 'T', 'W', 'T', 'F', 'S'].map(x => `<div class="dh">${x}</div>`).join('')}${cells}</div>
    <p class="small muted" style="margin:10px 0 0"><span class="pill" style="background:var(--accent);color:#fff8ee">reading</span> <span class="pill" style="background:var(--gold);color:#2b1d16">review only</span> <span class="pill">dashed = rest day</span></p>`;
  const shift = k => { const dt = new Date(y, m - 1 + k, 1); calMonth = `${dt.getFullYear()}-${String(dt.getMonth() + 1).padStart(2, '0')}`; drawCal(); };
  $('#pm').onclick = () => shift(-1); $('#nm').onclick = () => shift(1);
}

// ---------------------------------------------------------------- settings + backup
function settings() {
  const st = S.get(); const s = st.settings;
  const scr = shell(`<div class="topbar"><span class="iconbtn"></span><h1>Optiōnēs</h1><span class="iconbtn"></span></div>
    <h2 class="sect">Schedule</h2>
    <div class="card">
      <label class="field"><span>Start date</span><input type="date" id="sd" value="${s.startDate}"></label>
      <label class="field"><span>Catch-up / review day</span><select id="rw">${WD.map((w, i) => `<option value="${i}" ${i === s.restWeekday ? 'selected' : ''}>${w}</option>`).join('')}</select></label>
      <p class="small muted">Target finish: ${fmtDate(S.targetDate())}. Changing these only moves the calendar; nothing you've done is lost.</p>
    </div>
    <h2 class="sect">Reading</h2>
    <div class="card">
      <label class="field"><span>Theme</span><select id="th">${['auto', 'light', 'dark'].map(t => `<option ${t === s.theme ? 'selected' : ''}>${t}</option>`).join('')}</select></label>
      <label class="field"><span>Text size</span><select id="rs">${[18, 20, 22, 25, 28].map(t => `<option ${t === s.readSize ? 'selected' : ''}>${t}</option>`).join('')}</select></label>
      <label class="field"><span>Margin notes in the text</span><select id="sn"><option value="1" ${s.showNotes ? 'selected' : ''}>shown</option><option value="0" ${!s.showNotes ? 'selected' : ''}>hidden (still shown when you tap a word)</option></select></label>
    </div>
    <h2 class="sect">Backup</h2>
    <div class="card">
      <p class="small" style="margin-top:0">Your progress lives only on this device. Export a backup file now and then (Files, iCloud Drive, or email it to yourself).
      Last backup: <b>${st.lastExport ? fmtDate(st.lastExport) : 'never'}</b>.</p>
      <div class="row"><button class="btn" id="exp">Export backup</button><button class="btn secondary" id="imp">Import backup</button></div>
      <input type="file" id="file" accept="application/json,.json" hidden>
    </div>
    <h2 class="sect">Device</h2>
    <div class="card">
      <p class="small" style="margin-top:0" id="persist">Checking storage…</p>
      <button class="btn secondary" id="lockb">Forget passphrase on this device</button>
    </div>
    <p class="small muted center">Via Latina · content ${C.data().meta.cards} vocabulary cards · ${S.TOTAL} readings</p>`, 'optiones');
  $('#sd').onchange = e => { s.startDate = e.target.value || s.startDate; S.save(); settings(); };
  $('#rw').onchange = e => { s.restWeekday = +e.target.value; S.save(); settings(); };
  $('#th').onchange = e => { s.theme = e.target.value; S.save(); applySettings(); };
  $('#rs').onchange = e => { s.readSize = +e.target.value; S.save(); applySettings(); };
  $('#sn').onchange = e => { s.showNotes = e.target.value === '1'; S.save(); };
  $('#exp').onclick = () => exportBackup().then(() => settings());
  $('#imp').onclick = () => $('#file').click();
  $('#file').onchange = e => importBackup(e.target.files[0]);
  $('#lockb').onclick = async () => { if (confirm('Remove the cached key? You will need the passphrase again. Progress is kept.')) { await C.lock(); lockScreen(); } };
  (async () => {
    let p = false; try { p = navigator.storage && (await navigator.storage.persisted()); } catch (e) {}
    $('#persist') && ($('#persist').textContent = p ? 'Storage is persistent on this device.' : 'Storage is "best effort" — adding the app to your Home Screen and exporting backups keeps progress safe.');
  })();
}

async function exportBackup() {
  const st = S.get();
  st.lastExport = ymd();
  const data = JSON.stringify({ app: 'via-latina', format: 1, exportedAt: new Date().toISOString(), state: st }, null, 1);
  const name = `via-latina-backup-${ymd()}.json`;
  const file = new File([data], name, { type: 'application/json' });
  try {
    if (navigator.canShare && navigator.canShare({ files: [file] })) {
      await navigator.share({ files: [file], title: 'Via Latina backup' });
      S.save(true); toast('Backup exported.'); return;
    }
  } catch (e) { if (e && e.name === 'AbortError') { st.lastExport = null; return; } }
  const a = document.createElement('a'); a.href = URL.createObjectURL(file); a.download = name;
  document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(a.href), 5000);
  S.save(true); toast('Backup downloaded.');
}
async function importBackup(f) {
  if (!f) return;
  try {
    const j = JSON.parse(await f.text());
    const st = j.state;
    if (j.app !== 'via-latina' || !st || typeof st.done !== 'object' || typeof st.srs !== 'object' || !st.settings) throw new Error('not a backup');
    const n = Object.keys(st.done).length;
    if (!confirm(`Restore this backup from ${String(j.exportedAt).slice(0, 10)} (${n} readings done)? It replaces the progress on this device.`)) return;
    const d = S.defaults();
    await S.replace({ ...d, ...st, settings: { ...d.settings, ...st.settings, onboarded: true } });
    applySettings(); toast('Backup restored.'); go('via');
  } catch (e) { alert('That file is not a Via Latina backup.'); }
}

boot();
