import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { StyleSheet, Text, View, type LayoutChangeEvent } from 'react-native';
import Animated, { FadeIn, FadeInDown, FadeOut, ZoomIn } from 'react-native-reanimated';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { bestHint, buildOccupancy, firstBlocker, type Level } from '../game/engine';
import { getDaily, getLevel } from '../game/levels';
import { playSfx } from '../services/audio';
import { hapticBlocked, hapticFailure, hapticMove, hapticSuccess } from '../services/haptics';
import { monthKeyOf, monthProgress, prettyDate } from '../state/dates';
import { useStore } from '../state/store';
import { Board, type BoardHandle } from '../ui/Board';
import { Icon } from '../ui/Icon';
import { Btn, Hearts, ProgressBar, RoundBtn, Sheet } from '../ui/kit';
import { SPACE, useTheme } from '../ui/theme';

export type GameRoute = { mode: 'level' } | { mode: 'daily'; dateKey: string };

const MAX_HEARTS = 3;

interface GameState {
  occ: Int16Array;
  removed: Uint8Array;
  busy: Float64Array;
  left: number;
  hearts: number;
  mistakes: number;
  over: boolean;
  continued: boolean;
}

function newState(level: Level): GameState {
  return {
    occ: buildOccupancy(level),
    removed: new Uint8Array(level.arrows.length),
    busy: new Float64Array(level.arrows.length),
    left: level.arrows.length,
    hearts: MAX_HEARTS,
    mistakes: 0,
    over: false,
    continued: false,
  };
}

interface Reward {
  hint: boolean;
  perfect: boolean;
  month?: { done: number; total: number };
}

