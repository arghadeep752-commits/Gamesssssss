import { memo, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { Pressable, StyleSheet, Text, View, type StyleProp, type ViewStyle } from 'react-native';
import Animated, {
  Easing,
  FadeIn,
  FadeInDown,
  FadeOut,
  useAnimatedStyle,
  useSharedValue,
  withSequence,
  withSpring,
  withTiming,
  ZoomIn,
  type SharedValue,
} from 'react-native-reanimated';
import type { Tier } from '../game/levels';
import { TIER_LABEL } from '../game/levels';
import { playSfx } from '../services/audio';
import { CoinIcon, Icon, type IconName } from './Icon';
import { RADIUS, SPACE, useTheme } from './theme';

/**
 * Pressable with a slight press-down. Uses the pressed state rather than a
 * running animation, so a button that closes its own screen leaves nothing
 * animating behind.
 */
export const Pressy = memo(function Pressy({
  onPress,
  style,
  children,
  disabled,
  sound = true,
  label,
  containerStyle,
}: {
  onPress: () => void;
  style?: StyleProp<ViewStyle>;
  /** Style for the outer touch area (e.g. flex: 1 inside a grid cell). */
  containerStyle?: StyleProp<ViewStyle>;
  children: ReactNode;
  disabled?: boolean;
  sound?: boolean;
  label?: string;
}) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      disabled={disabled}
      hitSlop={6}
      style={containerStyle}
      onPress={() => {
        if (sound) playSfx('tap');
        onPress();
      }}
    >
      {({ pressed }: { pressed: boolean }) => <View style={[style, pressed && styles.pressed, disabled && styles.disabled]}>{children}</View>}
    </Pressable>
  );
});

export const Btn = memo(function Btn({
  label,
  onPress,
  icon,
  kind = 'primary',
  style,
  disabled,
}: {
  label: string;
  onPress: () => void;
  icon?: IconName;
  kind?: 'primary' | 'secondary' | 'gold';
  style?: StyleProp<ViewStyle>;
  disabled?: boolean;
}) {
  const t = useTheme();
  const bg = kind === 'primary' ? t.accent : kind === 'gold' ? t.gold : t.surface;
  const fg = kind === 'secondary' ? t.text : t.onAccent;
  return (
    <Pressy
      onPress={onPress}
      disabled={disabled}
      label={label}
      style={[styles.btn, { backgroundColor: bg, borderColor: kind === 'secondary' ? t.border : bg }, style]}
    >
      {icon ? <Icon name={icon} size={20} color={fg} filled={icon === 'play'} /> : null}
      <Text style={[styles.btnText, { color: fg }]} numberOfLines={1}>
        {label}
      </Text>
    </Pressy>
  );
});

export const RoundBtn = memo(function RoundBtn({
  icon,
  onPress,
  label,
  badge,
  size = 48,
  tint,
  bg,
  filled,
}: {
  icon: IconName;
  onPress: () => void;
  label: string;
  badge?: string | number;
  size?: number;
  tint?: string;
  bg?: string;
  filled?: boolean;
}) {
  const t = useTheme();
  return (
    <Pressy
      onPress={onPress}
      label={label}
      style={[
        styles.round,
        { width: size, height: size, borderRadius: size / 2, backgroundColor: bg ?? t.surface, borderColor: t.border },
      ]}
    >
      <Icon name={icon} size={Math.round(size * 0.48)} color={tint ?? t.text} filled={filled} />
      {badge !== undefined ? (
        <View style={[styles.badge, { backgroundColor: t.accent, borderColor: t.bg }]}>
          <Text style={styles.badgeText}>{badge}</Text>
        </View>
      ) : null}
    </Pressy>
  );
});

/** On/off switch. */
export const Toggle = memo(function Toggle({ value, onChange, label, icon }: { value: boolean; onChange: (v: boolean) => void; label: string; icon: IconName }) {
  const t = useTheme();
  return (
    <Pressable
      accessibilityRole="switch"
      accessibilityState={{ checked: value }}
      accessibilityLabel={label}
      onPress={() => {
        playSfx('toggle');
        onChange(!value);
      }}
      style={styles.toggleRow}
    >
      <Icon name={icon} size={22} color={t.sub} />
      <Text style={[styles.toggleLabel, { color: t.text }]}>{label}</Text>
      <View style={[styles.track, { backgroundColor: value ? t.accent : t.surfaceAlt }]}>
        <View style={[styles.knob, value && styles.knobOn]} />
      </View>
    </Pressable>
  );
});

/** Lives. A heart that is lost pops and fades to grey. */
export const Hearts = memo(function Hearts({ count, max = 3, size = 26 }: { count: number; max?: number; size?: number }) {
  const items = [];
  for (let i = 0; i < max; i++) items.push(<HeartPip key={i} full={i < count} size={size} />);
  return <View style={styles.hearts}>{items}</View>;
});

