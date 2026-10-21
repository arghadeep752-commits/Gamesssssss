import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { Animated, StyleSheet, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { AppText } from './AppText';
import { Icon, type IconName } from './Icon';
import { useTheme } from './theme';
import { Touchable } from './Touchable';

export type ToastTone = 'default' | 'success' | 'error' | 'warning';

export interface ToastOptions {
  message: string;
  detail?: string;
  tone?: ToastTone;
  durationMs?: number;
  action?: { label: string; onPress: () => void };
}

interface ToastContextValue {
  show: (options: ToastOptions) => void;
  hide: () => void;
}

const ToastContext = createContext<ToastContextValue>({ show: () => undefined, hide: () => undefined });

export function useToast(): ToastContextValue {
  return useContext(ToastContext);
}

const ICON_FOR: Record<ToastTone, IconName> = {
  default: 'info',
  success: 'checkCircle',
  error: 'alert',
  warning: 'alert',
};

/** One toast at a time, above the tab bar. `bottomOffset` lifts it over fixed bottom UI. */
export function ToastProvider({ children, bottomOffset = 72 }: { children: ReactNode; bottomOffset?: number }) {
  const { colors, radii, spacing } = useTheme();
  const insets = useSafeAreaInsets();
  const [toast, setToast] = useState<(ToastOptions & { id: number }) | null>(null);
  const anim = useRef(new Animated.Value(0)).current;
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const counter = useRef(0);

  const hide = useCallback(() => {
    if (timer.current) clearTimeout(timer.current);
    Animated.timing(anim, { toValue: 0, duration: 160, useNativeDriver: true }).start(({ finished }) => {
      if (finished) setToast(null);
    });
  }, [anim]);

  const show = useCallback(
    (options: ToastOptions) => {
      if (timer.current) clearTimeout(timer.current);
      counter.current += 1;
      setToast({ ...options, id: counter.current });
      anim.setValue(0);
      Animated.timing(anim, { toValue: 1, duration: 200, useNativeDriver: true }).start();
      const duration = options.durationMs ?? (options.action || options.detail ? 5200 : 3200);
      timer.current = setTimeout(hide, duration);
    },
    [anim, hide],
  );

  useEffect(
    () => () => {
      if (timer.current) clearTimeout(timer.current);
    },
    [],
  );

  const value = useMemo(() => ({ show, hide }), [show, hide]);
  const tone = toast?.tone ?? 'default';
  const accent =
    tone === 'success' ? colors.success : tone === 'error' ? colors.danger : tone === 'warning' ? colors.warning : colors.gold;

  return (
    <ToastContext.Provider value={value}>
      {children}
      {toast ? (
        <View pointerEvents="box-none" style={[StyleSheet.absoluteFill, styles.host]}>
          <Animated.View
            accessibilityLiveRegion="polite"
            accessibilityRole="alert"
            style={[
              styles.toast,
              {
                marginBottom: insets.bottom + bottomOffset,
                marginHorizontal: spacing.lg,
                backgroundColor: colors.text,
                borderRadius: radii.md,
                opacity: anim,
                transform: [{ translateY: anim.interpolate({ inputRange: [0, 1], outputRange: [16, 0] }) }],
              },
            ]}
          >
            <Icon name={ICON_FOR[tone]} size={18} color={accent} />
            <View style={styles.texts}>
              <AppText variant="label" color={colors.background} weight="600">
                {toast.message}
              </AppText>
              {toast.detail ? (
                <AppText variant="caption" color={colors.background} style={{ opacity: 0.8, marginTop: 2 }}>
                  {toast.detail}
                </AppText>
              ) : null}
            </View>
            {toast.action ? (
              <Touchable
                onPress={() => {
                  toast.action?.onPress();
                  hide();
                }}
                accessibilityRole="button"
                style={styles.action}
              >
                <AppText variant="label" weight="700" color={colors.primarySoft}>
                  {toast.action.label}
                </AppText>
              </Touchable>
            ) : null}
          </Animated.View>
        </View>
      ) : null}
    </ToastContext.Provider>
  );
}

const styles = StyleSheet.create({
  host: {
    justifyContent: 'flex-end',
  },
  toast: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    paddingVertical: 12,
    paddingHorizontal: 14,
    elevation: 6,
    shadowColor: '#000',
    shadowOpacity: 0.18,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: 4 },
  },
  texts: {
    flex: 1,
  },
  action: {
    paddingHorizontal: 8,
    paddingVertical: 6,
    borderRadius: 8,
    overflow: 'hidden',
  },
});
