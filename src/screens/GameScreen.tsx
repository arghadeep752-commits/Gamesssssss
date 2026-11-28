import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { AppState, StyleSheet, Text, useWindowDimensions, View, type LayoutChangeEvent } from 'react-native';
import Animated, { FadeIn, FadeInDown, FadeOut, ZoomIn } from 'react-native-reanimated';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { bestHint, buildOccupancy, firstBlocker, type Level } from '../game/engine';
import { getDaily, getLevel, type LevelInfo } from '../game/levels';
import { playSfx } from '../services/audio';
import { hapticBlocked, hapticFailure, hapticMove, hapticSuccess } from '../services/haptics';
import { monthKeyOf, monthProgress, prettyDate } from '../state/dates';
import {
  CHEST_COINS,
  CHEST_EVERY,
  CHEST_HINTS,
  DAILY_COINS,
  DAILY_HINTS,
  HINT_COST,
  levelCoins,
  REVIVE_COST,
  skinById,
  starsFor,
} from '../state/economy';
import { useStore } from '../state/store';
import { Board, type BoardHandle } from '../ui/Board';
import { CoinIcon, Icon } from '../ui/Icon';
import { Btn, Chip, Confetti, CountUp, Hearts, ProgressBar, RoundBtn, Sheet, StarRow, TierBadge } from '../ui/kit';
import { ShapeThumb } from '../ui/ShapeThumb';
import { SPACE, useTheme } from '../ui/theme';
import { useZoom } from '../ui/zoom';
import { ZoomBar } from '../ui/ZoomBar';

/** `start` (QA builds only) opens a specific level instead of the next one. */
export type GameRoute = { mode: 'level'; start?: number } | { mode: 'daily'; dateKey: string };

const MAX_HEARTS = 3;

interface GameState {
  occ: Int16Array;
  removed: Uint8Array;
  busy: Float64Array;
  left: number;
  hearts: number;
  mistakes: number;
  over: boolean;
  revived: boolean;
  combo: number;
  bestCombo: number;
  /** Play clock: accumulated ms plus the start of the running stretch (0 = paused). */
  acc: number;
  since: number;
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
    revived: false,
    combo: 0,
    bestCombo: 0,
    acc: 0,
    since: Date.now(),
  };
}

const elapsedMs = (s: GameState) => s.acc + (s.since ? Date.now() - s.since : 0);
const fmt = (ms: number) => {
  const t = Math.floor(ms / 1000);
  return `${String(Math.floor(t / 60)).padStart(2, '0')}:${String(t % 60).padStart(2, '0')}`;
};

interface Reward {
  stars: number;
  coins: number;
  hints: number;
  time: string;
  newShape: boolean;
  chest: number;
  chestOpened: boolean;
  month?: { done: number; total: number };
}

