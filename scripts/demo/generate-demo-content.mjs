// Generates the DevDarshan DEMO wallpapers: original, abstract devotional artwork
// (mandalas, diyas, lotus, Om, trishul, peacock feather, temples…) drawn from SVG.
// No third-party artwork is used. Output:
//   <out>/wallpapers/<id>/original.jpg | preview.webp | thumb.webp
//   apps/user/src/demo/catalog.data.ts  (metadata the demo build bundles)
//
//   SHARP_PATH=/path/to/node_modules/sharp node scripts/demo/generate-demo-content.mjs <out-dir>
import { createRequire } from 'node:module';
import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const sharp = require(process.env.SHARP_PATH || 'sharp');
const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const OUT = process.argv[2];
if (!OUT) throw new Error('usage: generate-demo-content.mjs <out-dir>');

const W = 1440;
const H = 3120;

// ---------- small helpers ----------
let seed = 7;
const rand = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
const range = (n) => Array.from({ length: n }, (_, i) => i);
const rad = (deg) => (deg * Math.PI) / 180;

const linear = (id, stops, x2 = 0, y2 = 1) =>
  `<linearGradient id="${id}" x1="0" y1="0" x2="${x2}" y2="${y2}">${stops
    .map(([o, c, a = 1]) => `<stop offset="${o}" stop-color="${c}" stop-opacity="${a}"/>`)
    .join('')}</linearGradient>`;
const radial = (id, stops, cx = 0.5, cy = 0.5, r = 0.5) =>
  `<radialGradient id="${id}" cx="${cx}" cy="${cy}" r="${r}">${stops
    .map(([o, c, a = 1]) => `<stop offset="${o}" stop-color="${c}" stop-opacity="${a}"/>`)
    .join('')}</radialGradient>`;
const glow = (id, sd) => `<filter id="${id}" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="${sd}"/></filter>`;
const svg = (defs, body) =>
  `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}"><defs>${defs}${glow('g40', 40)}${glow('g12', 12)}${glow('g90', 90)}</defs>${body}</svg>`;
const bg = (id) => `<rect width="${W}" height="${H}" fill="url(#${id})"/>`;

function bokeh(count, colors, minR = 10, maxR = 60, opacity = 0.25, area = [0, 0, W, H]) {
  return range(count)
    .map(() => {
      const r = minR + rand() * (maxR - minR);
      const x = area[0] + rand() * area[2];
      const y = area[1] + rand() * area[3];
      const c = colors[Math.floor(rand() * colors.length)];
      return `<circle cx="${x.toFixed(0)}" cy="${y.toFixed(0)}" r="${r.toFixed(0)}" fill="${c}" opacity="${(opacity * (0.4 + rand() * 0.6)).toFixed(2)}"/>`;
    })
    .join('');
}

function stars(count, color = '#FFF6D8') {
  return range(count)
    .map(() => `<circle cx="${(rand() * W).toFixed(0)}" cy="${(rand() * H * 0.6).toFixed(0)}" r="${(1.5 + rand() * 3).toFixed(1)}" fill="${color}" opacity="${(0.3 + rand() * 0.7).toFixed(2)}"/>`)
    .join('');
}

// A petal pointing up from (0,0), length l, width w.
const petal = (l, w) => `M0,0 C${w},${-l * 0.3} ${w * 0.6},${-l * 0.85} 0,${-l} C${-w * 0.6},${-l * 0.85} ${-w},${-l * 0.3} 0,0 Z`;

function mandalaGroup(cx, cy, scale, colors) {
  const [a, b, c, d] = colors;
  const ring = (n, l, w, r0, fill, opacity = 1, offset = 0) =>
    range(n)
      .map((i) => `<path d="${petal(l, w)}" transform="translate(${cx},${cy}) rotate(${(360 / n) * i + offset}) translate(0,${-r0})" fill="${fill}" opacity="${opacity}"/>`)
      .join('');
  const dots = (n, r0, rr, fill) =>
    range(n)
      .map((i) => {
        const t = rad((360 / n) * i);
        return `<circle cx="${(cx + Math.sin(t) * r0).toFixed(1)}" cy="${(cy - Math.cos(t) * r0).toFixed(1)}" r="${rr}" fill="${fill}"/>`;
      })
      .join('');
  const s = scale;
  return [
    `<circle cx="${cx}" cy="${cy}" r="${560 * s}" fill="none" stroke="${d}" stroke-width="${3 * s}" opacity="0.6"/>`,
    ring(32, 150 * s, 34 * s, 380 * s, a, 0.55),
    dots(64, 540 * s, 6 * s, d),
    ring(24, 210 * s, 56 * s, 170 * s, b, 0.9),
    ring(24, 150 * s, 40 * s, 170 * s, c, 0.9, 7.5),
    `<circle cx="${cx}" cy="${cy}" r="${370 * s}" fill="none" stroke="${d}" stroke-width="${4 * s}" stroke-dasharray="${6 * s} ${14 * s}"/>`,
    ring(16, 150 * s, 50 * s, 20 * s, a, 0.95),
    ring(8, 120 * s, 46 * s, 10 * s, c, 1, 22.5),
    `<circle cx="${cx}" cy="${cy}" r="${70 * s}" fill="${d}"/>`,
    `<circle cx="${cx}" cy="${cy}" r="${44 * s}" fill="${b}"/>`,
    dots(12, 105 * s, 9 * s, d),
  ].join('');
}

