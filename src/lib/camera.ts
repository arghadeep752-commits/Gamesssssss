import type { CameraCapability, CameraMode, Capabilities, VideoQuality } from '../../modules/camero-engine';

export type LensStop = {
  key: string;
  zoom: number;
  cameraId: string;
  kind: 'optical' | 'digital';
  lens: CameraCapability['lens'];
};

export function backCameras(caps: Capabilities | null): CameraCapability[] {
  return caps?.cameras.filter((c) => c.facing === 'back') ?? [];
}

export function frontCameras(caps: Capabilities | null): CameraCapability[] {
  return caps?.cameras.filter((c) => c.facing === 'front') ?? [];
}

/** The main rear camera: the logical camera if there is one, otherwise the wide lens. */
export function mainBack(caps: Capabilities | null): CameraCapability | undefined {
  const back = backCameras(caps);
  return (
    back.find((c) => c.logicalMultiCamera && c.lens === 'wide') ??
    back.find((c) => c.lens === 'wide') ??
    back[0]
  );
}

export function mainFront(caps: Capabilities | null): CameraCapability | undefined {
  return frontCameras(caps)[0];
}

export function cameraById(caps: Capabilities | null, id?: string): CameraCapability | undefined {
  return caps?.cameras.find((c) => c.id === id);
}

export function macroCamera(caps: Capabilities | null): CameraCapability | undefined {
  return backCameras(caps).find((c) => c.lens === 'macro');
}

const near = (a: number, b: number, tol = 0.04) => Math.abs(a - b) <= tol * Math.max(1, b);

/**
 * Zoom pills for the current side. Optical stops are where a physical lens sits; everything in
 * between is a crop of the wider lens and is labelled digital.
 */
export function lensStops(caps: Capabilities | null, current?: CameraCapability): LensStop[] {
  if (!caps || !current) return [];
  if (current.facing === 'front') {
    const stops: LensStop[] = [{ key: 'f1', zoom: 1, cameraId: current.id, kind: 'optical', lens: 'front' }];
    if (current.zoomMax >= 2) stops.push({ key: 'f2', zoom: 2, cameraId: current.id, kind: 'digital', lens: 'front' });
    return stops;
  }
  const main = mainBack(caps) ?? current;
  const stops: LensStop[] = [];
  if (main.zoomMin < 0.95) {
    stops.push({ key: 'uw', zoom: Math.round(main.zoomMin * 10) / 10, cameraId: main.id, kind: 'optical', lens: 'ultrawide' });
  }
  for (const cam of backCameras(caps)) {
    if (cam.id === main.id || cam.lens === 'macro') continue;
    if (cam.intrinsicZoom < 0.95 && !stops.some((s) => s.lens === 'ultrawide')) {
      stops.push({ key: `cam${cam.id}`, zoom: Math.round(cam.intrinsicZoom * 10) / 10, cameraId: cam.id, kind: 'optical', lens: 'ultrawide' });
    }
  }
  stops.push({ key: 'main', zoom: 1, cameraId: main.id, kind: 'optical', lens: 'wide' });
  for (const z of main.opticalStops ?? []) {
    if (z > 1.2 && z <= main.zoomMax && !stops.some((s) => near(s.zoom, z))) {
      stops.push({ key: `opt${z}`, zoom: z, cameraId: main.id, kind: 'optical', lens: 'tele' });
    }
  }
  for (const cam of backCameras(caps)) {
    if (cam.id === main.id || cam.lens !== 'tele') continue;
    if (!stops.some((s) => near(s.zoom, cam.intrinsicZoom))) {
      stops.push({ key: `cam${cam.id}`, zoom: Math.round(cam.intrinsicZoom * 10) / 10, cameraId: cam.id, kind: 'optical', lens: 'tele' });
    }
  }
  if (main.zoomMax >= 2 && !stops.some((s) => s.zoom > 1.5 && s.zoom < 3)) {
    stops.push({ key: 'd2', zoom: 2, cameraId: main.id, kind: 'digital', lens: 'wide' });
  }
  const top = Math.max(...stops.map((s) => s.zoom));
  if (main.zoomMax >= 8 && top < 6) {
    stops.push({ key: 'd5', zoom: Math.min(5, main.zoomMax), cameraId: main.id, kind: 'digital', lens: 'wide' });
  }
  if (main.zoomMax >= 25 && top < 12) {
    stops.push({ key: 'd10', zoom: 10, cameraId: main.id, kind: 'digital', lens: 'wide' });
  }
  return stops.sort((a, b) => a.zoom - b.zoom);
}

