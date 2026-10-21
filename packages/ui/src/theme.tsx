import { createContext, useContext, useMemo, type ReactNode } from 'react';
import { useColorScheme } from 'react-native';
import { palettes, radii, spacing, typeScale, type AppAccent, type ColorScheme, type Palette } from '@devdarshan/shared/theme';

export type ThemePreference = 'system' | 'light' | 'dark';

export interface Theme {
  accent: AppAccent;
  scheme: ColorScheme;
  colors: Palette;
  spacing: typeof spacing;
  radii: typeof radii;
  type: typeof typeScale;
}

function buildTheme(accent: AppAccent, scheme: ColorScheme): Theme {
  return { accent, scheme, colors: palettes[accent][scheme], spacing, radii, type: typeScale };
}

const ThemeContext = createContext<Theme>(buildTheme('user', 'light'));

export function ThemeProvider({
  accent,
  preference = 'system',
  children,
}: {
  accent: AppAccent;
  preference?: ThemePreference;
  children: ReactNode;
}) {
  const system = useColorScheme();
  const scheme: ColorScheme = preference === 'system' ? (system === 'dark' ? 'dark' : 'light') : preference;
  const theme = useMemo(() => buildTheme(accent, scheme), [accent, scheme]);
  return <ThemeContext.Provider value={theme}>{children}</ThemeContext.Provider>;
}

export function useTheme(): Theme {
  return useContext(ThemeContext);
}
