import { useSettings } from '../state/settings';
import { accents } from './tokens';

/** Current accent colour from settings. */
export function useAccent(): string {
  const key = useSettings((s) => s.accent);
  return accents[key]?.color ?? accents.tungsten.color;
}

export function withAlpha(hex: string, alpha: number): string {
  const v = hex.replace('#', '');
  const r = parseInt(v.slice(0, 2), 16);
  const g = parseInt(v.slice(2, 4), 16);
  const b = parseInt(v.slice(4, 6), 16);
  return `rgba(${r},${g},${b},${alpha})`;
}
