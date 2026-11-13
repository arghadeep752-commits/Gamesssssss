import assert from 'node:assert/strict';
import { test } from 'node:test';

import type { CameraCapability, Capabilities } from '../modules/camero-engine/src/types';
import { availableModes, lensStops, mainBack, zoomKind } from '../src/lib/camera';

function cam(over: Partial<CameraCapability>): CameraCapability {
  return {
    id: '0',
    facing: 'back',
    lens: 'wide',
    fixedFocus: false,
    intrinsicZoom: 1,
    sensorOrientation: 90,
    hasFlash: true,
    hardwareLevel: 'full',
    zoomMin: 1,
    zoomMax: 8,
    logicalMultiCamera: false,
    opticalStops: [1],
    exposureSupported: true,
    exposureMin: -12,
    exposureMax: 12,
    exposureStep: 1 / 6,
    manualSensor: true,
    manualFocus: true,
    minFocusDiopters: 10,
    awbModes: ['auto'],
    awbLock: true,
    aeLock: true,
    ois: false,
    eis: false,
    previewStabilization: false,
    videoStabilization: false,
    raw: false,
    ultraHdr: false,
    video: [{ quality: 'FHD', fps: [30] }],
    hdrVideo: false,
    hdrQualities: [],
    highSpeed: null,
    extensions: [],
    ...over,
  };
}

function caps(cameras: CameraCapability[]): Capabilities {
  return {
    cameras,
    device: {
      manufacturer: 'test',
      model: 'phone',
      sdk: 33,
      release: '13',
      totalRamMb: 4096,
      lowRam: false,
      tier: 'mid',
      maxTextureSize: 8192,
      gyroscope: true,
      accelerometer: true,
    },
    codecs: { h264: true, h264Max: '1920x1080', hevc: false },
  };
}

test('a single wide camera gets 1x plus labelled digital stops', () => {
  const c = caps([cam({ id: '0', zoomMax: 10 })]);
  const stops = lensStops(c, mainBack(c));
  assert.deepEqual(
    stops.map((s) => [s.zoom, s.kind]),
    [
      [1, 'optical'],
      [2, 'digital'],
      [5, 'digital'],
    ]
  );
  assert.equal(zoomKind(stops, '0', 1), 'optical');
  assert.equal(zoomKind(stops, '0', 2), 'digital');
});

test('a logical camera with ultra-wide and tele lenses shows them as optical', () => {
  const c = caps([cam({ id: '0', logicalMultiCamera: true, zoomMin: 0.6, zoomMax: 30, opticalStops: [0.6, 1, 3] })]);
  const stops = lensStops(c, mainBack(c));
  assert.deepEqual(
    stops.filter((s) => s.kind === 'optical').map((s) => s.zoom),
    [0.6, 1, 3]
  );
  assert.ok(stops.some((s) => s.zoom === 10 && s.kind === 'digital'));
});

test('slow motion and portrait only appear when a camera supports them', () => {
  const plain = caps([cam({})]);
  const modes = availableModes(plain, 'back').map((m) => m.mode);
  assert.ok(!modes.includes('slowmo'));
  assert.ok(!modes.includes('portrait'));
  assert.ok(modes.includes('macro'));

  const rich = caps([cam({ highSpeed: { qualities: ['HD'], fps: [120] }, extensions: ['bokeh'] })]);
  const richModes = availableModes(rich, 'back').map((m) => m.mode);
  assert.ok(richModes.includes('slowmo'));
  assert.ok(richModes.includes('portrait'));
});