export function GameScreen({
  route,
  onExit,
  onOpenSettings,
}: {
  route: GameRoute;
  onExit: () => void;
  onOpenSettings: () => void;
}) {
  const t = useTheme();
  const insets = useSafeAreaInsets();
  const { save, update } = useStore();
  const [levelNum, setLevelNum] = useState(save.level);
  const [attempt, setAttempt] = useState(0);
  const level = useMemo(
    () => (route.mode === 'level' ? getLevel(levelNum) : getDaily(route.dateKey)),
    [route, levelNum],
  );
  const gameKey = `${route.mode === 'level' ? `L${levelNum}` : `D${route.dateKey}`}:${attempt}`;

  const game = useRef<{ key: string; st: GameState } | null>(null);
  if (!game.current || game.current.key !== gameKey) game.current = { key: gameKey, st: newState(level) };
  const st = () => (game.current as { st: GameState }).st;

  const tutorial = route.mode === 'level' && levelNum <= 2 && !save.tutorial;
  const [hearts, setHearts] = useState(MAX_HEARTS);
  const [left, setLeft] = useState(level.arrows.length);
  const [hint, setHint] = useState(() => (tutorial ? bestHint(level, st().occ, st().removed) : -1));
  const [phase, setPhase] = useState<'play' | 'won' | 'lost'>('play');
  const [reward, setReward] = useState<Reward | null>(null);
  const [area, setArea] = useState<{ w: number; h: number } | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const boardRef = useRef<BoardHandle>(null);
  const hintRef = useRef(hint);
  hintRef.current = hint;
  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);
  const later = (fn: () => void, ms: number) => {
    timers.current.push(setTimeout(fn, ms));
  };
  useEffect(() => () => timers.current.forEach(clearTimeout), []);

  const resetUi = useCallback(
    (lvl: Level, withTutorialHint: boolean) => {
      timers.current.forEach(clearTimeout);
      timers.current = [];
      setHearts(MAX_HEARTS);
      setLeft(lvl.arrows.length);
      setPhase('play');
      setReward(null);
      setHint(withTutorialHint ? bestHint(lvl, buildOccupancy(lvl), new Uint8Array(lvl.arrows.length)) : -1);
    },
    [],
  );

  const restart = useCallback(() => {
    setAttempt((a) => a + 1);
    resetUi(level, tutorial);
  }, [level, tutorial, resetUi]);

  const nextLevel = useCallback(() => {
    const n = levelNum + 1;
    setLevelNum(n);
    setAttempt(0);
    resetUi(getLevel(n), n <= 2 && !save.tutorial);
  }, [levelNum, resetUi, save.tutorial]);

  const showToast = useCallback((msg: string) => {
    setToast(msg);
    later(() => setToast(null), 1900);
  }, []);

  const win = useCallback(() => {
    const s = st();
    const perfect = s.mistakes === 0;
    playSfx('complete');
    hapticSuccess();
    let r: Reward = { hint: false, perfect };
    if (route.mode === 'level') {
      update((sv) => {
        const firstClear = levelNum >= sv.level;
        const levels = sv.stats.levels + (firstClear ? 1 : 0);
        const bonus = firstClear && levels % 3 === 0 ? 1 : 0;
        r = { hint: bonus > 0, perfect };
        return {
          ...sv,
          level: Math.max(sv.level, levelNum + 1),
          hints: sv.hints + bonus,
          stats: { ...sv.stats, levels, perfect: sv.stats.perfect + (perfect && firstClear ? 1 : 0) },
          tutorial: sv.tutorial || levelNum >= 2,
        };
      });
    } else {
      const key = route.dateKey;
      update((sv) => {
        const first = !sv.daily[key];
        const daily = { ...sv.daily, [key]: 1 };
        r = { hint: first, perfect, month: monthProgress(monthKeyOf(key), daily) };
        return {
          ...sv,
          daily,
          hints: sv.hints + (first ? 1 : 0),
          stats: { ...sv.stats, daily: sv.stats.daily + (first ? 1 : 0) },
        };
      });
    }
    setReward(r);
    setPhase('won');
    // Build the next puzzle while the player looks at the result.
    if (route.mode === 'level') later(() => getLevel(levelNum + 1), 350);
  }, [route, levelNum, update]);

  const onTapArrow = useCallback(
    (id: number) => {
      const s = st();
      if (s.over || s.removed[id]) return;
      const now = Date.now();
      if (s.busy[id] > now) return;
      const a = level.arrows[id];
      const blk = firstBlocker(level, s.occ, a);
      const board = boardRef.current;
      if (!blk) {
        s.removed[id] = 1;
        for (const c of a.cells) s.occ[c] = -1;
        s.left--;
        const ms = board ? board.fly(id, 'exit', 0) : 0;
        playSfx('move');
        hapticMove();
        setLeft(s.left);
        if (s.left === 0) {
          s.over = true;
          setHint(-1);
          later(win, Math.min(ms, 520) + 140);
        } else if (tutorial) {
          setHint(bestHint(level, s.occ, s.removed));
        } else if (hintRef.current === id) {
          setHint(-1);
        }
      } else {
        const ms = board ? board.fly(id, 'bump', blk.gap) : 0;
        s.busy[id] = now + ms;
        playSfx('blocked');
        hapticBlocked();
        s.hearts--;
        s.mistakes++;
        setHearts(s.hearts);
        if (s.hearts <= 0) {
          s.over = true;
          later(() => {
            hapticFailure();
            setPhase('lost');
          }, ms + 120);
        }
      }
    },
    [level, tutorial, win],
  );

  const takeHint = useCallback(() => {
    const s = st();
    if (s.over) return;
    if (hintRef.current >= 0 && !s.removed[hintRef.current]) return;
    if (save.hints <= 0) {
      showToast('No hints left. Clear levels and daily puzzles to earn more.');
      return;
    }
    const id = bestHint(level, s.occ, s.removed);
    if (id < 0) return;
    setHint(id);
    update((sv) => ({ ...sv, hints: Math.max(0, sv.hints - 1) }));
  }, [level, save.hints, update, showToast]);

  const keepGoing = useCallback(() => {
    const s = st();
    s.hearts = 1;
    s.over = false;
    s.continued = true;
    setHearts(1);
    setPhase('play');
  }, []);

  const getOcc = useCallback(() => st().occ, []);
  const onLayout = useCallback((e: LayoutChangeEvent) => {
    const { width, height } = e.nativeEvent.layout;
    setArea((a) => (a && Math.abs(a.w - width) < 1 && Math.abs(a.h - height) < 1 ? a : { w: width, h: height }));
  }, []);

  const title = route.mode === 'level' ? `Level ${levelNum}` : 'Daily Challenge';
  const subtitle = route.mode === 'daily' ? prettyDate(route.dateKey) : null;
  const total = level.arrows.length;

  return (
    <View style={[styles.root, { backgroundColor: t.bg, paddingTop: insets.top + 6, paddingBottom: insets.bottom + 10 }]}>
      <View style={styles.header}>
        <RoundBtn icon="back" label="Back" onPress={onExit} size={44} />
        <View style={styles.titleBox}>
          <Text style={[styles.title, { color: t.text }]} numberOfLines={1}>
            {title}
          </Text>
          {subtitle ? <Text style={[styles.subtitle, { color: t.sub }]}>{subtitle}</Text> : null}
        </View>
        <RoundBtn icon="gear" label="Settings" onPress={onOpenSettings} size={44} />
      </View>
      <View style={styles.status}>
        <Hearts count={hearts} />
        <View style={styles.progressWrap}>
          <ProgressBar value={(total - left) / Math.max(1, total)} color={t.accent} track={t.surfaceAlt} />
        </View>
      </View>

      <View style={styles.area} onLayout={onLayout}>
        {area ? (
          <Board
            key={gameKey}
            ref={boardRef}
            level={level}
            areaW={area.w}
            areaH={area.h}
            palette={t}
            hintId={hint}
            getOcc={getOcc}
            onTapArrow={onTapArrow}
          />
        ) : null}
        {tutorial && phase === 'play' ? (
          <Animated.View entering={FadeInDown.duration(300)} pointerEvents="none" style={[styles.tip, { backgroundColor: t.surface, borderColor: t.border }]}>
            <Text style={[styles.tipText, { color: t.text }]}>
              {levelNum === 1
                ? 'Tap an arrow to slide it off the board.'
                : 'An arrow can only leave if nothing is in front of its head. Blocked taps cost a heart.'}
            </Text>
          </Animated.View>
        ) : null}
        {toast ? (
          <Animated.View entering={FadeIn.duration(150)} exiting={FadeOut.duration(150)} pointerEvents="none" style={[styles.toast, { backgroundColor: t.ink }]}>
            <Text style={[styles.toastText, { color: t.bg }]}>{toast}</Text>
          </Animated.View>
        ) : null}
      </View>

      <View style={styles.footer}>
        <RoundBtn icon="restart" label="Restart level" onPress={restart} size={56} />
        <Text style={[styles.left, { color: t.sub }]}>
          {left} {left === 1 ? 'arrow' : 'arrows'} left
        </Text>
        <RoundBtn icon="bulb" label="Hint" onPress={takeHint} size={56} badge={save.hints > 0 ? save.hints : '+'} tint={t.accent} />
      </View>

      {phase === 'won' && reward ? (
        <Sheet>
          <Animated.View entering={ZoomIn.delay(80).duration(320)} style={[styles.badgeCircle, { backgroundColor: t.success }]}>
            <Icon name="check" size={46} color="#fff" strokeWidth={3} />
          </Animated.View>
          <Text style={[styles.sheetTitle, { color: t.text }]}>
            {route.mode === 'level' ? `Level ${levelNum} cleared!` : 'Daily challenge done!'}
          </Text>
          <Text style={[styles.sheetText, { color: t.sub }]}>
            {reward.perfect ? 'Perfect — not a single heart lost.' : 'Nicely untangled.'}
          </Text>
          {reward.month ? (
            <View style={styles.monthBox}>
              <View style={styles.monthRow}>
                <Icon name="trophy" size={20} color={t.gold} filled />
                <Text style={[styles.monthText, { color: t.text }]}>
                  {reward.month.done === reward.month.total ? 'Monthly trophy earned!' : `${reward.month.done} / ${reward.month.total} this month`}
                </Text>
              </View>
              <ProgressBar value={reward.month.done / reward.month.total} color={t.gold} track={t.surfaceAlt} height={8} />
            </View>
          ) : null}
          {reward.hint ? (
            <View style={[styles.pill, { backgroundColor: t.accentSoft }]}>
              <Icon name="bulb" size={18} color={t.accent} />
              <Text style={[styles.pillText, { color: t.accent }]}>+1 hint</Text>
            </View>
          ) : null}
          {route.mode === 'level' ? (
            <>
              <Btn label="Next level" icon="play" onPress={nextLevel} />
              <Btn label="Home" kind="secondary" onPress={onExit} />
            </>
          ) : (
            <Btn label="Done" onPress={onExit} />
          )}
        </Sheet>
      ) : null}

      {phase === 'lost' ? (
        <Sheet>
          <Animated.View entering={ZoomIn.delay(60).duration(300)} style={[styles.badgeCircle, { backgroundColor: t.surfaceAlt }]}>
            <Icon name="heart" size={44} color={t.heartEmpty} filled />
          </Animated.View>
          <Text style={[styles.sheetTitle, { color: t.text }]}>Out of hearts</Text>
          <Text style={[styles.sheetText, { color: t.sub }]}>Look for arrows with a clear path in front of their head.</Text>
          <Btn label="Try again" icon="restart" onPress={restart} />
          {!st().continued ? <Btn label="Keep going with 1 heart" kind="secondary" onPress={keepGoing} /> : null}
          <Btn label="Home" kind="secondary" onPress={onExit} />
        </Sheet>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1 },
  header: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: SPACE.lg, gap: SPACE.md },
  titleBox: { flex: 1, alignItems: 'center' },
  title: { fontSize: 22, fontWeight: '800', letterSpacing: 0.2 },
  subtitle: { fontSize: 13, fontWeight: '600', marginTop: 1 },
  status: { alignItems: 'center', gap: 10, marginTop: 10, paddingHorizontal: SPACE.xl },
  progressWrap: { width: '62%' },
  area: { flex: 1 },
  footer: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: SPACE.xl, paddingTop: 6 },
  left: { fontSize: 15, fontWeight: '600' },
  tip: {
    position: 'absolute',
    left: SPACE.xl,
    right: SPACE.xl,
    bottom: 6,
    borderRadius: 16,
    borderWidth: 1,
    paddingVertical: 12,
    paddingHorizontal: 16,
  },
  tipText: { fontSize: 15, fontWeight: '600', textAlign: 'center', lineHeight: 21 },
  toast: { position: 'absolute', left: SPACE.xl, right: SPACE.xl, top: 8, borderRadius: 14, paddingVertical: 10, paddingHorizontal: 14 },
  toastText: { fontSize: 14, fontWeight: '600', textAlign: 'center' },
  badgeCircle: { width: 84, height: 84, borderRadius: 42, alignSelf: 'center', alignItems: 'center', justifyContent: 'center', marginBottom: 4 },
  sheetTitle: { fontSize: 24, fontWeight: '800', textAlign: 'center' },
  sheetText: { fontSize: 16, textAlign: 'center', lineHeight: 22, marginBottom: 4 },
  monthBox: { gap: 8, marginVertical: 4 },
  monthRow: { flexDirection: 'row', alignItems: 'center', gap: 8, justifyContent: 'center' },
  monthText: { fontSize: 15, fontWeight: '700' },
  pill: { flexDirection: 'row', alignSelf: 'center', alignItems: 'center', gap: 6, borderRadius: 999, paddingVertical: 6, paddingHorizontal: 14 },
  pillText: { fontSize: 15, fontWeight: '800' },
});
