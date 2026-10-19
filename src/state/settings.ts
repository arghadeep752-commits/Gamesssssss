import { I18nManager } from 'react-native';
import type { AngleMode, Grouping } from '../engine';
import { THEMES, ThemeId } from '../theme/theme';
import { KEYS, readJSON, writeJSON, writeString } from './storage';

export type ThemePref = 'system' | 'light' | 'dark';

export interface Settings {
  theme: ThemePref;
  palette: ThemeId;
  grouping: Grouping;
  angle: AngleMode;
  haptics: boolean;
  /** Scientific keys shown in portrait. */
  sci: boolean;
}

/** Indian digit grouping (12,34,567) by default on Indian locales. */
function defaultGrouping(): Grouping {
  try {
    const id = I18nManager.getConstants().localeIdentifier ?? '';
    return /[_-]IN(?:[_-]|$)/i.test(id) ? 'indian' : 'intl';
  } catch {
    return 'intl';
  }
}

export function loadSettings(): Settings {
  const defaults: Settings = {
    theme: 'system',
    palette: 'lagoon',
    grouping: defaultGrouping(),
    angle: 'deg',
    haptics: true,
    sci: false,
  };
  const saved = readJSON<Partial<Settings>>(KEYS.settings, {});
  const merged = { ...defaults, ...saved };
  if (!(merged.palette in THEMES)) {
    merged.palette = defaults.palette;
  }
  return merged;
}

export function saveSettings(settings: Settings): void {
  writeJSON(KEYS.settings, settings);
  // Read natively at launch so the first frame already has the right colors.
  writeString(KEYS.theme, settings.theme);
  writeString(KEYS.bgLight, THEMES[settings.palette].light.base);
  writeString(KEYS.bgDark, THEMES[settings.palette].dark.base);
}
