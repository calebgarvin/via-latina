// The Road through Rome: a tall, scrollable pixel-art map drawn on a canvas.
// Art comes only from assets.json (see art.js). World units are "art pixels".
import { img, art, meta, drawAt, drawRoman, romanWidth } from './art.js';
import { roman, seeded } from './util.js';

const DY = 30;           // vertical distance between stops (art px)
const TOP = 130, BOTTOM = 90;
const ROAD_HALF = 9;     // half the road's outer (dark) stroke
let st = null;           // active map state

export function buildNodes(days) {
  // reading days with a rest stop after every 6
  const nodes = [];
  for (const d of days) {
    nodes.push({ type: 'read', day: d.d, chap: d.c, chEnd: d.chEnd, chStart: d.chStart });
    if (d.d % 6 === 0) nodes.push({ type: 'rest', week: d.d / 6, chap: d.c, afterDay: d.d });
  }
  return nodes;
}

function layout(nodes, worldW) {
  const H = TOP + (nodes.length - 1) * DY + BOTTOM;
  const cx = worldW / 2, amp = Math.min(54, worldW / 2 - 34);
  nodes.forEach((n, k) => {
    n.y = H - BOTTOM - k * DY;
    n.x = Math.round(cx + amp * Math.sin(k * 0.31) + 8 * Math.sin(k * 0.097 + 1));
    n.k = k;
  });
  return H;
}
function roadXAt(nodes, y) {
  // nodes are ordered bottom (k=0) to top
  const k = (nodes[0].y - y) / DY;
  const i = Math.max(0, Math.min(nodes.length - 2, Math.floor(k)));
  const a = nodes[i], b = nodes[i + 1]; const t = Math.max(0, Math.min(1, (a.y - y) / DY));
  return a.x + (b.x - a.x) * t;
}

function districtOf(chap) { const m = art(); return m.chapterDistricts[chap - 1] || 'villa'; }

/** contiguous runs of one district, bottom to top: {d, top, bot} in world y */
function bandsOf(nodes, H) {
  const bands = [];
  for (let i = 0; i < nodes.length; i++) {
    const n = nodes[i]; const d = districtOf(n.chap);
    const yTop = n.y - DY / 2, yBot = n.y + DY / 2;
    if (bands.length && bands[bands.length - 1].d === d) bands[bands.length - 1].top = yTop;
    else bands.push({ d, top: yTop, bot: i === 0 ? H : yBot });
  }
  bands[bands.length - 1].top = 0;
  return bands;
}
/** leftmost and rightmost road centre between two heights (yA above yB) */
function roadSpan(nodes, yA, yB) {
  let mn = Infinity, mx = -Infinity;
  for (let y = yA; ; y += 3) {
    const x = roadXAt(nodes, Math.min(y, yB));
    if (x < mn) mn = x; if (x > mx) mx = x;
    if (y >= yB) break;
  }
  return [mn, mx];
}
// sprites are anchored bottom-centre: the rectangle a w×h sprite covers when drawn at (x, y)
const box = (x, y, w, h) => ({ x0: x - w / 2, x1: x + w / 2, y0: y - h, y1: y });
const hit = (a, b, pad = 0) => a.x0 < b.x1 + pad && a.x1 > b.x0 - pad && a.y0 < b.y1 + pad && a.y1 > b.y0 - pad;

/**
 * Everything that stands on the map, placed once per layout so nothing overlaps:
 * the Capitol, an arch wherever the chapter changes, a milestone and a fountain or shrine
 * at every rest stop, then the district's props around them.
 */