const HeartPip = memo(function HeartPip({ full, size }: { full: boolean; size: number }) {
  const t = useTheme();
  const sc = useSharedValue(1);
  const first = useRef(true);
  useEffect(() => {
    if (first.current) {
      first.current = false;
      return;
    }
    sc.value = withSequence(withTiming(full ? 1.25 : 1.45, { duration: 110 }), withSpring(1, { damping: 9, stiffness: 260 }));
  }, [full, sc]);
  const st = useAnimatedStyle(() => ({ transform: [{ scale: sc.value }] }));
  return (
    <Animated.View style={st}>
      <Icon name="heart" size={size} color={full ? t.heart : t.heartEmpty} filled />
    </Animated.View>
  );
});

/** Thin progress bar; the fill grows with a transform (no layout per frame). */
export const ProgressBar = memo(function ProgressBar({ value, color, track, height = 6 }: { value: number; color: string; track: string; height?: number }) {
  const v = Math.max(0, Math.min(1, value));
  const p = useSharedValue(v);
  const last = useRef(v);
  useEffect(() => {
    if (Math.abs(last.current - v) < 0.001) return;
    last.current = v;
    p.value = withTiming(v, { duration: 260, easing: Easing.out(Easing.quad) });
  }, [v, p]);
  const st = useAnimatedStyle(() => ({ transform: [{ scaleX: Math.max(0.0001, p.value) }] }));
  return (
    <View style={[styles.bar, { height, borderRadius: height / 2, backgroundColor: track }]}>
      <Animated.View style={[StyleSheet.absoluteFill, { backgroundColor: color, borderRadius: height / 2, transformOrigin: '0% 50%' }, st]} />
    </View>
  );
});

/** Centered dialog with a dimmed backdrop. Render it only while open. */
export function Sheet({ children, onBackdrop }: { children: ReactNode; onBackdrop?: () => void }) {
  const t = useTheme();
  return (
    <Animated.View entering={FadeIn.duration(160)} exiting={FadeOut.duration(140)} style={[StyleSheet.absoluteFill, styles.sheetWrap]}>
      <Pressable style={[StyleSheet.absoluteFill, { backgroundColor: t.scrim }]} onPress={onBackdrop} accessibilityLabel="Close" />
      <Animated.View entering={FadeInDown.duration(260).easing(Easing.out(Easing.cubic))} style={[styles.sheet, { backgroundColor: t.surface }]}>
        {children}
      </Animated.View>
    </Animated.View>
  );
}


/** Small pill with an icon (or coin) and a value. */
export const Chip = memo(function Chip({
  icon,
  coin,
  text,
  onPress,
  tint,
  label,
}: {
  icon?: IconName;
  coin?: boolean;
  text: string;
  onPress?: () => void;
  tint?: string;
  label?: string;
}) {
  const t = useTheme();
  const body = (
    <>
      {coin ? <CoinIcon size={18} /> : icon ? <Icon name={icon} size={17} color={tint ?? t.accent} filled={icon === 'heart'} /> : null}
      <Text style={[styles.chipText, { color: t.text }]} numberOfLines={1}>
        {text}
      </Text>
    </>
  );
  const style = [styles.chip, { backgroundColor: t.surface, borderColor: t.border }];
  if (!onPress) return <View style={style}>{body}</View>;
  return (
    <Pressy onPress={onPress} style={style} label={label ?? text}>
      {body}
    </Pressy>
  );
});

/** "Hard" / "Super Hard" tag next to the level title. */
export const TierBadge = memo(function TierBadge({ tier }: { tier: Tier }) {
  const t = useTheme();
  if (tier === 'normal' || tier === 'easy') return null;
  const color = tier === 'super' ? t.error : t.warn;
  return (
    <View style={[styles.tier, { backgroundColor: color }]}>
      <Text style={styles.tierText}>{TIER_LABEL[tier].toUpperCase()}</Text>
    </View>
  );
});

/** Three stars that pop in one after another. */
export const StarRow = memo(function StarRow({ count, size = 44, delay = 250 }: { count: number; size?: number; delay?: number }) {
  const t = useTheme();
  useEffect(() => {
    const ids: ReturnType<typeof setTimeout>[] = [];
    for (let i = 0; i < count; i++) ids.push(setTimeout(() => playSfx('star'), delay + i * 230));
    return () => ids.forEach(clearTimeout);
  }, [count, delay]);
  return (
    <View style={styles.stars}>
      {[0, 1, 2].map((i) => (
        <View key={i} style={{ marginTop: i === 1 ? -10 : 0 }}>
          <Icon name="star" size={size} color={t.heartEmpty} filled />
          {i < count ? (
            <Animated.View entering={ZoomIn.delay(delay + i * 230).duration(260)} style={StyleSheet.absoluteFill}>
              <Icon name="star" size={size} color={t.gold} filled />
            </Animated.View>
          ) : null}
        </View>
      ))}
    </View>
  );
});

/** Number that counts up from 0 (a handful of renders, then stops). */
export function CountUp({ value, style, prefix = '' }: { value: number; style?: object; prefix?: string }) {
  const [shown, setShown] = useState(0);
  useEffect(() => {
    if (value <= 0) {
      setShown(value);
      return;
    }
    let i = 0;
    const steps = 12;
    const id = setInterval(() => {
      i++;
      setShown(Math.round((value * i) / steps));
      if (i >= steps) clearInterval(id);
    }, 45);
    return () => clearInterval(id);
  }, [value]);
  return <Text style={style}>{prefix + shown}</Text>;
}

