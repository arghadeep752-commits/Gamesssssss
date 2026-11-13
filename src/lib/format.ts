const MINUS = '−';

export function formatBytes(bytes: number | undefined | null): string {
  if (bytes == null || bytes < 0) return '—';
  if (bytes < 1024) return `${bytes} B`;
  const units = ['KB', 'MB', 'GB', 'TB'];
  let v = bytes / 1024;
  let i = 0;
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024;
    i++;
  }
  return `${v >= 100 ? v.toFixed(0) : v.toFixed(1)} ${units[i]}`;
}

export function formatClock(ms: number): string {
  const total = Math.max(0, Math.floor(ms / 1000));
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  const mm = String(m).padStart(2, '0');
  const ss = String(s).padStart(2, '0');
  return h > 0 ? `${h}:${mm}:${ss}` : `${mm}:${ss}`;
}

export function formatDuration(ms: number): string {
  const total = Math.max(0, Math.round(ms / 1000));
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  return `${m}:${String(s).padStart(2, '0')}`;
}

export function formatSeconds(ms: number, digits = 1): string {
  return `${(ms / 1000).toFixed(digits)} s`;
}

export function formatShutterNs(ns: number | undefined | null): string {
  if (!ns || ns <= 0) return '—';
  const s = ns / 1e9;
  if (s >= 0.3) return `${s >= 1 ? s.toFixed(s % 1 === 0 ? 0 : 1) : s.toFixed(1)}″`;
  return `1/${Math.round(1 / s)}`;
}

export function formatShutterSeconds(s: number | undefined | null): string {
  if (!s || s <= 0) return '—';
  if (s >= 0.3) return `${s.toFixed(s >= 1 && s % 1 === 0 ? 0 : 1)}″`;
  return `1/${Math.round(1 / s)}`;
}

export function signed(v: number, digits = 1): string {
  const r = Number(v.toFixed(digits));
  if (r === 0) return (0).toFixed(digits);
  return `${r > 0 ? '+' : MINUS}${Math.abs(r).toFixed(digits)}`;
}

export function signedInt(v: number): string {
  const r = Math.round(v);
  if (r === 0) return '0';
  return `${r > 0 ? '+' : MINUS}${Math.abs(r)}`;
}

export function formatFocus(diopters: number | null | undefined): string {
  if (diopters == null) return 'AF';
  if (diopters <= 0.01) return '∞';
  const m = 1 / diopters;
  if (m < 1) return `${Math.round(m * 100)} cm`;
  return `${m.toFixed(m < 10 ? 1 : 0)} m`;
}

export function formatMp(width?: number, height?: number): string {
  if (!width || !height) return '';
  const mp = (width * height) / 1e6;
  return `${mp >= 10 ? Math.round(mp) : mp.toFixed(1)} MP`;
}

export function qualityLabel(q?: string): string {
  switch (q) {
    case 'UHD':
      return '4K';
    case 'FHD':
      return '1080p';
    case 'HD':
      return '720p';
    case 'SD':
      return '480p';
    default:
      return q ?? '';
  }
}

export function formatDate(ms: number): string {
  const d = new Date(ms);
  try {
    return d.toLocaleString(undefined, { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
  } catch {
    return d.toISOString().slice(0, 16).replace('T', ' ');
  }
}

export function formatDay(ms: number): string {
  const d = new Date(ms);
  try {
    return d.toLocaleDateString(undefined, { day: 'numeric', month: 'long', year: 'numeric' });
  } catch {
    return d.toISOString().slice(0, 10);
  }
}

export function formatTime(ms: number): string {
  const d = new Date(ms);
  try {
    return d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
  } catch {
    return d.toISOString().slice(11, 16);
  }
}

export function formatZoom(z: number): string {
  if (z < 1) return `${z.toFixed(1).replace(/^0/, '')}×`;
  if (z < 10) return `${Number(z.toFixed(1))}×`;
  return `${Math.round(z)}×`;
}