function buildScene(nodes, worldW, bands) {
  const fixed = [], solid = [];
  const dim = id => meta(id) || { w: 0, h: 0 };
  const top = nodes[nodes.length - 1];
  const cap = dim('landmark_capitolium');
  fixed.push({ id: 'landmark_capitolium', x: top.x, y: top.y - 26 });
  solid.push(box(top.x, top.y - 26, cap.w, cap.h));

  // an arch stands on the district boundary, between the last stop of one chapter and the first of the next
  const ar = dim('landmark_arch');
  for (let i = 0; i < nodes.length - 1; i++) {
    const n = nodes[i], nx = nodes[i + 1];
    if (nx.chap === n.chap) continue;
    const x = Math.round((n.x + nx.x) / 2), y = Math.round((n.y + nx.y) / 2) + 6;
    fixed.push({ id: 'landmark_arch', x, y, text: roman(n.chap) });
    solid.push(box(x, y, ar.w, ar.h));
  }

  // x of a sprite standing beside the road, clear of it over the sprite's whole height
  const beside = (a, side, y, from) => {
    const [mn, mx] = roadSpan(nodes, y - a.h, y);
    const edge = side > 0 ? Math.max(mx + ROAD_HALF + 1, from) : Math.min(mn - ROAD_HALF - 1, from);
    return Math.round(edge + side * a.w / 2);
  };
  // stand it beside the road, sliding along the road until it is clear of arches and the Capitol
  const stand = (id, a, side, y, from = side > 0 ? -1e9 : 1e9) => {
    let x = beside(a, side, y, from), dir = 0;
    for (let k = 0; k < 28; k++) {
      const r = box(x, y, a.w, a.h); const s = solid.find(o => hit(r, o, 2));
      if (!s) break;
      if (!dir) dir = (s.y0 + s.y1) / 2 < y - a.h / 2 ? 1 : -1;
      y += dir; x = beside(a, side, y, from);
    }
    return { id, x, y };
  };
  const ms = dim('landmark_milestone');
  const rests = [];
  for (const n of nodes) {
    if (n.type !== 'rest') continue;
    const side = n.x > worldW / 2 ? -1 : 1;           // the roomier side of the road
    const lid = n.week % 2 ? 'landmark_fountain' : 'landmark_shrine';
    const lm = dim(lid);
    // milestone across the road from the fountain or shrine; on the same side when there is no room
    let m = stand('landmark_milestone', ms, -side, n.y + 6), l;
    if (m.x - ms.w / 2 >= 1 && m.x + ms.w / 2 <= worldW - 1) l = stand(lid, lm, side, n.y + 4);
    else {
      m = stand('landmark_milestone', ms, side, n.y + 6);
      l = stand(lid, lm, side, n.y + 4, m.x + side * (ms.w / 2 + 2));
    }
    m.text = roman(n.week);
    fixed.push(l, m);
    rests.push(box(l.x, l.y, lm.w, lm.h), box(m.x, m.y, ms.w, ms.h));
  }
  solid.push(...rests);
  return { fixed, props: makeProps(nodes, worldW, bands, solid) };
}