/** Whether the given zoom on the given camera is a native lens position. */
export function zoomKind(stops: LensStop[], cameraId: string | undefined, zoom: number): 'optical' | 'digital' {
  const hit = stops.find((s) => s.kind === 'optical' && s.cameraId === cameraId && near(s.zoom, zoom, 0.02));
  if (hit) return 'optical';
  const separate = stops.find((s) => s.cameraId === cameraId && s.kind === 'optical' && s.key.startsWith('cam'));
  if (separate && near(zoom, 1, 0.02)) return 'optical';
  return 'digital';
}

export type ModeInfo = { mode: CameraMode; label: string };

export function availableModes(caps: Capabilities | null, facing: 'back' | 'front'): ModeInfo[] {
  const cams = facing === 'front' ? frontCameras(caps) : backCameras(caps);
  const out: ModeInfo[] = [];
  out.push({ mode: 'timelapse', label: 'Time-lapse' });
  if (facing === 'back' && cams.some((c) => c.highSpeed)) out.push({ mode: 'slowmo', label: 'Slow-mo' });
  out.push({ mode: 'video', label: 'Video' });
  out.push({ mode: 'photo', label: 'Photo' });
  if (cams.some((c) => c.extensions.includes('bokeh'))) out.push({ mode: 'portrait', label: 'Portrait' });
  if (facing === 'back') out.push({ mode: 'macro', label: 'Macro' });
  out.push({ mode: 'pro', label: 'Pro' });
  return out;
}

export function isVideoMode(mode: CameraMode): boolean {
  return mode === 'video' || mode === 'slowmo' || mode === 'timelapse';
}

export function qualitiesFor(cam?: CameraCapability): VideoQuality[] {
  return cam?.video.map((v) => v.quality) ?? ['FHD'];
}

export function fpsFor(cam: CameraCapability | undefined, quality: VideoQuality): number[] {
  const v = cam?.video.find((m) => m.quality === quality);
  return v && v.fps.length ? v.fps : [30];
}

/** Rough recording bitrate in bits per second, used to estimate remaining time. */
export function estimateBitrate(quality: VideoQuality, fps: number, level: 'auto' | 'high' | 'max'): number {
  const base: Record<VideoQuality, number> = { UHD: 42e6, FHD: 16e6, HD: 9e6, SD: 4e6 };
  const mult = level === 'max' ? 1.9 : level === 'high' ? 1.25 : 1;
  return base[quality] * mult * Math.max(1, fps / 30) + 256e3;
}

export const ISO_STOPS = [50, 64, 80, 100, 125, 160, 200, 250, 320, 400, 500, 640, 800, 1000, 1250, 1600, 2000, 2500, 3200, 4000, 5000, 6400, 8000, 10000, 12800];

export const SHUTTER_STOPS = [
  1 / 8000, 1 / 6400, 1 / 5000, 1 / 4000, 1 / 3200, 1 / 2500, 1 / 2000, 1 / 1600, 1 / 1250, 1 / 1000, 1 / 800, 1 / 640,
  1 / 500, 1 / 400, 1 / 320, 1 / 250, 1 / 200, 1 / 160, 1 / 125, 1 / 100, 1 / 80, 1 / 60, 1 / 50, 1 / 40, 1 / 30,
  1 / 25, 1 / 20, 1 / 15, 1 / 13, 1 / 10, 1 / 8, 1 / 6, 1 / 5, 1 / 4, 0.3, 0.4, 0.5, 0.6, 0.8, 1,
];

export const AWB_LABELS: Record<string, { label: string; kelvin?: number }> = {
  auto: { label: 'Auto' },
  incandescent: { label: 'Tungsten', kelvin: 2800 },
  'warm-fluorescent': { label: 'Warm fluorescent', kelvin: 3200 },
  fluorescent: { label: 'Fluorescent', kelvin: 4000 },
  daylight: { label: 'Daylight', kelvin: 5500 },
  cloudy: { label: 'Cloudy', kelvin: 6500 },
  shade: { label: 'Shade', kelvin: 7500 },
  twilight: { label: 'Twilight', kelvin: 9000 },
};

export const AWB_ORDER = ['auto', 'incandescent', 'warm-fluorescent', 'fluorescent', 'daylight', 'cloudy', 'shade', 'twilight'];
