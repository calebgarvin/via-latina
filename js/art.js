// Loads assets/assets.json and every image it lists. Nothing else in the app knows file names.
let M = null;
const imgs = {};
export async function loadArt() {
  if (M) return M;
  M = await (await fetch('assets/assets.json')).json();
  await Promise.all(Object.entries(M.assets).map(([id, a]) => new Promise(res => {
    const im = new Image();
    im.onload = () => { imgs[id] = im; res(); };
    im.onerror = () => { console.warn('missing asset', id, a.file); res(); };
    im.src = 'assets/' + a.file;
  })));
  // expose UI art to CSS
  const fr = M.assets.ui_frame;
  if (fr) document.documentElement.style.setProperty('--frame', `url("${new URL('assets/' + fr.file, location.href).href}")`);
  return M;
}
export function art() { return M; }
export function img(id) { return imgs[id]; }
export function meta(id) { return M && M.assets[id]; }
export function url(id) { const a = meta(id); return a ? new URL('assets/' + a.file, location.href).href : ''; }

/** draw a single-frame asset with its bottom-centre at (x,y) in art pixels */
export function drawAt(ctx, id, x, y, opts = {}) {
  const im = imgs[id]; if (!im) return;
  const a = M.assets[id];
  const w = a.w, h = a.h;
  const fx = (opts.frame || 0) * w, fy = (opts.row || 0) * h;
  const ax = a.anchor ? a.anchor[0] : w / 2, ay = a.anchor ? a.anchor[1] : h;
  ctx.drawImage(im, fx, fy, w, h, Math.round(x - ax), Math.round(y - ay), w, h);
}
/** draw a Roman numeral string using the bitmap font sheet, centred at (x,y) */
export function drawRoman(ctx, text, x, y) {
  const a = M && M.assets.font_roman; const im = imgs.font_roman;
  if (!a || !im) return;
  const adv = a.advance || a.w + 1;
  const total = text.length * adv - 1;
  let cx = Math.round(x - total / 2);
  for (const ch of text) {
    const k = a.glyphs.indexOf(ch);
    if (k >= 0) ctx.drawImage(im, k * adv, 0, a.w, a.h, cx, Math.round(y), a.w, a.h);
    cx += adv;
  }
}
