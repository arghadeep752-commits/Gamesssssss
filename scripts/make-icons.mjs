/**
 * Renders the launcher icon, Android adaptive icon foreground and splash image
 * from the same vector mark used in-app (src/components/Logo.tsx).
 *
 *   npm i -D sharp && node scripts/make-icons.mjs
 *
 * The generated PNGs are committed, so normal builds do not need sharp.
 */
import { mkdirSync } from 'node:fs';
import { createRequire } from 'node:module';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const sharp = require(process.env.SHARP_PATH || 'sharp');

const here = dirname(fileURLToPath(import.meta.url));
const out = join(here, '..', 'assets', 'images');
mkdirSync(out, { recursive: true });

const NAVY = '#12204A';
const TEAL = '#0E9F87';
const WHITE = '#FFFFFF';

// Same paths as LOGO_PATHS in src/components/Logo.tsx (64-unit box).
const marks = (s = 1) => `
  <path d="M17 47V22h21" stroke="${WHITE}" stroke-width="${5 * s}" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
  <path d="M48 22l-9.5-6v12z" fill="${WHITE}" stroke="${WHITE}" stroke-width="${2 * s}" stroke-linejoin="round"/>
  <path d="M47 47H30V38" stroke="${TEAL}" stroke-width="${5 * s}" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
  <path d="M30 29l-6 9.5h12z" fill="${TEAL}" stroke="${TEAL}" stroke-width="${2 * s}" stroke-linejoin="round"/>`;

// Content box of the marks is about x 14.5..50, y 16..49.5; centre (32.25, 32.75).
const centred = (scale, size) =>
  `<g transform="translate(${size / 2} ${size / 2}) scale(${scale}) translate(-32.25 -32.75)">${marks()}</g>`;

const jobs = [
  {
    file: 'icon.png',
    size: 1024,
    svg: `<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024"><rect width="1024" height="1024" fill="${NAVY}"/>${centred(19, 1024)}</svg>`,
  },
  {
    // Adaptive icon foreground: transparent, artwork inside the central safe zone.
    file: 'adaptive-icon.png',
    size: 1024,
    svg: `<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024">${centred(12.5, 1024)}</svg>`,
  },
  {
    // Monochrome layer for Android 13+ themed icons.
    file: 'adaptive-icon-mono.png',
    size: 1024,
    svg: `<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024">${centred(12.5, 1024).replaceAll(TEAL, WHITE)}</svg>`,
  },
  {
    file: 'splash-icon.png',
    size: 512,
    svg: `<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 64 64"><rect width="64" height="64" rx="16" fill="${NAVY}"/>${marks()}</svg>`,
  },
];

for (const job of jobs) {
  const file = join(out, job.file);
  await sharp(Buffer.from(job.svg)).resize(job.size, job.size).png({ compressionLevel: 9, palette: true }).toFile(file);
  console.log('wrote', file);
}