function makeProps(nodes, worldW, bands, solid) {
  const m = art(); const all = [];
  let cur = [], prev = [];
  const MINOR = 24;                                     // narrower than this is street furniture, not a building
  const full = p => box(p.x, p.y, p.w, p.h);
  // the strip of ground a prop stands on; two props may overlap in depth but not share ground
  const foot = p => ({ x0: p.x - p.w / 2, x1: p.x + p.w / 2, y0: p.y - Math.max(5, Math.min(18, Math.round(p.h * 0.45))), y1: p.y });
  const ok = (c, pad = 1) => {
    const [mn, mx] = roadSpan(nodes, c.y - c.h, c.y + 1);
    if (c.x - c.w / 2 < mx + ROAD_HALF + 2 && c.x + c.w / 2 > mn - ROAD_HALF - 2) return false;   // clear of the road, top to bottom
    const fr = full(c);
    if (solid.some(o => hit(fr, o, 2))) return false;                                             // clear of landmarks
    const ff = foot(c);
    for (const list of [cur, prev]) for (const e of list) {
      if (!hit(fr, full(e))) continue;
      if (hit(ff, foot(e), pad)) return false;
      if (c.w < MINOR && c.y <= e.y) return false;          // small things do not hide behind bigger ones
      if (e.w < MINOR && c.w >= MINOR && c.y > e.y) return false;
    }
    return true;
  };
  // loose props either side of the road (the countryside), or close to it (street life in a city)
  const scatter = (b, list, rnd, density, street) => {
    if (!list || !list.length) return;
    for (let y = b.bot - 2; y > b.top + 3; y -= street ? 11 : 15) for (let side = -1; side <= 1; side += 2) {
      if (rnd() >= density) continue;
      const id = list[Math.floor(rnd() * list.length)];
      const a = meta(id); if (!a) continue;
      for (let t = 0; t < 3; t++) {
        const off = street ? ROAD_HALF + 3 + a.w / 2 + rnd() * rnd() * 50 : 24 + rnd() * (worldW / 2);
        const yy = Math.round(y + rnd() * 6);
        const c = { id, w: a.w, h: a.h, x: Math.round(roadXAt(nodes, yy) + side * off), y: yy };
        if (c.x < 6 || c.x > worldW - 6) continue;
        if (a.w >= 40 && [...cur, ...prev].some(e => e.id === id && Math.abs(e.y - c.y) < 120)) break;   // one big building of a kind per screenful
        if (ok(c)) { cur.push(c); break; }
      }
    }
  };
  // rows of buildings shoulder to shoulder, leaving a pavement beside the road, alleys and the odd small square.
  // Each row stands far enough behind the one in front that its upper floors show above the roofs.
  const city = (b, d, rnd) => {
    const open = d.open ?? 0.1;
    for (let side = -1; side <= 1; side += 2) {
      let y = b.bot - 3 - Math.floor(rnd() * 8);
      while (y > b.top + 12) {
        let cursor = side > 0 ? -1e9 : 1e9, tallest = 0;
        const pavement = 12 + Math.floor(rnd() * 5);
        for (let k = 0; k < 9; k++) {
          const id = d.buildings[Math.floor(rnd() * d.buildings.length)];
          const a = meta(id); if (!a) continue;
          const yy = y - Math.floor(rnd() * 3);
          const [mn, mx] = roadSpan(nodes, yy - a.h, yy + 1);
          const edge = side > 0 ? Math.max(mx + ROAD_HALF + pavement, cursor) : Math.min(mn - ROAD_HALF - pavement, cursor);
          const c = { id, w: a.w, h: a.h, x: Math.round(edge + side * a.w / 2), y: yy };
          const outside = side > 0 ? c.x + a.w / 2 - worldW : a.w / 2 - c.x;
          if (outside > a.w * 0.45) break;                               // mostly off the edge of the map
          if (rnd() < open) { cursor = edge + side * (18 + rnd() * 14); continue; }
          if (ok(c, 0)) { cur.push(c); tallest = Math.max(tallest, a.h); cursor = edge + side * (a.w + (rnd() < 0.3 ? 3 + Math.floor(rnd() * 5) : 0)); }
          else cursor = edge + side * 8;
        }
        y -= Math.max(26, Math.round(tallest * 0.8)) + 3 + Math.floor(rnd() * 5);
      }
    }
  };
  bands.forEach((b, i) => {
    const d = m.districts[b.d]; if (!d) return;
    const rnd = seeded(31337 + i * 7919);
    prev = cur; cur = [];
    if (d.buildings && d.buildings.length) { city(b, d, rnd); scatter(b, d.props, rnd, d.density ?? 0.7, true); }
    else scatter(b, d.props, rnd, d.density ?? 0.6, false);
    all.push(...cur);
  });
  return all;
}

export function mountMap(container, { days, nodes, statusOf, heroNode, outfit, onTap, onScroll }) {
  destroy();
  const wrap = document.createElement('div'); wrap.className = 'mapwrap';
  const scroll = document.createElement('div'); scroll.className = 'mapscroll';
  const spacer = document.createElement('div'); spacer.className = 'mapspacer';
  const canvas = document.createElement('canvas'); canvas.className = 'mapcanvas';
  scroll.appendChild(spacer); wrap.appendChild(canvas); wrap.appendChild(scroll); container.appendChild(wrap);
  st = { wrap, scroll, spacer, canvas, ctx: canvas.getContext('2d'), nodes, days, statusOf, heroNode, outfit,
         hero: null, anim: null, frame: 0, raf: 0, timer: 0, onTap, onScroll, patterns: {} };
  resize();
  st.hero = { x: nodes[heroNode].x, y: nodes[heroNode].y, dir: 'up', walking: false, node: heroNode };
  centerOn(heroNode, false);
  scroll.addEventListener('scroll', () => { draw(); st.onScroll && st.onScroll(); }, { passive: true });
  scroll.addEventListener('click', tap);
  window.addEventListener('resize', resize);
  st.timer = setInterval(() => { st.frame++; if (!st.anim) draw(); }, 450);
  draw();
  return { walkTo, centerOn, redraw: draw, setOutfit: o => { st.outfit = o; draw(); }, destroy };
}

export function destroy() {
  if (!st) return;
  clearInterval(st.timer); cancelAnimationFrame(st.raf);
  window.removeEventListener('resize', resize);
  st.wrap.remove(); st = null;
}