// ---------- motifs ----------
const motifs = {
  mandala({ c1, c2, petals }) {
    const defs = radial('bg', [[0, c1], [1, c2]], 0.5, 0.45, 0.75);
    return svg(defs, bg('bg') + bokeh(40, [petals[3]], 4, 14, 0.5) + mandalaGroup(W / 2, H * 0.45, 1.05, petals) + mandalaGroup(W / 2, H * 0.45, 0.32, petals.slice().reverse()));
  },

  om({ c1, c2, gold, ring }) {
    const defs = radial('bg', [[0, c1], [1, c2]], 0.5, 0.42, 0.8) + radial('halo', [[0, gold, 0.55], [1, gold, 0]]);
    const om = `<text x="${W / 2}" y="${H * 0.42 + 230}" font-family="FreeSerif" font-size="760" text-anchor="middle" fill="${gold}">ॐ</text>`;
    return svg(
      defs,
      bg('bg') +
        `<circle cx="${W / 2}" cy="${H * 0.42}" r="720" fill="url(#halo)"/>` +
        mandalaGroup(W / 2, H * 0.42, 1.12, [ring, ring, gold, gold]).replace(/opacity="0\.9"/g, 'opacity="0.18"').replace(/opacity="0\.55"/g, 'opacity="0.14"').replace(/opacity="0\.95"/g, 'opacity="0.18"').replace(/opacity="1"/g, 'opacity="0.2"') +
        `<g filter="url(#g40)" opacity="0.8">${om}</g>` + om +
        bokeh(60, [gold], 3, 10, 0.6),
    );
  },

  diyas({ c1, c2, flame }) {
    const defs = linear('bg', [[0, c1], [1, c2]]) + radial('fl', [[0, '#FFFBE6'], [0.35, '#FFD25A'], [1, flame, 0]]);
    const diya = (x, y, s) => `
      <g transform="translate(${x},${y}) scale(${s})">
        <circle cx="0" cy="-120" r="150" fill="url(#fl)" filter="url(#g40)"/>
        <path d="M-150,0 C-120,80 120,80 150,0 C90,22 -90,22 -150,0 Z" fill="#7A2E0E"/>
        <path d="M-150,0 C-110,12 110,12 150,0 C130,30 -130,30 -150,0 Z" fill="#B85C1F"/>
        <path d="M150,-4 C190,-30 205,-50 196,-70 C178,-46 160,-30 128,-14 Z" fill="#9A3F14"/>
        <path d="M0,-12 C-26,-50 -18,-110 0,-150 C18,-110 26,-50 0,-12 Z" fill="#FFC93C"/>
        <path d="M0,-22 C-12,-50 -8,-92 0,-118 C8,-92 12,-50 0,-22 Z" fill="#FFF7D6"/>
      </g>`;
    const row = range(5)
      .map((i) => diya(220 + i * 250, H * 0.72 + (i % 2) * 70, 0.85))
      .join('');
    return svg(defs, bg('bg') + stars(120) + bokeh(70, ['#FFC14D', '#FF8A3D', '#FFE29A'], 10, 70, 0.35, [0, H * 0.35, W, H * 0.5]) + diya(W / 2, H * 0.5, 2.1) + row);
  },

  lotus({ c1, c2, p1, p2, water }) {
    const defs = linear('bg', [[0, c1], [0.62, c2], [0.62, water], [1, '#0C2733']]) + linear('pe', [[0, p1], [1, p2]]);
    const cx = W / 2;
    const cy = H * 0.6;
    const layer = (n, l, w, spread, op) =>
      range(n)
        .map((i) => {
          const a = -spread / 2 + (spread / (n - 1)) * i;
          return `<path d="${petal(l, w)}" transform="translate(${cx},${cy}) rotate(${a})" fill="url(#pe)" stroke="${p2}" stroke-width="3" opacity="${op}"/>`;
        })
        .join('');
    const ripples = range(6)
      .map((i) => `<ellipse cx="${cx}" cy="${cy + 40}" rx="${260 + i * 110}" ry="${40 + i * 18}" fill="none" stroke="#FFFFFF" stroke-opacity="${0.18 - i * 0.025}" stroke-width="4"/>`)
      .join('');
    return svg(
      defs,
      bg('bg') + bokeh(50, ['#FFF2C7'], 4, 16, 0.4, [0, 0, W, H * 0.55]) + `<circle cx="${cx}" cy="${H * 0.3}" r="230" fill="#FFF2C7" opacity="0.85" filter="url(#g40)"/>` + ripples +
        layer(9, 520, 150, 150, 0.95) + layer(7, 600, 140, 100, 1) + layer(5, 640, 120, 50, 1) +
        `<ellipse cx="${cx}" cy="${cy - 40}" rx="90" ry="40" fill="#F6C344"/>`,
    );
  },

  sun({ c1, c2, disc }) {
    const defs = radial('bg', [[0, c1], [1, c2]], 0.5, 0.38, 0.85) + radial('disc', [[0, '#FFFBEA'], [0.55, disc], [1, disc, 0.9]]);
    const cx = W / 2;
    const cy = H * 0.38;
    const rays = range(36)
      .map((i) => `<path d="M-38,0 L0,-${i % 2 ? 560 : 720} L38,0 Z" transform="translate(${cx},${cy}) rotate(${i * 10}) translate(0,-300)" fill="${disc}" opacity="${i % 2 ? 0.45 : 0.75}"/>`)
      .join('');
    return svg(defs, bg('bg') + `<circle cx="${cx}" cy="${cy}" r="700" fill="${disc}" opacity="0.35" filter="url(#g90)"/>` + rays + `<circle cx="${cx}" cy="${cy}" r="290" fill="url(#disc)"/>` + mandalaGroup(cx, cy, 0.42, ['#FFF3C4', '#FFE08A', '#FFC24D', '#FFFFFF']).replace(/opacity="0\.\d+"/g, 'opacity="0.55"') + `<path d="M0,${H * 0.78} C${W * 0.3},${H * 0.74} ${W * 0.7},${H * 0.8} ${W},${H * 0.76} L${W},${H} L0,${H} Z" fill="#3B1606" opacity="0.6"/>`);
  },

  trishul({ c1, c2, metal }) {
    const defs = linear('bg', [[0, c1], [1, c2]]) + linear('mt', [[0, '#FFFFFF'], [0.5, metal], [1, '#6B7280']], 1, 0);
    const cx = W / 2;
    const moon = `<g transform="translate(${cx + 330},${H * 0.2})"><circle r="150" fill="#F8F4E3"/><circle cx="62" cy="-34" r="140" fill="${c1}"/></g>`;
    const trishul = `
      <g transform="translate(${cx},${H * 0.3})">
        <rect x="-22" y="160" width="44" height="1500" rx="20" fill="url(#mt)"/>
        <path d="M0,-260 C40,-150 46,-40 22,160 L-22,160 C-46,-40 -40,-150 0,-260 Z" fill="url(#mt)"/>
        <path d="M-40,170 C-210,140 -300,0 -280,-200 C-250,-90 -170,-10 -40,20 Z" fill="url(#mt)"/>
        <path d="M40,170 C210,140 300,0 280,-200 C250,-90 170,-10 40,20 Z" fill="url(#mt)"/>
        <rect x="-120" y="150" width="240" height="40" rx="18" fill="${metal}"/>
        <g transform="translate(0,420)">
          <path d="M-120,-110 L120,-110 L18,0 L120,110 L-120,110 L-18,0 Z" fill="#8B5A2B"/>
          <path d="M-120,-110 L120,-110 L18,0 L-18,0 Z" fill="#A8743C"/>
          <rect x="-130" y="-8" width="260" height="16" rx="8" fill="#E9D7A8"/>
        </g>
        <path d="M-22,330 C-200,360 -220,520 -60,560" fill="none" stroke="#E9D7A8" stroke-width="10"/>
      </g>`;
    const mountains = `<path d="M0,${H * 0.82} L${W * 0.2},${H * 0.7} L${W * 0.33},${H * 0.76} L${W * 0.5},${H * 0.62} L${W * 0.68},${H * 0.75} L${W * 0.82},${H * 0.69} L${W},${H * 0.8} L${W},${H} L0,${H} Z" fill="#E8EEF6" opacity="0.9"/><path d="M${W * 0.5},${H * 0.62} L${W * 0.58},${H * 0.68} L${W * 0.52},${H * 0.67} L${W * 0.47},${H * 0.7} L${W * 0.44},${H * 0.66} Z" fill="#FFFFFF"/>`;
    return svg(defs, bg('bg') + stars(160) + moon + `<g filter="url(#g40)" opacity="0.5"><rect x="${cx - 40}" y="${H * 0.2}" width="80" height="1300" fill="#BFD7FF"/></g>` + trishul + mountains);
  },

  feather({ c1, c2 }) {
    const defs = linear('bg', [[0, c1], [1, c2]]) + radial('eye', [[0, '#0B1E5B'], [0.35, '#1B3FA6'], [0.55, '#14B8A6'], [0.75, '#E0B341'], [1, '#2E7D32', 0.2]]);
    const cx = W * 0.58;
    const barbs = range(70)
      .map((i) => {
        const y = 300 + i * 26;
        const len = 230 + Math.sin(i / 9) * 60;
        return `<path d="M0,${y} q${-len * 0.6},${-30} ${-len},${-90}" stroke="#4CAF50" stroke-opacity="0.55" stroke-width="5" fill="none"/><path d="M0,${y} q${len * 0.6},${-30} ${len},${-90}" stroke="#4CAF50" stroke-opacity="0.55" stroke-width="5" fill="none"/>`;
      })
      .join('');
    const feather = `
      <g transform="translate(${cx},${H * 0.08}) rotate(-12)">
        ${barbs}
        <ellipse cx="0" cy="560" rx="250" ry="340" fill="url(#eye)"/>
        <ellipse cx="0" cy="600" rx="96" ry="140" fill="#0B1E5B"/>
        <ellipse cx="0" cy="570" rx="52" ry="78" fill="#1E40AF"/>
        <path d="M0,240 C14,900 10,1800 -20,2400" stroke="#D9C27A" stroke-width="12" fill="none"/>
      </g>`;
    const flute = `
      <g transform="translate(${W * 0.22},${H * 0.66}) rotate(-28)">
        <rect x="0" y="-26" width="1250" height="52" rx="26" fill="#C8892B"/>
        <rect x="0" y="-26" width="1250" height="20" rx="10" fill="#E2AE52"/>
        ${range(7).map((i) => `<ellipse cx="${380 + i * 95}" cy="0" rx="14" ry="10" fill="#4A2A0A"/>`).join('')}
        <rect x="120" y="-30" width="30" height="60" fill="#B91C1C"/><rect x="200" y="-30" width="18" height="60" fill="#B91C1C"/>
        <path d="M150,26 C120,140 180,220 110,330" stroke="#B91C1C" stroke-width="10" fill="none"/>
      </g>`;
    return svg(defs, bg('bg') + bokeh(60, ['#93C5FD', '#FDE68A'], 4, 22, 0.45) + feather + flute);
  },

  bow({ c1, c2, gold }) {
    const defs = linear('bg', [[0, c1], [1, c2]]) + radial('disc', [[0, '#FFF7DA'], [1, gold, 0.2]]);
    const cx = W / 2;
    const cy = H * 0.45;
    return svg(
      defs,
      bg('bg') + `<circle cx="${cx}" cy="${cy}" r="560" fill="url(#disc)"/>` +
        range(24).map((i) => `<rect x="-6" y="-860" width="12" height="230" fill="${gold}" opacity="0.6" transform="translate(${cx},${cy}) rotate(${i * 15})"/>`).join('') +
        `<path d="M${cx - 120},${cy - 900} C${cx + 420},${cy - 500} ${cx + 420},${cy + 500} ${cx - 120},${cy + 900}" fill="none" stroke="#5B2C06" stroke-width="54" stroke-linecap="round"/>` +
        `<path d="M${cx - 120},${cy - 900} C${cx + 420},${cy - 500} ${cx + 420},${cy + 500} ${cx - 120},${cy + 900}" fill="none" stroke="${gold}" stroke-width="16" stroke-linecap="round"/>` +
        `<line x1="${cx - 120}" y1="${cy - 900}" x2="${cx - 120}" y2="${cy + 900}" stroke="#FFF3D1" stroke-width="6"/>` +
        `<line x1="${cx - 420}" y1="${cy}" x2="${cx + 560}" y2="${cy}" stroke="#4A2507" stroke-width="16"/>` +
        `<path d="M${cx + 560},${cy - 46} L${cx + 680},${cy} L${cx + 560},${cy + 46} Z" fill="${gold}"/>` +
        `<path d="M${cx - 420},${cy} l-80,-60 l40,60 l-40,60 Z" fill="#B91C1C"/>` +
        bokeh(50, ['#FFE7A3'], 4, 14, 0.5),
    );
  },

  gada({ c1, c2 }) {
    const defs = linear('bg', [[0, c1], [1, c2]]) + radial('head', [[0, '#FFE8A3'], [0.4, '#F5B53A'], [1, '#9A5B0A']], 0.38, 0.35, 0.7);
    const cx = W / 2;
    const top = H * 0.24;
    return svg(
      defs,
      bg('bg') + bokeh(40, ['#FFD08A'], 10, 60, 0.25) + `<circle cx="${cx}" cy="${top + 260}" r="520" fill="#FFB347" opacity="0.4" filter="url(#g90)"/>` +
        `<rect x="${cx - 40}" y="${top + 420}" width="80" height="1500" rx="30" fill="#8A4B08"/>` +
        range(9).map((i) => `<rect x="${cx - 52}" y="${top + 520 + i * 150}" width="104" height="26" rx="12" fill="#F5B53A"/>`).join('') +
        `<circle cx="${cx}" cy="${top + 260}" r="300" fill="url(#head)"/>` +
        range(5).map((i) => `<ellipse cx="${cx}" cy="${top + 260}" rx="${300 - i * 4}" ry="${60 + i * 50}" fill="none" stroke="#9A5B0A" stroke-width="10" opacity="0.6"/>`).join('') +
        `<path d="M${cx},${top - 120} L${cx + 40},${top - 20} L${cx - 40},${top - 20} Z" fill="#F5B53A"/>` +
        `<path d="M${cx + 300},${H * 0.12} L${cx + 300},${H * 0.36}" stroke="#7C2D12" stroke-width="12"/>` +
        `<path d="M${cx + 306},${H * 0.12} C${cx + 460},${H * 0.13} ${cx + 520},${H * 0.15} ${cx + 640},${H * 0.14} L${cx + 600},${H * 0.18} L${cx + 640},${H * 0.22} C${cx + 520},${H * 0.23} ${cx + 460},${H * 0.21} ${cx + 306},${H * 0.22} Z" fill="#F97316"/>`,
    );
  },

  temple({ c1, c2, sil }) {
    const defs = linear('bg', [[0, c1], [0.7, c2], [1, '#2A0F05']]);
    const shikhara = (x, base, w, h, color) => {
      const tiers = range(6)
        .map((i) => {
          const tw = w * (1 - i * 0.13);
          const y = base - h * 0.15 * i;
          return `<path d="M${x - tw / 2},${y} Q${x - tw / 2},${y - h * 0.16} ${x},${y - h * 0.2} Q${x + tw / 2},${y - h * 0.16} ${x + tw / 2},${y} Z" fill="${color}"/>`;
        })
        .join('');
      return `${tiers}<rect x="${x - w * 0.6}" y="${base}" width="${w * 1.2}" height="${H - base}" fill="${color}"/><circle cx="${x}" cy="${base - h * 0.95}" r="${w * 0.06}" fill="${color}"/><line x1="${x}" y1="${base - h}" x2="${x}" y2="${base - h * 1.25}" stroke="${color}" stroke-width="8"/><path d="M${x},${base - h * 1.25} l${w * 0.3},${h * 0.05} l-${w * 0.3},${h * 0.07} Z" fill="#F97316"/>`;
    };
    return svg(
      defs,
      bg('bg') + stars(90) + `<circle cx="${W * 0.7}" cy="${H * 0.36}" r="200" fill="#FFE2A8" opacity="0.9"/><circle cx="${W * 0.7}" cy="${H * 0.36}" r="380" fill="#FFB86B" opacity="0.35" filter="url(#g90)"/>` +
        shikhara(W * 0.5, H * 0.72, 520, 1300, sil) + shikhara(W * 0.18, H * 0.8, 300, 640, sil) + shikhara(W * 0.84, H * 0.8, 300, 640, sil) +
        range(18).map((i) => `<circle cx="${80 + i * 75}" cy="${H * 0.86}" r="10" fill="#FFD27A"/><circle cx="${80 + i * 75}" cy="${H * 0.86}" r="34" fill="#FFB347" opacity="0.35" filter="url(#g12)"/>`).join(''),
    );
  },

  kalash({ c1, c2 }) {
    const defs = radial('bg', [[0, c1], [1, c2]], 0.5, 0.5, 0.8) + linear('pot', [[0, '#FFE39A'], [0.5, '#D9A02A'], [1, '#8A5A07']], 1, 0);
    const cx = W / 2;
    const cy = H * 0.52;
    const leaves = range(7)
      .map((i) => `<path d="${petal(330, 70)}" transform="translate(${cx},${cy - 330}) rotate(${-75 + i * 25})" fill="#2F7D32" stroke="#1B5E20" stroke-width="4"/>`)
      .join('');
    const coins = range(26)
      .map(() => `<circle cx="${(cx - 520 + rand() * 1040).toFixed(0)}" cy="${(cy + 480 + rand() * 260).toFixed(0)}" r="${(34 + rand() * 14).toFixed(0)}" fill="#F2C14E" stroke="#B7791F" stroke-width="5"/>`)
      .join('');
    return svg(
      defs,
      bg('bg') + mandalaGroup(cx, cy - 100, 1.25, ['#7F1D1D', '#991B1B', '#B45309', '#F59E0B']).replace(/opacity="0\.\d+"/g, 'opacity="0.25"').replace(/opacity="1"/g, 'opacity="0.25"') +
        leaves + `<ellipse cx="${cx}" cy="${cy - 400}" rx="120" ry="150" fill="#8B5A2B"/><path d="M${cx - 40},${cy - 540} q40,-60 80,0" fill="#5B3A1A"/>` +
        `<path d="M${cx - 200},${cy - 320} C${cx - 470},${cy - 220} ${cx - 480},${cy + 340} ${cx - 160},${cy + 420} L${cx + 160},${cy + 420} C${cx + 480},${cy + 340} ${cx + 470},${cy - 220} ${cx + 200},${cy - 320} Z" fill="url(#pot)"/>` +
        `<rect x="${cx - 230}" y="${cy - 350}" width="460" height="56" rx="26" fill="#C98A1C"/>` +
        `<path d="M${cx - 380},${cy} Q${cx},${cy + 90} ${cx + 380},${cy}" fill="none" stroke="#B91C1C" stroke-width="22"/>` +
        coins + bokeh(60, ['#FDE68A'], 4, 12, 0.6),
    );
  },

  holi() {
    const defs = linear('bg', [[0, '#FFF7ED'], [1, '#FDE7F3']]);
    const colors = ['#EC4899', '#F59E0B', '#22C55E', '#3B82F6', '#A855F7', '#EF4444', '#FACC15'];
    const clouds = range(26)
      .map(() => {
        const c = colors[Math.floor(rand() * colors.length)];
        return `<circle cx="${(rand() * W).toFixed(0)}" cy="${(rand() * H).toFixed(0)}" r="${(140 + rand() * 260).toFixed(0)}" fill="${c}" opacity="0.55" filter="url(#g90)"/>`;
      })
      .join('');
    return svg(defs, bg('bg') + clouds + bokeh(260, colors, 4, 22, 0.8));
  },

  rangoli({ c1, petals }) {
    const defs = radial('bg', [[0, c1], [1, '#0B0A12']], 0.5, 0.5, 0.8);
    const cx = W / 2;
    const cy = H / 2;
    const outer = range(8)
      .map((i) => `<g transform="rotate(${i * 45} ${cx} ${cy})"><path d="M${cx},${cy - 300} C${cx + 160},${cy - 420} ${cx + 120},${cy - 640} ${cx},${cy - 700} C${cx - 120},${cy - 640} ${cx - 160},${cy - 420} ${cx},${cy - 300} Z" fill="${petals[i % 4]}"/><circle cx="${cx}" cy="${cy - 760}" r="34" fill="${petals[(i + 2) % 4]}"/></g>`)
      .join('');
    return svg(defs, bg('bg') + outer + mandalaGroup(cx, cy, 0.62, petals) + bokeh(80, petals, 3, 9, 0.7));
  },
};