const CONFETTI_COLORS = ['#F2B01E', '#3B6CF6', '#EE4537', '#1FAF6B', '#A855F7', '#06B6D4', '#F97316'];

/**
 * A short burst of confetti (win screen). All pieces follow one progress value
 * owned by the screen, so the screen can stop it instantly before navigating.
 */
export const Confetti = memo(function Confetti({ width, height, progress }: { width: number; height: number; progress: SharedValue<number> }) {
  const pieces = useMemo(() => {
    const out = [];
    let seed = 1234567;
    const rnd = () => {
      seed = (seed * 16807) % 2147483647;
      return seed / 2147483647;
    };
    for (let i = 0; i < 30; i++) {
      out.push({
        x: width * (0.15 + rnd() * 0.7),
        dx: (rnd() - 0.5) * width * 0.7,
        up: height * (0.25 + rnd() * 0.25),
        delay: rnd() * 0.15,
        spin: (rnd() - 0.5) * 900,
        color: CONFETTI_COLORS[i % CONFETTI_COLORS.length],
        w: 6 + rnd() * 6,
        h: 8 + rnd() * 8,
      });
    }
    return out;
  }, [width, height]);
  return (
    <View pointerEvents="none" style={[StyleSheet.absoluteFill, styles.confetti]}>
      {pieces.map((p, i) => (
        <ConfettiPiece key={i} {...p} progress={progress} startY={height * 0.42} fall={height * 0.75} />
      ))}
    </View>
  );
});

function ConfettiPiece({
  x,
  dx,
  up,
  delay,
  spin,
  color,
  w,
  h,
  startY,
  fall,
  progress,
}: {
  x: number;
  dx: number;
  up: number;
  delay: number;
  spin: number;
  color: string;
  w: number;
  h: number;
  startY: number;
  fall: number;
  progress: SharedValue<number>;
}) {
  const st = useAnimatedStyle(() => {
    const raw = (progress.value - delay) / (1 - delay);
    const k = raw < 0 ? 0 : raw > 1 ? 1 : 1 - (1 - raw) * (1 - raw);
    const y = startY - up * 4 * k * (1 - k) + fall * k * k;
    return {
      opacity: raw <= 0 ? 0 : k < 0.85 ? 1 : (1 - k) / 0.15,
      transform: [{ translateX: x + dx * k }, { translateY: y }, { rotate: `${spin * k}deg` }],
    };
  });
  return <Animated.View style={[{ position: 'absolute', left: 0, top: 0, width: w, height: h, borderRadius: 2, backgroundColor: color }, st]} />;
}

export const styles = StyleSheet.create({
  disabled: { opacity: 0.45 },
  pressed: { opacity: 0.85, transform: [{ scale: 0.96 }] },
  knobOn: { transform: [{ translateX: 20 }] },
  btn: {
    height: 56,
    borderRadius: RADIUS.pill,
    paddingHorizontal: SPACE.xl,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: SPACE.sm,
    borderWidth: 1.5,
  },
  btnText: { fontSize: 18, fontWeight: '700', letterSpacing: 0.2 },
  round: { alignItems: 'center', justifyContent: 'center', borderWidth: 1 },
  badge: {
    position: 'absolute',
    top: -4,
    right: -4,
    minWidth: 22,
    height: 22,
    borderRadius: 11,
    paddingHorizontal: 5,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 2,
  },
  badgeText: { color: '#fff', fontSize: 12, fontWeight: '800' },
  toggleRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 12, gap: SPACE.md },
  toggleLabel: { flex: 1, fontSize: 17, fontWeight: '600' },
  track: { width: 48, height: 28, borderRadius: 14, padding: 3 },
  knob: { width: 22, height: 22, borderRadius: 11, backgroundColor: '#fff' },
  hearts: { flexDirection: 'row', gap: 6, alignItems: 'center' },
  bar: { width: '100%', overflow: 'hidden' },
  sheetWrap: { alignItems: 'center', justifyContent: 'center', padding: SPACE.xl, zIndex: 50, elevation: 50 },
  sheet: { width: '100%', maxWidth: 400, borderRadius: RADIUS.xl, padding: SPACE.xl, alignItems: 'stretch', gap: SPACE.md },
  chip: { flexDirection: 'row', alignItems: 'center', gap: 6, borderWidth: 1, borderRadius: 999, paddingHorizontal: 11, height: 34 },
  chipText: { fontSize: 15, fontWeight: '800', fontVariant: ['tabular-nums'] },
  tier: { borderRadius: 6, paddingHorizontal: 7, paddingVertical: 2 },
  tierText: { color: '#fff', fontSize: 11, fontWeight: '900', letterSpacing: 0.6 },
  stars: { flexDirection: 'row', justifyContent: 'center', gap: 6, alignItems: 'flex-end' },
  // Above the dialog (which uses elevation 50 on Android).
  confetti: { zIndex: 60, elevation: 60 },
});