function resize() {
  if (!st) return;
  const vw = window.innerWidth, vh = window.innerHeight;
  const dpr = Math.min(3, window.devicePixelRatio || 1);
  st.scale = Math.max(2, Math.floor(vw / 200));
  st.worldW = Math.ceil(vw / st.scale);
  const keepNode = st.hero ? st.hero.node : st.heroNode;
  st.H = layout(st.nodes, st.worldW);
  st.bands = bandsOf(st.nodes, st.H);
  const scene = buildScene(st.nodes, st.worldW, st.bands);
  st.props = scene.props; st.fixed = scene.fixed;
  st.spacer.style.height = (st.H * st.scale) + 'px';
  st.canvas.width = Math.round(vw * dpr); st.canvas.height = Math.round(vh * dpr);
  st.canvas.style.width = vw + 'px'; st.canvas.style.height = vh + 'px';
  st.dpr = dpr; st.vw = vw; st.vh = vh;
  st.patterns = {};
  if (st.hero) { const n = st.nodes[keepNode]; st.hero.x = n.x; st.hero.y = n.y; }
  draw();
}

function pattern(id) {
  if (st.patterns[id] !== undefined) return st.patterns[id];
  const im = img(id); st.patterns[id] = im ? st.ctx.createPattern(im, 'repeat') : null;
  return st.patterns[id];
}

export function centerOn(k, smooth = true) {
  if (!st) return;
  const n = st.nodes[k];
  const top = n.y * st.scale - st.vh * 0.55;
  st.scroll.scrollTo({ top: Math.max(0, top), behavior: smooth ? 'smooth' : 'auto' });
  draw();
}

function tap(e) {
  if (!st || st.anim) return;
  const y0 = st.scroll.scrollTop / st.scale;
  const wx = e.clientX / st.scale, wy = y0 + e.clientY / st.scale;
  let best = null, bd = 1e9;
  for (const n of st.nodes) { const d = Math.hypot(n.x - wx, n.y - 4 - wy); if (d < bd) { bd = d; best = n; } }
  if (best && bd < 16) st.onTap && st.onTap(best);
}

function draw() {
  if (!st) return;
  cancelAnimationFrame(st.raf);
  st.raf = requestAnimationFrame(render);
}

function render() {
  const { ctx, scale, dpr, nodes } = st;
  const y0 = st.scroll.scrollTop / scale, vhW = st.vh / scale, y1 = y0 + vhW;
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.imageSmoothingEnabled = false;
  ctx.fillStyle = '#1d1511'; ctx.fillRect(0, 0, st.canvas.width, st.canvas.height);
  ctx.setTransform(scale * dpr, 0, 0, scale * dpr, 0, -y0 * scale * dpr);
  ctx.imageSmoothingEnabled = false;

  // 1) district bands
  const bands = st.bands;
  for (const b of bands) {
    if (b.bot < y0 || b.top > y1) continue;
    const p = pattern('bg_' + b.d);
    ctx.fillStyle = p || '#5d6b34';
    ctx.fillRect(0, Math.floor(b.top), st.worldW, Math.ceil(b.bot - b.top));
    ctx.fillStyle = 'rgba(20,14,11,.18)'; ctx.fillRect(0, Math.floor(b.bot) - 1, st.worldW, 1);
  }

  // 2) road
  const vis = nodes.filter(n => n.y > y0 - DY * 2 && n.y < y1 + DY * 2);
  if (vis.length > 1) {
    const path = () => {
      ctx.beginPath();
      ctx.moveTo(vis[0].x, vis[0].y);
      for (let i = 1; i < vis.length - 1; i++) {
        const mx = (vis[i].x + vis[i + 1].x) / 2, my = (vis[i].y + vis[i + 1].y) / 2;
        ctx.quadraticCurveTo(vis[i].x, vis[i].y, mx, my);
      }
      const l = vis[vis.length - 1]; ctx.lineTo(l.x, l.y);
    };
    ctx.lineCap = 'round'; ctx.lineJoin = 'round';
    path(); ctx.strokeStyle = 'rgba(43,29,22,.85)'; ctx.lineWidth = 18; ctx.stroke();
    path(); ctx.strokeStyle = pattern('tile_via') || '#8a847a'; ctx.lineWidth = 14; ctx.stroke();
  }

  // 3) props and landmarks, depth-sorted by y
  const items = [];
  for (const p of st.props) if (p.y > y0 - 4 && p.y - p.h < y1) items.push({ y: p.y, f: () => drawAt(ctx, p.id, p.x, p.y) });
  for (const f of st.fixed) if (f.y > y0 - 4 && f.y - 100 < y1) items.push({ y: f.y, f: () => drawFixed(ctx, f) });
  items.sort((a, b) => a.y - b.y).forEach(it => it.f());

  // 4) waypoints
  for (const n of vis) {
    const s = st.statusOf(n);
    const id = n.type === 'rest' ? (s === 'done' ? 'wp_rest' : 'wp_locked') : s === 'done' ? 'wp_done' : s === 'current' ? 'wp_current' : 'wp_locked';
    if (s === 'current' && st.frame % 2) { ctx.globalAlpha = .75; }
    drawAt(ctx, id, n.x, n.y + 6);
    ctx.globalAlpha = 1;
  }

  // 5) hero, always in front: a chapter's first stop is right behind its arch, and he must stay in view there
  const h = st.hero;
  if (h && h.y > y0 - 30 && h.y < y1 + 30) {
    const a = meta('hero_base');
    const rows = (a && a.rows) || ['down', 'up', 'left', 'right'];
    const anim = (a && a.anim) || { idle: [0, 1], walk: [2, 3, 4, 5] };
    const seq = h.walking ? anim.walk : anim.idle;
    const frame = seq[(h.walking ? st.walkFrame | 0 : st.frame) % seq.length];
    const row = Math.max(0, rows.indexOf(h.walking ? h.dir : 'down'));
    ctx.fillStyle = 'rgba(20,14,11,.35)'; ctx.fillRect(Math.round(h.x - 5), Math.round(h.y + 1), 10, 2);
    drawAt(ctx, 'hero_base', h.x, h.y + 2, { frame, row });
    for (const o of st.outfit || []) drawAt(ctx, 'hero_' + o, h.x, h.y + 2, { frame, row });
  }
}