// ---------- the demo set ----------
const P = {
  saffron: ['#FFB547', '#FF8A3D', '#FFD86B', '#FFF1C9'],
  royal: ['#E0B341', '#60A5FA', '#F9E2A0', '#FFFFFF'],
  rose: ['#F472B6', '#FB923C', '#FDE68A', '#FFF7ED'],
  emerald: ['#34D399', '#F59E0B', '#A7F3D0', '#FEF3C7'],
  festive: ['#F43F5E', '#F59E0B', '#22D3EE', '#A3E635'],
};

const WALLPAPERS = [
  ['om-golden', 'Golden Om', ['sanatan-symbols'], ['om', 'aum', 'mantra'], 'om', { c1: '#7A1F0A', c2: '#220704', gold: '#F6C453', ring: '#F59E0B' }],
  ['om-midnight', 'Om in Midnight Blue', ['sanatan-symbols'], ['om', 'aum', 'meditation'], 'om', { c1: '#1E3A8A', c2: '#050B24', gold: '#FCD34D', ring: '#93C5FD' }],
  ['om-saffron', 'Saffron Om', ['sanatan-symbols'], ['om', 'bhagwa', 'saffron'], 'om', { c1: '#F97316', c2: '#7C2D12', gold: '#FFF4D6', ring: '#FFEDD5' }],
  ['mandala-saffron', 'Saffron Mandala', ['sanatan-symbols'], ['mandala', 'yantra'], 'mandala', { c1: '#9A3412', c2: '#2B0A04', petals: P.saffron }],
  ['mandala-royal', 'Royal Blue Mandala', ['sanatan-symbols', 'vishnu-bhagwan'], ['mandala', 'neel'], 'mandala', { c1: '#1E3A8A', c2: '#0B1023', petals: P.royal }],
  ['mandala-rose', 'Rose Mandala', ['sanatan-symbols', 'maa-lakshmi'], ['mandala', 'pink'], 'mandala', { c1: '#831843', c2: '#1F0612', petals: P.rose }],
  ['mandala-emerald', 'Emerald Mandala', ['sanatan-symbols', 'spiritual-nature'], ['mandala', 'green'], 'mandala', { c1: '#065F46', c2: '#04140F', petals: P.emerald }],
  ['diya-deepavali', 'Deepavali Diyas', ['festival-wallpapers'], ['diwali', 'deepavali', 'diya', 'deep'], 'diyas', { c1: '#1E1036', c2: '#5B1A0C', flame: '#FF8A00' }],
  ['diya-akhand-jyoti', 'Akhand Jyoti', ['festival-wallpapers', 'sanatan-symbols'], ['diya', 'jyoti', 'aarti'], 'diyas', { c1: '#0F172A', c2: '#3B0D0D', flame: '#FFB000' }],
  ['diya-sandhya', 'Sandhya Aarti', ['festival-wallpapers'], ['diya', 'aarti', 'evening'], 'diyas', { c1: '#3B0764', c2: '#7C2D12', flame: '#FF7A00' }],
  ['lotus-dawn', 'Lotus at Dawn', ['maa-lakshmi', 'spiritual-nature'], ['lotus', 'kamal', 'lakshmi'], 'lotus', { c1: '#FDBA74', c2: '#FDE68A', p1: '#FFE4EF', p2: '#EC4899', water: '#2A6F7F' }],
  ['lotus-moonlit', 'Moonlit Lotus', ['maa-saraswati', 'spiritual-nature'], ['lotus', 'kamal', 'saraswati'], 'lotus', { c1: '#0F172A', c2: '#334155', p1: '#FFFFFF', p2: '#C4B5FD', water: '#1E293B' }],
  ['lotus-pink', 'Pink Kamal', ['maa-lakshmi'], ['lotus', 'kamal', 'pink'], 'lotus', { c1: '#FBCFE8', c2: '#FEF3C7', p1: '#FFF1F7', p2: '#DB2777', water: '#0E7490' }],
  ['surya-dev', 'Surya Dev', ['other-deities', 'spiritual-nature'], ['surya', 'sun', 'sunrise'], 'sun', { c1: '#FDBA74', c2: '#9A3412', disc: '#FDB022' }],
  ['surya-namaskar', 'Surya Namaskar', ['other-deities'], ['surya', 'sun', 'yoga'], 'sun', { c1: '#FEF08A', c2: '#EA580C', disc: '#F59E0B' }],
  ['trishul-kailash', 'Trishul at Kailash', ['mahadev'], ['shiva', 'shiv', 'mahadev', 'trishul', 'kailash', 'bholenath'], 'trishul', { c1: '#0B1B3A', c2: '#1E3A5F', metal: '#CBD5E1' }],
  ['trishul-mahakal', 'Mahakal Night', ['mahadev'], ['shiva', 'mahakal', 'trishul', 'damru'], 'trishul', { c1: '#020617', c2: '#312E81', metal: '#E2E8F0' }],
  ['trishul-ash', 'Bhasm Blue', ['mahadev', 'shiv-parivar'], ['shiva', 'bholenath', 'trishul'], 'trishul', { c1: '#334155', c2: '#64748B', metal: '#F1F5F9' }],
  ['morpankh-blue', 'Morpankh', ['shri-krishna', 'radha-krishna'], ['krishna', 'kanha', 'morpankh', 'peacock feather', 'murli'], 'feather', { c1: '#0C4A6E', c2: '#082F49' }],
  ['morpankh-dawn', 'Murli at Dawn', ['shri-krishna'], ['krishna', 'murli', 'flute', 'bansuri'], 'feather', { c1: '#1E3A8A', c2: '#0F766E' }],
  ['morpankh-vrindavan', 'Vrindavan Evening', ['radha-krishna', 'shri-krishna'], ['krishna', 'radha', 'vrindavan'], 'feather', { c1: '#4C1D95', c2: '#0E7490' }],
  ['kodanda', 'Kodanda', ['shri-ram', 'ram-darbar'], ['ram', 'shri ram', 'dhanush', 'bow', 'jai shri ram'], 'bow', { c1: '#F97316', c2: '#7C2D12', gold: '#FCD34D' }],
  ['kodanda-ayodhya', 'Ayodhya Dawn', ['shri-ram'], ['ram', 'ayodhya', 'dhanush'], 'bow', { c1: '#FDBA74', c2: '#B45309', gold: '#FFF1C2' }],
  ['gada-sankat-mochan', 'Sankat Mochan', ['shri-hanuman'], ['hanuman', 'bajrang', 'gada', 'mace'], 'gada', { c1: '#EA580C', c2: '#7F1D1D' }],
  ['gada-bajrang', 'Bajrang Bali', ['shri-hanuman'], ['hanuman', 'bajrangbali', 'gada'], 'gada', { c1: '#DC2626', c2: '#431407' }],
  ['mandir-sandhya', 'Mandir at Sunset', ['hindu-temples'], ['temple', 'mandir', 'shikhara'], 'temple', { c1: '#7C2D12', c2: '#F59E0B', sil: '#1C0A03' }],
  ['mandir-night', 'Temple Night', ['hindu-temples', 'festival-wallpapers'], ['temple', 'mandir', 'night'], 'temple', { c1: '#0F172A', c2: '#7C3AED', sil: '#05030A' }],
  ['kalash-lakshmi', 'Lakshmi Kalash', ['maa-lakshmi', 'festival-wallpapers'], ['lakshmi', 'kalash', 'dhanteras', 'prosperity'], 'kalash', { c1: '#7F1D1D', c2: '#2A0505' }],
  ['kalash-shubh', 'Shubh Kalash', ['maa-lakshmi', 'shri-ganesh'], ['kalash', 'shubh', 'puja'], 'kalash', { c1: '#9A3412', c2: '#2A0E05' }],
  ['holi-colours', 'Holi Colours', ['festival-wallpapers'], ['holi', 'rang', 'colours'], 'holi', {}],
  ['rangoli-navratri', 'Navratri Rangoli', ['festival-wallpapers', 'maa-durga'], ['rangoli', 'navratri', 'durga'], 'rangoli', { c1: '#4C0519', petals: P.festive }],
  ['rangoli-ganesh', 'Ganesh Chaturthi Rangoli', ['shri-ganesh', 'festival-wallpapers'], ['rangoli', 'ganesh', 'chaturthi'], 'rangoli', { c1: '#7C2D12', petals: ['#F59E0B', '#EF4444', '#FDE047', '#FB7185'] }],
];

