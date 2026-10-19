/**
 * Persistence and haptics through the CalcKit native module. Every call is
 * guarded so the app keeps working (without persistence) if the module is
 * unavailable.
 */
import { Platform, Vibration } from 'react-native';
import NativeCalcKit from '../specs/NativeCalcKit';

export const KEYS = {
  settings: 'settings.v1',
  tape: 'tape.v1',
  session: 'session.v1',
  /** Plain values read natively at startup to pick the window colors. */
  theme: 'theme',
  bgLight: 'bg.light',
  bgDark: 'bg.dark',
};

export function readString(key: string): string | null {
  try {
    return NativeCalcKit?.getItem(key) ?? null;
  } catch {
    return null;
  }
}

export function writeString(key: string, value: string): void {
  try {
    NativeCalcKit?.setItem(key, value);
  } catch {
    // Storage is best-effort.
  }
}

export function readJSON<T>(key: string, fallback: T): T {
  const raw = readString(key);
  if (raw == null) {
    return fallback;
  }
  try {
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

export function writeJSON(key: string, value: unknown): void {
  writeString(key, JSON.stringify(value));
}

/**
 * Tells the native side the app has drawn its first frames. The app paints
 * the whole window itself, so the window background underneath is released.
 */
export function windowReady(): void {
  try {
    NativeCalcKit?.windowReady();
  } catch {
    // Purely an optimization.
  }
}

export type HapticKind = 'tap' | 'confirm' | 'long';

export function haptic(kind: HapticKind): void {
  try {
    if (NativeCalcKit) {
      NativeCalcKit.haptic(kind);
      return;
    }
  } catch {
    // Fall through to vibration.
  }
  if (Platform.OS === 'android') {
    Vibration.vibrate(kind === 'long' ? 18 : 8);
  }
}