/** a landmark, with its Roman numeral carved on the face named in assets.json (`face`: [x, y, w, h] inside the sprite) */
function drawFixed(ctx, f) {
  drawAt(ctx, f.id, f.x, f.y);
  if (!f.text) return;
  const a = meta(f.id), fa = meta('font_roman'); if (!a || !fa) return;
  const [fx, fy, fw, fh] = a.face || [0, 0, a.w, a.h];
  let lines = [f.text];
  if (romanWidth(f.text) > fw) {                       // too long for one line: tens above, units below
    const m = f.text.match(/^(.*?)(IX|IV|V?I{0,3})$/);
    if (m && m[1] && m[2]) lines = [m[1], m[2]];
  }
  const total = lines.length * fa.h + (lines.length - 1) * 2;
  const cx = Math.round(f.x - a.w / 2) + fx + fw / 2;
  let y = Math.round(f.y - a.h) + fy + Math.max(0, Math.floor((fh - total) / 2));
  for (const ln of lines) { drawRoman(ctx, ln, cx, y); y += fa.h + 2; }
}

/** animate the hero from its node to node `to` (through intermediate stops) */
export function walkTo(to, done) {
  if (!st) { done && done(); return; }
  const from = st.hero.node;
  if (to === from) { done && done(); return; }
  const path = [];
  for (let k = from; k !== to; k += to > from ? 1 : -1) path.push(st.nodes[k + (to > from ? 1 : -1)]);
  const a = meta('hero_base'); const fps = (a && a.fps) || 8;
  const speed = 34; // art px per second
  let i = 0, last = performance.now(), acc = 0;
  st.hero.walking = true; st.walkFrame = 0;
  const step = now => {
    if (!st) return;
    const dt = Math.min(0.05, (now - last) / 1000); last = now;
    acc += dt; st.walkFrame = acc * fps;
    const tgt = path[i]; const h = st.hero;
    const dx = tgt.x - h.x, dy = tgt.y - h.y, dist = Math.hypot(dx, dy);
    const mv = speed * dt;
    h.dir = Math.abs(dx) > Math.abs(dy) * 1.2 ? (dx < 0 ? 'left' : 'right') : (dy < 0 ? 'up' : 'down');
    if (dist <= mv) { h.x = tgt.x; h.y = tgt.y; h.node = tgt.k; i++; }
    else { h.x += dx / dist * mv; h.y += dy / dist * mv; }
    // keep hero in view
    const want = h.y * st.scale - st.vh * 0.55;
    st.scroll.scrollTop += (want - st.scroll.scrollTop) * 0.12;
    render();
    if (i < path.length) st.anim = requestAnimationFrame(step);
    else { st.anim = null; h.walking = false; render(); done && done(); }
  };
  st.anim = requestAnimationFrame(step);
}