/** mm:ss play clock; re-renders only itself once a second. */
function Clock({ get, running }: { get: () => number; running: boolean }) {
  const [, tick] = useState(0);
  useEffect(() => {
    if (!running) return;
    const id = setInterval(() => tick((n) => n + 1), 1000);
    return () => clearInterval(id);
  }, [running]);
  return <Chip icon="timer" text={fmt(get())} />;
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
  const win = useWindowDimensions();
  const { save, update } = useStore();
  const [levelNum, setLevelNum] = useState(route.mode === 'level' && route.start ? route.start : save.level);
  const [attempt, setAttempt] = useState(0);
  const info: LevelInfo = useMemo(
    () => (route.mode === 'level' ? getLevel(levelNum) : getDaily(route.dateKey)),
    [route, levelNum],
  );
  const level = info.level;
  const gameKey = `${route.mode === 'level' ? `L${levelNum}` : `D${route.dateKey}`}:${attempt}`;

  const game = useRef<{ key: string; st: GameState } | null>(null);
  if (!game.current || game.current.key !== gameKey) game.current = { key: gameKey, st: newState(level) };
  const st = () => (game.current as { st: GameState }).st;

  const tutorial = route.mode === 'level' && !route.start && levelNum <= 3 && !save.tutorial;
  const [hearts, setHearts] = useState(MAX_HEARTS);
  const [left, setLeft] = useState(level.arrows.length);
  const [hint, setHint] = useState(() => (tutorial ? bestHint(level, st().occ, st().removed) : -1));
  const [phase, setPhase] = useState<'play' | 'won' | 'lost'>('play');
  const [reward, setReward] = useState<Reward | null>(null);
  const [area, setArea] = useState<{ w: number; h: number } | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [combo, setCombo] = useState<number | null>(null);
  const [maxZoom, setMaxZoom] = useState(1);
  const zoom = useZoom();
  const boardRef = useRef<BoardHandle>(null);
  const hintRef = useRef(hint);
  hintRef.current = hint;
  const saveRef = useRef(save);
  saveRef.current = save;
  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);
  const later = (fn: () => void, ms: number) => {
    timers.current.push(setTimeout(fn, ms));
  };
  useEffect(() => () => timers.current.forEach(clearTimeout), []);

  // Pause the clock while the app is in the background.
  useEffect(() => {
    const sub = AppState.addEventListener('change', (state) => {
      const s = st();
      if (state !== 'active' && s.since) {
        s.acc += Date.now() - s.since;
        s.since = 0;
      } else if (state === 'active' && !s.since && !s.over) {
        s.since = Date.now();
      }
    });
    return () => sub.remove();
  }, []);

  const skin = skinById(save.skin);
  const ink = t.dark ? skin.dark : skin.light;

  const resetUi = useCallback((lvl: Level, withTutorialHint: boolean) => {
    timers.current.forEach(clearTimeout);
    timers.current = [];
    setHearts(MAX_HEARTS);
    setLeft(lvl.arrows.length);
    setPhase('play');
    setReward(null);
    setCombo(null);
    setHint(withTutorialHint ? bestHint(lvl, buildOccupancy(lvl), new Uint8Array(lvl.arrows.length)) : -1);
  }, []);

  const restart = useCallback(() => {
    setAttempt((a) => a + 1);
    resetUi(level, tutorial);
  }, [level, tutorial, resetUi]);

  const nextLevel = useCallback(() => {
    const n = levelNum + 1;
    setLevelNum(n);
    setAttempt(0);
    resetUi(getLevel(n).level, n <= 3 && !saveRef.current.tutorial);
  }, [levelNum, resetUi]);

  const showToast = useCallback((msg: string) => {
    setToast(msg);
    later(() => setToast(null), 2000);
  }, []);

  const finish = useCallback(() => {
    const s = st();
    if (s.since) {
      s.acc += Date.now() - s.since;
      s.since = 0;
    }
    const stars = starsFor(s.hearts, s.revived);
    const time = fmt(s.acc);
    playSfx('complete');
    hapticSuccess();
    const shape = info.shape;
    let r: Reward = { stars, coins: 0, hints: 0, time, newShape: false, chest: 0, chestOpened: false };
    if (route.mode === 'level') {
      update((sv) => {
        const firstClear = levelNum >= sv.level;
        let coins = firstClear ? levelCoins(info.tier, stars) : 5;
        let hints = 0;
        let chest = sv.chest + (firstClear ? 1 : 0);
        let chestOpened = false;
        if (chest >= CHEST_EVERY) {
          chest = 0;
          chestOpened = true;
          coins += CHEST_COINS;
          hints += CHEST_HINTS;
        }
        const newShape = shape !== 'rect' && !sv.shapes[shape];
        r = { stars, coins, hints, time, newShape, chest, chestOpened };
        return {
          ...sv,
          level: Math.max(sv.level, levelNum + 1),
          coins: sv.coins + coins,
          hints: sv.hints + hints,
          chest,
          shapes: shape === 'rect' ? sv.shapes : { ...sv.shapes, [shape]: (sv.shapes[shape] ?? 0) + 1 },
          stats: {
            ...sv.stats,
            levels: sv.stats.levels + (firstClear ? 1 : 0),
            perfect: sv.stats.perfect + (stars === 3 && firstClear ? 1 : 0),
            stars: sv.stats.stars + (firstClear ? stars : 0),
            arrows: sv.stats.arrows + level.arrows.length,
            bestStreak: Math.max(sv.stats.bestStreak, s.bestCombo),
          },
          tutorial: sv.tutorial || levelNum >= 3,
        };
      });
    } else {
      const key = route.dateKey;
      update((sv) => {
        const first = !sv.daily[key];
        const daily = { ...sv.daily, [key]: 1 };
        const newShape = shape !== 'rect' && !sv.shapes[shape];
        r = {
          stars,
          coins: first ? DAILY_COINS : 0,
          hints: first ? DAILY_HINTS : 0,
          time,
          newShape,
          chest: sv.chest,
          chestOpened: false,
          month: monthProgress(monthKeyOf(key), daily),
        };
        return {
          ...sv,
          daily,
          coins: sv.coins + r.coins,
          hints: sv.hints + r.hints,
          shapes: shape === 'rect' ? sv.shapes : { ...sv.shapes, [shape]: (sv.shapes[shape] ?? 0) + 1 },
          stats: {
            ...sv.stats,
            daily: sv.stats.daily + (first ? 1 : 0),
            arrows: sv.stats.arrows + level.arrows.length,
            bestStreak: Math.max(sv.stats.bestStreak, s.bestCombo),
          },
        };
      });
    }
    setReward(r);
    setPhase('won');
    if (r.coins > 0) later(() => playSfx('coin'), 1100);
    if (r.chestOpened) later(() => playSfx('reward'), 1500);
    // Build the next puzzle while the player looks at the result.
    if (route.mode === 'level') later(() => getLevel(levelNum + 1), 400);
  }, [route, levelNum, update, info, level]);

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
        s.combo++;
        s.bestCombo = Math.max(s.bestCombo, s.combo);
        const ms = board ? board.fly(id, 'exit', 0) : 0;
        playSfx('move');
        hapticMove();
        setLeft(s.left);
        if (s.combo >= 5 && s.combo % 5 === 0 && s.left > 0) {
          setCombo(s.combo);
          later(() => setCombo(null), 1100);
        }
        if (s.left === 0) {
          s.over = true;
          setHint(-1);
          later(finish, Math.min(ms, 520) + 160);
        } else if (tutorial) {
          setHint(bestHint(level, s.occ, s.removed));
        } else if (hintRef.current === id) {
          setHint(-1);
        }
      } else {
        const ms = board ? board.fly(id, 'bump', blk.gap) : 0;
        s.busy[id] = now + ms;
        s.combo = 0;
        playSfx('blocked');
        hapticBlocked();
        s.hearts--;
        s.mistakes++;
        setHearts(s.hearts);
        if (s.hearts <= 0) {
          s.over = true;
          if (s.since) {
            s.acc += Date.now() - s.since;
            s.since = 0;
          }
          later(() => {
            playSfx('fail');
            hapticFailure();
            setPhase('lost');
          }, ms + 140);
        }
      }
    },
    [level, tutorial, finish],
  );

  const takeHint = useCallback(() => {
    const s = st();
    if (s.over) return;
    if (hintRef.current >= 0 && !s.removed[hintRef.current]) return;
    const sv = saveRef.current;
    if (sv.hints <= 0 && sv.coins < HINT_COST) {
      showToast(`No hints left. A hint costs ${HINT_COST} coins — clear levels to earn more.`);
      return;
    }
    const id = bestHint(level, s.occ, s.removed);
    if (id < 0) return;
    playSfx('hint');
    setHint(id);
    if (sv.hints > 0) update((v) => ({ ...v, hints: Math.max(0, v.hints - 1) }));
    else {
      update((v) => ({ ...v, coins: Math.max(0, v.coins - HINT_COST) }));
      showToast(`Hint bought for ${HINT_COST} coins`);
    }
  }, [level, update, showToast]);

  const revive = useCallback(() => {
    const s = st();
    if (saveRef.current.coins < REVIVE_COST || s.revived) return;
    update((v) => ({ ...v, coins: v.coins - REVIVE_COST }));
    s.hearts = 1;
    s.over = false;
    s.revived = true;
    s.since = Date.now();
    playSfx('unlock');
    setHearts(1);
    setPhase('play');
  }, [update]);

  const toggleGrid = useCallback(() => {
    playSfx('toggle');
    update((v) => ({ ...v, settings: { ...v.settings, grid: !v.settings.grid } }));
  }, [update]);

  const getOcc = useCallback(() => st().occ, []);
  const onLayout = useCallback((e: LayoutChangeEvent) => {
    const { width, height } = e.nativeEvent.layout;
    setArea((a) => (a && Math.abs(a.w - width) < 1 && Math.abs(a.h - height) < 1 ? a : { w: width, h: height }));
  }, []);
  const onMaxZoom = useCallback((m: number) => setMaxZoom(m), []);

  const title = route.mode === 'level' ? `Level ${levelNum}` : 'Daily Challenge';
  const total = level.arrows.length;
  const s = st();

  return (
    <View style={[styles.root, { backgroundColor: t.bg, paddingTop: insets.top + 6, paddingBottom: insets.bottom + 8 }]}>
      <View style={styles.header}>
        <RoundBtn icon="home" label="Home" onPress={onExit} size={42} />
        <RoundBtn icon="restart" label="Restart level" onPress={restart} size={42} />
        <View style={styles.titleBox}>
          <Text style={[styles.title, { color: t.text }]} numberOfLines={1}>
            {title}
          </Text>
          <View style={styles.subRow}>
            <TierBadge tier={info.tier} />
            <Text style={[styles.subtitle, { color: t.sub }]} numberOfLines={1}>
              {route.mode === 'daily' ? prettyDate(route.dateKey) : info.shape === 'rect' ? 'Warm-up' : info.shapeName}
            </Text>
          </View>
        </View>
        <RoundBtn icon="gear" label="Settings" onPress={onOpenSettings} size={42} />
      </View>

      <View style={styles.status}>
        <Chip icon="arrowUR" text={`${left}/${total}`} label={`${left} arrows left`} />
        <Hearts count={hearts} size={26} />
        <Clock get={() => elapsedMs(s)} running={phase === 'play' && !s.over} />
      </View>

      <View style={styles.area} onLayout={onLayout}>
        {area ? (
          <Board
            key={gameKey}
            ref={boardRef}
            level={level}
            areaW={area.w}
            areaH={area.h}
            ink={ink}
            hintColor={t.hint}
            errorColor={t.error}
            dotColor={t.dot}
            gridColor={t.gridLine}
            thin={save.settings.thin}
            grid={save.settings.grid}
            hintId={hint}
            zoom={zoom}
            getOcc={getOcc}
            onTapArrow={onTapArrow}
            onMaxZoom={onMaxZoom}
          />
        ) : null}
        {tutorial && phase === 'play' ? (
          <Animated.View entering={FadeInDown.duration(300)} pointerEvents="none" style={[styles.tip, { backgroundColor: t.surface, borderColor: t.border }]}>
            <Text style={[styles.tipText, { color: t.text }]}>
              {levelNum === 1
                ? 'Tap the glowing arrow. It slides out the way it points.'
                : levelNum === 2
                  ? 'An arrow can only leave if nothing is in front of its head. A blocked tap costs a heart.'
                  : 'Clear every arrow to win. Stuck? Tap the bulb for a hint.'}
            </Text>
          </Animated.View>
        ) : null}
        {combo ? (
          <Animated.View key={combo} entering={ZoomIn.duration(220)} exiting={FadeOut.duration(200)} pointerEvents="none" style={[styles.combo, { backgroundColor: t.accent }]}>
            <Text style={styles.comboText}>{combo} in a row!</Text>
          </Animated.View>
        ) : null}
        {toast ? (
          <Animated.View entering={FadeIn.duration(150)} exiting={FadeOut.duration(150)} pointerEvents="none" style={[styles.toast, { backgroundColor: t.ink }]}>
            <Text style={[styles.toastText, { color: t.bg }]}>{toast}</Text>
          </Animated.View>
        ) : null}
      </View>

      <View style={styles.footer}>
        {maxZoom > 1.25 ? <ZoomBar zoom={zoom} /> : <View />}
        <View style={styles.footRight}>
          <RoundBtn
            icon="grid"
            label="Grid lines"
            onPress={toggleGrid}
            size={52}
            tint={save.settings.grid ? t.onAccent : t.text}
            bg={save.settings.grid ? t.accent : undefined}
          />
          <RoundBtn icon="bulb" label="Hint" onPress={takeHint} size={52} badge={save.hints > 0 ? save.hints : '+'} tint={t.accent} />
        </View>
      </View>

      {phase === 'won' && reward ? (
        <WinSheet
          reward={reward}
          info={info}
          title={route.mode === 'level' ? `Level ${levelNum} complete!` : 'Daily challenge done!'}
          daily={route.mode === 'daily'}
          ink={ink}
          width={win.width}
          height={win.height}
          onNext={nextLevel}
          onHome={onExit}
        />
      ) : null}

      {phase === 'lost' ? (
        <Sheet>
          <Animated.View entering={ZoomIn.delay(60).duration(300)} style={[styles.badgeCircle, { backgroundColor: t.surfaceAlt }]}>
            <Icon name="heart" size={44} color={t.heartEmpty} filled />
          </Animated.View>
          <Text style={[styles.sheetTitle, { color: t.text }]}>Out of hearts</Text>
          <Text style={[styles.sheetText, { color: t.sub }]}>
            {left} {left === 1 ? 'arrow' : 'arrows'} to go. Look for arrows with nothing in front of their head.
          </Text>
          {!s.revived ? (
            <Btn
              label={`Revive +1 heart · ${REVIVE_COST}`}
              icon="heart"
              kind="gold"
              disabled={save.coins < REVIVE_COST}
              onPress={revive}
            />
          ) : null}
          <Btn label="Try again" icon="restart" kind={s.revived || save.coins < REVIVE_COST ? 'primary' : 'secondary'} onPress={restart} />
          <Btn label="Home" kind="secondary" onPress={onExit} />
        </Sheet>
      ) : null}
    </View>
  );
}

