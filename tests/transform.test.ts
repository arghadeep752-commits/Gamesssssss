import assert from 'node:assert/strict';
import { test } from 'node:test';

import type { EditTransform } from '../modules/camero-engine/src/types';
import { cropForRatio, IDENTITY, isIdentity, mirror, outputSize, rotateClockwise } from '../src/lib/transform';

type P = [number, number];

// Port of EditTransform.outputToDisplayed in gl/Affine.kt: crop, then mirrors, then undo the turn.
function toSource(t: EditTransform, [u, v]: P): P {
  let x = t.crop.x + u * t.crop.w;
  let y = t.crop.y + v * t.crop.h;
  if (t.flipH) x = 1 - x;
  if (t.flipV) y = 1 - y;
  switch (t.rotation) {
    case 90:
      return [y, 1 - x];
    case 180:
      return [1 - x, 1 - y];
    case 270:
      return [1 - y, x];
    default:
      return [x, y];
  }
}

function close(a: P, b: P) {
  assert.ok(Math.abs(a[0] - b[0]) < 1e-9 && Math.abs(a[1] - b[1]) < 1e-9, `${a} != ${b}`);
}

const samples: P[] = [
  [0, 0],
  [1, 0],
  [0, 1],
  [1, 1],
  [0.25, 0.7],
  [0.9, 0.1],
];

function transforms(): EditTransform[] {
  const out: EditTransform[] = [];
  for (const rotation of [0, 90, 180, 270] as const)
    for (const flipH of [false, true])
      for (const flipV of [false, true])
        out.push({ rotation, flipH, flipV, crop: { x: 0.1, y: 0.2, w: 0.5, h: 0.6 } });
  return out;
}

test('a quarter turn keeps every pixel, turned clockwise', () => {
  for (const t of transforms()) {
    const r = rotateClockwise(t);
    // What sat at (u, v) now sits at (1 - v, u).
    for (const [u, v] of samples) close(toSource(r, [1 - v, u]), toSource(t, [u, v]));
  }
});

test('four quarter turns are the identity', () => {
  for (const t of transforms()) {
    const back = rotateClockwise(rotateClockwise(rotateClockwise(rotateClockwise(t))));
    assert.equal(back.rotation, t.rotation);
    assert.equal(back.flipH, t.flipH);
    assert.equal(back.flipV, t.flipV);
    for (const k of ['x', 'y', 'w', 'h'] as const) assert.ok(Math.abs(back.crop[k] - t.crop[k]) < 1e-12);
  }
});

test('mirror flips what the user sees, left to right', () => {
  for (const t of transforms()) {
    const m = mirror(t);
    for (const [u, v] of samples) close(toSource(m, [1 - u, v]), toSource(t, [u, v]));
  }
});

test('identity detection', () => {
  assert.equal(isIdentity(IDENTITY), true);
  assert.equal(isIdentity(rotateClockwise(IDENTITY)), false);
  assert.equal(isIdentity(mirror(mirror(IDENTITY))), true);
});

test('ratio crops are centred and keep the requested shape', () => {
  const wide = cropForRatio(2);
  assert.deepEqual(wide, { x: 0, y: 0.25, w: 1, h: 0.5 });
  const tall = cropForRatio(0.5);
  assert.deepEqual(tall, { x: 0.25, y: 0, w: 0.5, h: 1 });
});

test('output size follows the turn and the crop, rounded to even pixels', () => {
  assert.deepEqual(outputSize(4000, 3000, IDENTITY), { width: 4000, height: 3000 });
  assert.deepEqual(outputSize(4000, 3000, rotateClockwise(IDENTITY)), { width: 3000, height: 4000 });
  const cropped: EditTransform = { ...IDENTITY, crop: { x: 0, y: 0, w: 0.5, h: 0.333 } };
  assert.deepEqual(outputSize(4000, 3000, cropped), { width: 2000, height: 1000 });
});