const CATEGORY_IDS = [...new Set(WALLPAPERS.flatMap((w) => w[2]))];

async function main() {
  const entries = [];
  const t0 = Date.parse('2026-10-24T06:00:00Z');
  for (const [index, [id, title, categoryIds, tags, motif, params]] of WALLPAPERS.entries()) {
    seed = 1000 + index * 37;
    const markup = motifs[motif](params);
    const dir = join(OUT, 'wallpapers', id);
    mkdirSync(dir, { recursive: true });
    const base = sharp(Buffer.from(markup), { density: 72 }).png();
    const png = await base.toBuffer();
    const original = await sharp(png).jpeg({ quality: 86, mozjpeg: true }).toBuffer();
    const preview = await sharp(png).resize({ width: 1440, height: 2560, fit: 'inside' }).webp({ quality: 78 }).toBuffer();
    const thumb = await sharp(png).resize({ width: 540, height: 1200, fit: 'inside' }).webp({ quality: 70 }).toBuffer();
    const tiny = await sharp(png).resize({ width: 16, height: 32, fit: 'inside' }).webp({ quality: 40 }).toBuffer();
    const { dominant } = await sharp(png).stats();
    const hex = (v) => v.toString(16).padStart(2, '0');
    writeFileSync(join(dir, 'original.jpg'), original);
    writeFileSync(join(dir, 'preview.webp'), preview);
    writeFileSync(join(dir, 'thumb.webp'), thumb);
    entries.push({
      id,
      title,
      categoryIds,
      tags,
      width: W,
      height: H,
      bytes: original.length,
      dominantColor: `#${hex(dominant.r)}${hex(dominant.g)}${hex(dominant.b)}`,
      placeholder: `data:image/webp;base64,${tiny.toString('base64')}`,
      publishedAt: t0 - index * 3 * 60 * 60 * 1000,
    });
    console.log(`${id}: original ${(original.length / 1024).toFixed(0)} KB, preview ${(preview.length / 1024).toFixed(0)} KB, thumb ${(thumb.length / 1024).toFixed(0)} KB`);
  }
  const ts = `// Generated by scripts/demo/generate-demo-content.mjs; do not edit by hand.
// Original abstract artwork for the DEMO build (images live on the repository's
// demo-content branch). Real builds never use this data.

export interface DemoWallpaperEntry {
  id: string;
  title: string;
  categoryIds: string[];
  tags: string[];
  width: number;
  height: number;
  bytes: number;
  dominantColor: string;
  placeholder: string;
  publishedAt: number;
}

export const DEMO_CATEGORY_IDS: readonly string[] = ${JSON.stringify(CATEGORY_IDS)};

export const DEMO_WALLPAPER_ENTRIES: readonly DemoWallpaperEntry[] = ${JSON.stringify(entries, null, 2)};
`;
  writeFileSync(join(ROOT, 'apps/user/src/demo/catalog.data.ts'), ts);
  console.log(`wrote ${entries.length} wallpapers, ${CATEGORY_IDS.length} categories`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