function WinSheet({
  reward,
  info,
  title,
  daily,
  ink,
  width,
  height,
  onNext,
  onHome,
}: {
  reward: Reward;
  info: LevelInfo;
  title: string;
  daily: boolean;
  ink: string;
  width: number;
  height: number;
  onNext: () => void;
  onHome: () => void;
}) {
  const t = useTheme();
  return (
    <>
      <Sheet>
        <Text style={[styles.sheetTitle, { color: t.text }]}>{title}</Text>
        <StarRow count={reward.stars} />
        {info.shape !== 'rect' ? (
          <View style={styles.shapeRow}>
            <ShapeThumb shape={info.shape} size={52} color={ink} />
            <View style={styles.shapeText}>
              <Text style={[styles.shapeName, { color: t.text }]}>{info.shapeName}</Text>
              <Text style={[styles.shapeSub, { color: reward.newShape ? t.success : t.sub }]}>
                {reward.newShape ? 'New! Added to your collection' : 'Already in your collection'}
              </Text>
            </View>
          </View>
        ) : null}
        <View style={styles.statsRow}>
          <View style={[styles.statBox, { backgroundColor: t.surfaceAlt }]}>
            <Icon name="timer" size={18} color={t.sub} />
            <Text style={[styles.statValue, { color: t.text }]}>{reward.time}</Text>
          </View>
          <View style={[styles.statBox, { backgroundColor: t.surfaceAlt }]}>
            <CoinIcon size={20} />
            <CountUp value={reward.coins} prefix="+" style={[styles.statValue, { color: t.text }]} />
          </View>
          {reward.hints > 0 ? (
            <View style={[styles.statBox, { backgroundColor: t.accentSoft }]}>
              <Icon name="bulb" size={18} color={t.accent} />
              <Text style={[styles.statValue, { color: t.accent }]}>+{reward.hints}</Text>
            </View>
          ) : null}
        </View>
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
        ) : (
          <View style={styles.monthBox}>
            <View style={styles.monthRow}>
              <Icon name="chest" size={20} color={reward.chestOpened ? t.gold : t.sub} />
              <Text style={[styles.monthText, { color: t.text }]}>
                {reward.chestOpened ? `Chest opened! +${CHEST_COINS} coins, +${CHEST_HINTS} hint` : `Reward chest ${reward.chest}/${CHEST_EVERY}`}
              </Text>
            </View>
            <ProgressBar value={reward.chestOpened ? 1 : reward.chest / CHEST_EVERY} color={t.gold} track={t.surfaceAlt} height={8} />
          </View>
        )}
        {daily ? (
          <Btn label="Done" onPress={onHome} />
        ) : (
          <>
            <Btn label="Next level" icon="play" onPress={onNext} />
            <Btn label="Home" kind="secondary" onPress={onHome} />
          </>
        )}
      </Sheet>
      <Confetti width={width} height={height} />
    </>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1 },
  header: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: SPACE.lg, gap: SPACE.sm },
  titleBox: { flex: 1, alignItems: 'center' },
  title: { fontSize: 21, fontWeight: '900', letterSpacing: 0.2 },
  subRow: { flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 2 },
  subtitle: { fontSize: 13, fontWeight: '700' },
  status: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginTop: 10, paddingHorizontal: SPACE.lg },
  area: { flex: 1 },
  footer: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: SPACE.lg, paddingTop: 6 },
  footRight: { flexDirection: 'row', alignItems: 'center', gap: SPACE.md },
  tip: { position: 'absolute', left: SPACE.xl, right: SPACE.xl, bottom: 6, borderRadius: 16, borderWidth: 1, paddingVertical: 12, paddingHorizontal: 16 },
  tipText: { fontSize: 15, fontWeight: '600', textAlign: 'center', lineHeight: 21 },
  toast: { position: 'absolute', left: SPACE.xl, right: SPACE.xl, top: 8, borderRadius: 14, paddingVertical: 10, paddingHorizontal: 14 },
  toastText: { fontSize: 14, fontWeight: '600', textAlign: 'center' },
  combo: { position: 'absolute', alignSelf: 'center', top: 10, borderRadius: 999, paddingVertical: 6, paddingHorizontal: 14 },
  comboText: { color: '#fff', fontSize: 15, fontWeight: '900' },
  badgeCircle: { width: 84, height: 84, borderRadius: 42, alignSelf: 'center', alignItems: 'center', justifyContent: 'center', marginBottom: 4 },
  sheetTitle: { fontSize: 24, fontWeight: '900', textAlign: 'center' },
  sheetText: { fontSize: 16, textAlign: 'center', lineHeight: 22, marginBottom: 4 },
  shapeRow: { flexDirection: 'row', alignItems: 'center', gap: SPACE.md, alignSelf: 'center' },
  shapeText: { gap: 2 },
  shapeName: { fontSize: 17, fontWeight: '800' },
  shapeSub: { fontSize: 13, fontWeight: '700' },
  statsRow: { flexDirection: 'row', justifyContent: 'center', gap: SPACE.sm },
  statBox: { flexDirection: 'row', alignItems: 'center', gap: 6, borderRadius: 12, paddingVertical: 8, paddingHorizontal: 12 },
  statValue: { fontSize: 17, fontWeight: '900', fontVariant: ['tabular-nums'] },
  monthBox: { gap: 8, marginVertical: 2 },
  monthRow: { flexDirection: 'row', alignItems: 'center', gap: 8, justifyContent: 'center' },
  monthText: { fontSize: 15, fontWeight: '700' },
});
