import assert from 'node:assert/strict';
import { test } from 'node:test';

import { formatBytes, formatClock, formatDuration, formatMp, formatShutterNs, formatShutterSeconds, qualityLabel, signed } from '../src/lib/format';

test('bytes', () => {
  assert.equal(formatBytes(512), '512 B');
  assert.equal(formatBytes(1536), '1.5 KB');
  assert.equal(formatBytes(250 * 1024 * 1024), '250 MB');
  assert.equal(formatBytes(null), '—');
});

test('clock and duration', () => {
  assert.equal(formatClock(0), '00:00');
  assert.equal(formatClock(65_400), '01:05');
  assert.equal(formatClock(3_725_000), '1:02:05');
  assert.equal(formatDuration(9_600), '0:10');
  assert.equal(formatDuration(3_725_000), '1:02:05');
});

test('shutter speeds read like a camera', () => {
  assert.equal(formatShutterNs(1e9 / 250), '1/250');
  assert.equal(formatShutterNs(2e9), '2″');
  assert.equal(formatShutterSeconds(1 / 60), '1/60');
  assert.equal(formatShutterSeconds(0.5), '0.5″');
});

test('megapixels and quality names', () => {
  assert.equal(formatMp(4000, 3000), '12 MP');
  assert.equal(formatMp(3264, 2448), '8.0 MP');
  assert.equal(qualityLabel('UHD'), '4K');
  assert.equal(qualityLabel('FHD'), '1080p');
});

test('signed values use a real minus sign', () => {
  assert.equal(signed(0.04), '0.0');
  assert.equal(signed(1.26), '+1.3');
  assert.equal(signed(-0.7), '−0.7');
});
