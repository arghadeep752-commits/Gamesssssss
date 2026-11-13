import type { Adjustments, Grade } from '../../modules/camero-engine';

export type AdjustmentKey = keyof Adjustments;

export type AdjustmentDef = {
  key: AdjustmentKey;
  label: string;
  min: number;
  max: number;
  step: number;
  /** Divider from UI units to native units. */
  scale: number;
  group: 'light' | 'colour' | 'detail' | 'effects';
};

/** Manual grading controls, in the order they appear. UI values are integers except exposure. */
export const ADJUSTMENTS: AdjustmentDef[] = [
  { key: 'exposure', label: 'Exposure', min: -2, max: 2, step: 0.1, scale: 1, group: 'light' },
  { key: 'brightness', label: 'Brightness', min: -100, max: 100, step: 1, scale: 100, group: 'light' },
  { key: 'contrast', label: 'Contrast', min: -100, max: 100, step: 1, scale: 100, group: 'light' },
  { key: 'highlights', label: 'Highlights', min: -100, max: 100, step: 1, scale: 100, group: 'light' },
  { key: 'shadows', label: 'Shadows', min: -100, max: 100, step: 1, scale: 100, group: 'light' },
  { key: 'whites', label: 'Whites', min: -100, max: 100, step: 1, scale: 100, group: 'light' },
  { key: 'blacks', label: 'Blacks', min: -100, max: 100, step: 1, scale: 100, group: 'light' },
  { key: 'temperature', label: 'Temperature', min: -100, max: 100, step: 1, scale: 100, group: 'colour' },
  { key: 'tint', label: 'Tint', min: -100, max: 100, step: 1, scale: 100, group: 'colour' },
  { key: 'saturation', label: 'Saturation', min: -100, max: 100, step: 1, scale: 100, group: 'colour' },
  { key: 'vibrance', label: 'Vibrance', min: -100, max: 100, step: 1, scale: 100, group: 'colour' },
  { key: 'sharpness', label: 'Sharpness', min: 0, max: 100, step: 1, scale: 100, group: 'detail' },
  { key: 'clarity', label: 'Clarity', min: -100, max: 100, step: 1, scale: 100, group: 'detail' },
  { key: 'dehaze', label: 'Dehaze', min: -100, max: 100, step: 1, scale: 100, group: 'detail' },
  { key: 'fade', label: 'Fade', min: 0, max: 100, step: 1, scale: 100, group: 'effects' },
  { key: 'vignette', label: 'Vignette', min: -100, max: 100, step: 1, scale: 100, group: 'effects' },
  { key: 'grain', label: 'Grain', min: 0, max: 100, step: 1, scale: 100, group: 'effects' },
];

export const ADJUSTMENT_MAP: Record<AdjustmentKey, AdjustmentDef> = Object.fromEntries(
  ADJUSTMENTS.map((a) => [a.key, a])
) as Record<AdjustmentKey, AdjustmentDef>;

export type UiAdjustments = Partial<Record<AdjustmentKey, number>>;

export type UiGrade = { look: string; intensity: number; adj: UiAdjustments };

export const NEUTRAL_GRADE: UiGrade = { look: 'none', intensity: 100, adj: {} };

export function isNeutral(g: UiGrade): boolean {
  return (g.look === 'none' || g.intensity === 0) && Object.values(g.adj).every((v) => !v);
}

export function hasAdjustments(adj: UiAdjustments): boolean {
  return Object.values(adj).some((v) => !!v);
}

export function toNativeGrade(g: UiGrade): Grade {
  const adj: Partial<Adjustments> = {};
  for (const def of ADJUSTMENTS) {
    const v = g.adj[def.key];
    if (v) adj[def.key] = v / def.scale;
  }
  return { look: g.look, intensity: Math.max(0, Math.min(1, g.intensity / 100)), adj };
}

export function gradeJson(g: UiGrade): string {
  return JSON.stringify(toNativeGrade(g));
}

export function formatAdjustment(def: AdjustmentDef, v: number): string {
  if (def.key === 'exposure') {
    const r = Number(v.toFixed(1));
    return r === 0 ? '0.0' : `${r > 0 ? '+' : '−'}${Math.abs(r).toFixed(1)}`;
  }
  const r = Math.round(v);
  if (def.min >= 0) return String(r);
  return r === 0 ? '0' : `${r > 0 ? '+' : '−'}${Math.abs(r)}`;
}
