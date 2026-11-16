// The Road through Rome: a tall, scrollable pixel-art map drawn on a canvas.
// Art comes only from assets.json (see art.js). World units are "art pixels".
import { img, art, meta, drawAt, drawRoman } from './art.js';
import { roman, seeded } from './util.js';

const DY = 30;           // vertical distance between stops (art px)
const TOP = 130, BOTTOM = 90;
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

function makeProps(nodes, worldW) {
  const m = art(); const props = [];
  const rnd = seeded(31337);
  for (let y = nodes[0].y + 40; y > nodes[nodes.length - 1].y - 20; y -= 15) {
    const k = Math.max(0, Math.min(nodes.length - 1, Math.round((nodes[0].y - y) / DY)));
    const d = m.districts[districtOf(nodes[k].chap)];
    for (let side = -1; side <= 1; side += 2) {
      if (rnd() < 0.45) continue;
      const rx = roadXAt(nodes, y);
      const x = Math.round(rx + side * (24 + rnd() * (worldW / 2)));
      if (x < 6 || x > worldW - 6) continue;
      const id = d.props[Math.floor(rnd() * d.props.length)];
      const a = meta(id); if (!a) continue;
      if (Math.abs(x - rx) < a.w / 2 + 14) continue;
      props.push({ id, x, y: Math.round(y + rnd() * 6) });
    }
  }
  return props;
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
  st.props = makeProps(st.nodes, st.worldW);
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
  const bands = [];
  for (let i = 0; i < nodes.length; i++) {
    const n = nodes[i]; const d = districtOf(n.chap);
    const yTop = n.y - DY / 2, yBot = n.y + DY / 2;
    if (bands.length && bands[bands.length - 1].d === d) bands[bands.length - 1].top = yTop;
    else bands.push({ d, top: yTop, bot: i === 0 ? st.H : yBot });
  }
  bands[bands.length - 1].top = 0;
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

  // 3) props + landmarks, depth-sorted by y
  const items = [];
  for (const p of st.props) if (p.y > y0 - 10 && p.y - 40 < y1) items.push({ y: p.y, f: () => drawAt(ctx, p.id, p.x, p.y) });
  for (let i = 0; i < nodes.length; i++) {
    const n = nodes[i];
    if (n.y < y0 - 60 || n.y > y1 + 60) continue;
    if (n.type === 'rest') {
      const side = n.x > st.worldW / 2 ? -1 : 1;
      const lid = n.week % 2 ? 'landmark_fountain' : 'landmark_shrine';
      items.push({ y: n.y + 4, f: () => drawAt(ctx, lid, n.x + side * 26, n.y + 4) });
      items.push({ y: n.y + 6, f: () => { drawAt(ctx, 'landmark_milestone', n.x - side * 16, n.y + 6); } });
    }
    if (n.type === 'read' && n.chEnd) {
      const nx = nodes[i + 1] || n;
      const ax = (n.x + nx.x) / 2, ay = (n.y + nx.y) / 2 + 6;
      items.push({ y: ay, f: () => {
        drawAt(ctx, 'landmark_arch', ax, ay);
        const a = meta('landmark_arch'); if (a) drawRoman(ctx, roman(n.chap), ax, ay - a.h + 3);
      } });
    }
  }
  const top = nodes[nodes.length - 1];
  items.push({ y: top.y - 26, f: () => drawAt(ctx, 'landmark_capitolium', top.x, top.y - 26) });
  items.sort((a, b) => a.y - b.y).forEach(it => it.f());
  // milestone numerals on top
  for (const n of nodes) {
    if (n.type !== 'rest' || n.y < y0 - 30 || n.y > y1 + 30) continue;
    const side = n.x > st.worldW / 2 ? -1 : 1;
    const a = meta('landmark_milestone');
    const txt = roman(n.week);
    if (a && txt.length <= 3) drawRoman(ctx, txt, n.x - side * 16, n.y + 6 - a.h + 4);
    else if (a) { drawRoman(ctx, txt, n.x - side * 16, n.y + 6 - a.h - 6); }
  }

  // 4) waypoints
  for (const n of vis) {
    const s = st.statusOf(n);
    const id = n.type === 'rest' ? (s === 'done' ? 'wp_rest' : 'wp_locked') : s === 'done' ? 'wp_done' : s === 'current' ? 'wp_current' : 'wp_locked';
    if (s === 'current' && st.frame % 2) { ctx.globalAlpha = .75; }
    drawAt(ctx, id, n.x, n.y + 6);
    ctx.globalAlpha = 1;
  }

  // 5) hero
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
