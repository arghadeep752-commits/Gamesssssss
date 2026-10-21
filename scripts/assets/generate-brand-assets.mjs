// Generates every launcher icon and splash image for both apps from the DevDarshan
// mark (the same geometry as packages/ui/src/Logo.tsx).
//
//   node scripts/assets/generate-brand-assets.mjs   (needs `sharp`)
//
// Outputs are committed, so builds never depend on this script.
import { mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const sharp = require(process.env.SHARP_PATH || 'sharp');

const root = join(dirname(fileURLToPath(import.meta.url)), '..', '..');

const P = {
  arch: 'M15 56 V31 C15 23.5 21 19 26 15.5 C29.2 13.2 31 10.5 32 7 C33 10.5 34.8 13.2 38 15.5 C43 19 49 23.5 49 31 V56',
  base: 'M10 56 H54',
  bowl: 'M21 45 H43 C42 50.5 37.5 53 32 53 C26.5 53 22 50.5 21 45 Z',
  flame: 'M32 26.5 C35.9 30.9 37.2 34.4 37.2 37.3 C37.2 40.4 34.9 42.7 32 42.7 C29.1 42.7 26.8 40.4 26.8 37.3 C26.8 34.4 28.1 30.9 32 26.5 Z',
  core: 'M32 32.6 C33.7 34.7 34.3 36.3 34.3 37.7 C34.3 39.1 33.3 40.2 32 40.2 C30.7 40.2 29.7 39.1 29.7 37.7 C29.7 36.3 30.3 34.7 32 32.6 Z',
};

// Visual centre of the mark in its 64-unit grid.
const MARK_CENTER = { x: 32, y: 30.4 };

function mark({ arch, flame, core, halo }) {
  return `
    ${halo ? `<circle cx="32" cy="36.5" r="10.5" fill="${halo}"/>` : ''}
    <path d="${P.arch}" fill="none" stroke="${arch}" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round"/>
    <path d="${P.base}" fill="none" stroke="${arch}" stroke-width="3.2" stroke-linecap="round"/>
    <circle cx="32" cy="4.6" r="1.9" fill="${arch}"/>
    <path d="${P.flame}" fill="${flame}"/>
    <path d="${P.core}" fill="${core}"/>
    <path d="${P.bowl}" fill="${arch}"/>`;
}

function svg({ size, scale, background, colors, rounded = 0 }) {
  const tx = size / 2 - MARK_CENTER.x * scale;
  const ty = size / 2 - MARK_CENTER.y * scale;
  const bg = background
    ? `<rect width="${size}" height="${size}" rx="${rounded}" fill="${background}"/>`
    : '';
  return Buffer.from(
    `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">${bg}<g transform="translate(${tx} ${ty}) scale(${scale})">${mark(colors)}</g></svg>`,
  );
}

async function write(file, buffer) {
  mkdirSync(dirname(file), { recursive: true });
  await sharp(buffer).png({ compressionLevel: 9 }).toFile(file);
  console.log('wrote', file.replace(root + '/', ''));
}

const themes = {
  user: {
    background: '#FAF6EF',
    colors: { arch: '#B9581A', flame: '#DE9A2E', core: '#FFF4DC', halo: '#F6E7CF' },
    dark: { arch: '#E3893F', flame: '#E8AC4A', core: '#FFF4DC', halo: null },
  },
  admin: {
    background: '#2E5B43',
    colors: { arch: '#F6EEDC', flame: '#E8AC4A', core: '#FFF8E8', halo: '#3B6E53' },
    dark: { arch: '#A9D3BA', flame: '#E8AC4A', core: '#FFF8E8', halo: null },
  },
};

for (const [app, theme] of Object.entries(themes)) {
  const dir = join(root, 'apps', app, 'assets');
  // Legacy/full-bleed icon (also used as the store icon).
  await write(join(dir, 'icon.png'), svg({ size: 1024, scale: 10.4, background: theme.background, colors: theme.colors }));
  // Adaptive icon foreground: kept inside the 66/108 safe zone; background colour set in app.config.ts.
  await write(join(dir, 'adaptive-icon.png'), svg({ size: 1024, scale: 8.2, colors: theme.colors }));
  // Android 13+ themed (monochrome) icon: a single opaque colour the system tints.
  await write(
    join(dir, 'adaptive-icon-monochrome.png'),
    svg({ size: 1024, scale: 8.2, colors: { arch: '#FFFFFF', flame: '#FFFFFF', core: 'none', halo: null } }),
  );
  // Splash (Android 12+ shows it centred on the background colour).
  await write(join(dir, 'splash-icon.png'), svg({ size: 512, scale: 7.6, colors: { ...theme.colors, halo: null } }));
  await write(join(dir, 'splash-icon-dark.png'), svg({ size: 512, scale: 7.6, colors: theme.dark }));
}

// A round preview used in the README.
await write(
  join(root, 'docs', 'images', 'logo.png'),
  svg({ size: 256, scale: 2.7, background: themes.user.background, colors: themes.user.colors, rounded: 56 }),
);
