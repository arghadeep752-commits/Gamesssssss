import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { StyleSheet, Text, View, type LayoutChangeEvent } from 'react-native';
import { useBackHandler, useNav } from '../app/navigation';
import type { ArrowTone } from '../components/ArrowView';
import { Board, type CorridorOverlay } from '../components/Board';
import { Button, IconButton } from '../components/Button';
import { Hearts } from '../components/Hearts';
import { Sheet } from '../components/Sheet';
import { Stars } from '../components/Stars';
import { Toast, type ToastMessage } from '../components/Toast';
import { Screen, TierBadge } from '../components/ui';
import { RULES, TIMING } from '../config/gameConfig';
import { COLORS, RADIUS, SPACE, TYPE } from '../config/theme';
import { activeCount, inspectCorridor, prepareLevel, type CorridorInspection } from '../game/board';
import {
  livesApply,
  newSession,
  requestHint,
  restart,
  restoreSession,
  scanArrow,
  snapshotSession,
  tapArrow,
  undo,
  type SessionState,
} from '../game/session';
import type { LevelDef } from '../game/types';
import { getLevel, LEVEL_COUNT } from '../levels';
import { dailyLevel, parseDateKey } from '../levels/daily';
import { playSfx } from '../services/audio';
import { hapticBlocked, hapticFailure, hapticMove, hapticSuccess } from '../services/haptics';
import { completeDaily, completeLevel, markDailyPlayed, setCurrentLevel, setSession, spendHint, type CompletionOutcome } from '../state/progress';
import { useStore } from '../state/store';
import { fitCellSize } from '../utils/hitTest';

type GameRoute = { mode: 'level'; level: number } | { mode: 'daily'; dateKey: string };
type Modal = 'none' | 'pause' | 'complete' | 'gameover' | 'nohints' | 'error';

const TUTORIAL_TIPS: Record<number, string> = {
  1: 'Tap an arrow. It slides out the way it points.',
  2: 'Arrows cannot pass through each other. Move the one in the way first.',
  3: 'Find the order: some arrows must wait for others.',
};

function formatDailyTitle(key: string): string {
  const d = parseDateKey(key);
  if (!d) return 'Daily';
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  return `Daily · ${months[d.getMonth()]} ${d.getDate()}`;
}

export function GameScreen({ route }: { route: GameRoute }) {
  const nav = useNav();
  const store = useStore();
  const isDaily = route.mode === 'daily';
  const dateKey = route.mode === 'daily' ? route.dateKey : null;
  const levelNumber = route.mode === 'level' ? route.level : 0;

  const level: LevelDef = useMemo(
    () => (dateKey ? dailyLevel(dateKey) : getLevel(levelNumber)),
    [dateKey, levelNumber],
  );
  const prepared = useMemo(() => prepareLevel(level), [level]);
  const reduced = store.save.settings.reducedEffects;
  const hintsLeft = store.save.economy.hints;

  // ------------------------------------------------------------- state
  const [session, setSessionState] = useState<SessionState>(() => {
    const snap = store.getSave().session;
    if (snap && snap.levelId === level.id) {
      const restored = restoreSession(prepared, snap, RULES);
      if (restored) return restored;
    }
    return newSession(prepared, RULES);
  });
  const sessionRef = useRef(session);
  const [moving, setMoving] = useState<ReadonlySet<number>>(() => new Set());
  const [shakes, setShakes] = useState<Readonly<Record<number, number>>>({});
  const [flash, setFlash] = useState<Readonly<Record<number, ArrowTone>> | null>(null);
  const [scanMode, setScanMode] = useState(false);
  const [scan, setScan] = useState<{ arrowId: number; info: CorridorInspection } | null>(null);
  const [modal, setModal] = useState<Modal>('none');
  const [completion, setCompletion] = useState<CompletionOutcome | null>(null);
  const [toast, setToast] = useState<ToastMessage | null>(null);
  const [area, setArea] = useState({ w: 0, h: 0 });
  const recorded = useRef(false);
  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);
  const modalRef = useRef(modal);
  modalRef.current = modal;

  const later = useCallback((fn: () => void, ms: number) => {
    const t = setTimeout(fn, ms);
    timers.current.push(t);
    return t;
  }, []);
  const flashTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const scanTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (dateKey) store.update((s) => markDailyPlayed(s, dateKey));
    else store.update((s) => setCurrentLevel(s, levelNumber));
    return () => {
      for (const t of timers.current) clearTimeout(t);
      if (flashTimer.current) clearTimeout(flashTimer.current);
      if (scanTimer.current) clearTimeout(scanTimer.current);
      store.sync();
      void store.flush();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ------------------------------------------------------------- helpers
  const persist = useCallback(
    (s: SessionState) => {
      store.updateQuiet((save) =>
        setSession(
          save,
          s.status === 'playing'
            ? { ...snapshotSession(s), levelNumber: dateKey ? 0 : levelNumber, dailyKey: dateKey }
            : null,
        ),
      );
    },
    [store, dateKey, levelNumber],
  );

  const commit = useCallback(
    (s: SessionState) => {
      sessionRef.current = s;
      setSessionState(s);
      persist(s);
    },
    [persist],
  );

  const showScan = useCallback((value: { arrowId: number; info: CorridorInspection } | null) => {
    if (scanTimer.current) clearTimeout(scanTimer.current);
    setScan(value);
    if (value) {
      scanTimer.current = setTimeout(() => {
        scanTimer.current = null;
        setScan(null);
      }, TIMING.pathHelperVisible);
    }
  }, []);

  const showToast = useCallback((text: string, icon?: ToastMessage['icon']) => {
    setToast((prev) => ({ seq: (prev?.seq ?? 0) + 1, text, icon }));
  }, []);

  // ------------------------------------------------------------- input
  const onTap = useCallback(
    (arrowId: number) => {
      if (modalRef.current !== 'none') return;
      const s = sessionRef.current;
      if (s.status !== 'playing') return;

      if (scanMode) {
        const r = scanArrow(prepared, s, arrowId);
        setScanMode(false);
        if (r.inspection) {
          commit(r.state);
          showScan({ arrowId, info: r.inspection });
          playSfx('tap');
        }
        return;
      }

      const { state, outcome } = tapArrow(prepared, s, arrowId, RULES);
      if (outcome.kind === 'ignored') return;
      commit(state);
      if (outcome.kind === 'removed') {
        setMoving((prev) => {
          const next = new Set(prev);
          next.add(arrowId);
          return next;
        });
        if (scan) showScan(null);
        playSfx('move');
        hapticMove();
        return;
      }
      // Blocked: bump toward the obstacle and flash.
      setShakes((prev) => ({ ...prev, [arrowId]: (prev[arrowId] ?? 0) + 1 }));
      const tones: Record<number, ArrowTone> = { [arrowId]: 'error' };
      if (level.tier === 'tutorial') for (const b of outcome.blockers) tones[b] = 'blocker';
      if (flashTimer.current) clearTimeout(flashTimer.current);
      setFlash(tones);
      flashTimer.current = setTimeout(() => {
        flashTimer.current = null;
        setFlash(null);
      }, 480);
      playSfx('blocked');
      hapticBlocked();
      if (outcome.gameOver) {
        hapticFailure();
        later(() => setModal('gameover'), 520);
      }
    },
    [prepared, scanMode, commit, scan, showScan, level.tier, later],
  );

  const onExited = useCallback((arrowId: number) => {
    setMoving((prev) => {
      if (!prev.has(arrowId)) return prev;
      const next = new Set(prev);
      next.delete(arrowId);
      return next;
    });
  }, []);

  // ------------------------------------------------------------- completion
  useEffect(() => {
    if (session.status !== 'won' || moving.size > 0 || recorded.current) return;
    recorded.current = true;
    const holder: { out?: CompletionOutcome } = {};
    const final = sessionRef.current;
    store.update((save) => {
      holder.out = dateKey
        ? completeDaily(save, dateKey, level, final, Date.now())
        : completeLevel(save, level, final, LEVEL_COUNT, Date.now());
      return holder.out.save;
    });
    void store.flush();
    const out = holder.out ?? null;
    setCompletion(out);
    setModal('complete');
    playSfx('complete');
    hapticSuccess();
    if (out && out.rewardHints > 0) later(() => playSfx('reward'), 650);
    if (out && out.unlocked.length) {
      const names = out.unlocked.map((a) => a.title).join(', ');
      later(() => {
        playSfx('achievement');
        showToast(`Achievement: ${names}`, 'trophy');
      }, 1100);
    }
  }, [session.status, moving, store, dateKey, level, later, showToast]);

  // ------------------------------------------------------------- tools
  const onUndo = useCallback(() => {
    const r = undo(sessionRef.current);
    if (r.restored === null) return;
    commit(r.state);
    const restored = r.restored;
    setMoving((prev) => {
      if (!prev.has(restored)) return prev;
      const next = new Set(prev);
      next.delete(restored);
      return next;
    });
    showScan(null);
  }, [commit, showScan]);

  const onRestart = useCallback(() => {
    for (const t of timers.current) clearTimeout(t);
    timers.current = [];
    recorded.current = false;
    commit(restart(prepared, RULES));
    setMoving(new Set());
    setShakes({});
    setFlash(null);
    setScanMode(false);
    showScan(null);
    setCompletion(null);
    setModal('none');
  }, [commit, prepared, showScan]);

  const onHint = useCallback(() => {
    const s = sessionRef.current;
    if (s.status !== 'playing') return;
    setScanMode(false);
    const r = requestHint(prepared, s);
    if (r.outcome.kind === 'none') {
      if (r.outcome.reason === 'unsolvable') setModal('error');
      return;
    }
    if (r.outcome.consumed) {
      if (store.getSave().economy.hints <= 0) {
        setModal('nohints');
        return;
      }
      store.update((save) => spendHint(save) ?? save);
    }
    commit(r.state);
    showScan(null);
  }, [prepared, store, commit, showScan]);

  const onScanToggle = useCallback(() => {
    if (sessionRef.current.scansLeft <= 0 && !scanMode) {
      showToast('No scans left for this attempt');
      return;
    }
    setScanMode((v) => !v);
    showScan(null);
  }, [scanMode, showScan, showToast]);

  const onPause = useCallback(() => {
    setScanMode(false);
    setModal('pause');
  }, []);

  // ------------------------------------------------------------- navigation
  const goHome = useCallback(() => nav.resetTo({ name: 'home' }), [nav]);
  const goNext = useCallback(() => {
    if (dateKey || levelNumber >= LEVEL_COUNT) {
      nav.pop();
      return;
    }
    nav.replace({ name: 'game', mode: 'level', level: levelNumber + 1 });
  }, [nav, dateKey, levelNumber]);

  useBackHandler(() => {
    const m = modalRef.current;
    if (m === 'pause' || m === 'nohints' || m === 'error') {
      setModal('none');
      return true;
    }
    if (m === 'none' && sessionRef.current.status === 'playing') {
      setModal('pause');
      return true;
    }
    return false;
  });

  // ------------------------------------------------------------- derived view data
  const onLayout = useCallback((e: LayoutChangeEvent) => {
    const { width, height } = e.nativeEvent.layout;
    setArea((a) => (Math.abs(a.w - width) < 1 && Math.abs(a.h - height) < 1 ? a : { w: width, h: height }));
  }, []);
  const cell = fitCellSize(area.w, area.h, level.width, level.height);

  const tones = useMemo(() => {
    const t: Record<number, ArrowTone> = {};
    if (session.hintArrow !== null) t[session.hintArrow] = 'hint';
    if (scan) {
      t[scan.arrowId] = 'focus';
      for (const b of scan.info.blockers) t[b] = 'blocker';
    }
    if (flash) Object.assign(t, flash);
    return t;
  }, [session.hintArrow, scan, flash]);

  const overlay: CorridorOverlay | null = useMemo(() => {
    if (scan) return { cells: scan.info.cells, tone: 'scan' };
    if (session.hintArrow !== null && !session.removed[session.hintArrow]) {
      return { cells: inspectCorridor(prepared, session.removed, session.hintArrow).cells, tone: 'hint' };
    }
    return null;
  }, [scan, session.hintArrow, session.removed, prepared]);

  const remaining = activeCount(session.removed);
  const forgiving = !livesApply(prepared, RULES);
  let banner: { text: string; tone: 'info' | 'scan' | 'clear' | 'blocked' } | null = null;
  if (scanMode) banner = { text: 'Scan: tap an arrow to see its path', tone: 'scan' };
  else if (scan) {
    const n = scan.info.blockers.length;
    banner = n
      ? { text: `Blocked by ${n} arrow${n > 1 ? 's' : ''} (orange)`, tone: 'blocked' }
      : { text: 'Path is clear. Tap it to send it out.', tone: 'clear' };
  } else if (session.hintArrow !== null) banner = { text: 'Hint: the green arrow can leave now', tone: 'clear' };
  else if (!isDaily && TUTORIAL_TIPS[level.number]) banner = { text: TUTORIAL_TIPS[level.number], tone: 'info' };
  else if (forgiving) banner = { text: 'Practice level: blocked taps cost no hearts', tone: 'info' };

  const title = dateKey ? formatDailyTitle(dateKey) : `Level ${level.number}`;
  const playing = session.status === 'playing';

  return (
    <Screen>
      <View style={styles.header}>
        <IconButton icon="back" label="Back" onPress={nav.pop} />
        <View style={styles.titleBox}>
          <Text style={TYPE.heading} accessibilityRole="header">
            {title}
          </Text>
          <TierBadge tier={level.tier} small />
        </View>
        <IconButton icon="pause" label="Pause" onPress={onPause} disabled={!playing} />
      </View>

      <View style={styles.status}>
        <Hearts lives={session.livesLeft} max={RULES.lives} animate={!reduced} />
        <Text style={styles.counter} accessibilityLabel={`${remaining} arrows left`}>
          <Text style={styles.counterNum}>{remaining}</Text>
          {remaining === 1 ? ' arrow left' : ' arrows left'}
        </Text>
        <Text style={styles.moves}>Moves {session.moves}</Text>
      </View>

      <View style={styles.bannerSlot}>
        {banner ? (
          <View
            style={[
              styles.banner,
              banner.tone === 'blocked' && { backgroundColor: COLORS.errorSoft },
              (banner.tone === 'clear' || banner.tone === 'scan') && { backgroundColor: COLORS.hintSoft },
            ]}
          >
            <Text style={styles.bannerText} numberOfLines={2}>
              {banner.text}
            </Text>
          </View>
        ) : null}
      </View>

      <View style={styles.boardArea} onLayout={onLayout}>
        {cell > 0 ? (
          <Board
            prepared={prepared}
            cell={cell}
            removed={session.removed}
            moving={moving}
            shakes={shakes}
            tones={tones}
            pulseArrow={session.hintArrow}
            overlay={overlay}
            reducedEffects={reduced}
            disabled={modal !== 'none' || !playing}
            onTap={onTap}
            onExited={onExited}
          />
        ) : null}
      </View>

      <View style={styles.toolbar}>
        <IconButton icon="undo" label="Undo" showLabel onPress={onUndo} disabled={!playing || session.history.length === 0} />
        <IconButton
          icon="scan"
          label="Scan"
          showLabel
          badge={session.scansLeft}
          active={scanMode}
          onPress={onScanToggle}
          disabled={!playing}
        />
        <IconButton icon="bulb" label="Hint" showLabel badge={hintsLeft} onPress={onHint} disabled={!playing} />
      </View>

      {modal === 'pause' ? (
        <Sheet title="Paused" subtitle={title} reducedEffects={reduced}>
          <Button label="Resume" icon="play" onPress={() => setModal('none')} />
          <Button label="Restart" icon="restart" variant="secondary" onPress={onRestart} />
          <Button label="Settings" icon="sliders" variant="secondary" onPress={() => nav.push({ name: 'settings' })} />
          <Button label="Home" icon="home" variant="ghost" onPress={goHome} />
        </Sheet>
      ) : null}

      {modal === 'complete' && completion ? (
        <Sheet title="LEVEL COMPLETE" subtitle={title} reducedEffects={reduced}>
          <View style={styles.starsBox}>
            <Stars count={completion.result.stars} size={44} gap={8} animate={!reduced} />
            {completion.newBest && !completion.firstClear ? <Text style={styles.newBest}>New best!</Text> : null}
          </View>
          <View style={styles.statsRow}>
            <Stat label="Moves" value={completion.result.moves} />
            <Stat label="Mistakes" value={completion.result.mistakes} />
            <Stat label="Hints" value={completion.result.hints} />
          </View>
          {completion.rewardHints > 0 ? (
            <Text style={styles.reward}>
              Reward: +{completion.rewardHints} hint{completion.rewardHints > 1 ? 's' : ''}
            </Text>
          ) : null}
          {!dateKey && levelNumber < LEVEL_COUNT ? (
            <Button label="NEXT LEVEL" icon="play" onPress={goNext} />
          ) : (
            <Button label={dateKey ? 'DONE' : 'ALL LEVELS CLEARED'} icon="check" onPress={dateKey ? nav.pop : goHome} />
          )}
          <View style={styles.pair}>
            <Button label="Replay" icon="restart" variant="secondary" onPress={onRestart} style={styles.flex} />
            <Button label="HOME" icon="home" variant="secondary" onPress={goHome} style={styles.flex} />
          </View>
        </Sheet>
      ) : null}

      {modal === 'gameover' ? (
        <Sheet
          title="Out of hearts"
          subtitle="An arrow can only leave when nothing stands in its path. Clear the arrows in front first."
          reducedEffects={reduced}
        >
          <Button label="Retry" icon="restart" onPress={onRestart} />
          <Button label="Home" icon="home" variant="secondary" onPress={goHome} />
        </Sheet>
      ) : null}

      {modal === 'nohints' ? (
        <Sheet
          title="No hints left"
          subtitle="Earn hints by completing the Daily Challenge and every fifth level. Scan can still show what blocks an arrow."
          reducedEffects={reduced}
        >
          <Button label="OK" onPress={() => setModal('none')} />
        </Sheet>
      ) : null}

      {modal === 'error' ? (
        <Sheet title="No move found" subtitle="This board has no legal move. Please restart the level." reducedEffects={reduced}>
          <Button label="Restart" icon="restart" onPress={onRestart} />
        </Sheet>
      ) : null}

      <Toast message={toast} top={64} />
    </Screen>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <View style={styles.stat}>
      <Text style={styles.statValue}>{value}</Text>
      <Text style={styles.statLabel}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  header: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: SPACE.sm, height: 60 },
  titleBox: { flex: 1, alignItems: 'center', gap: 3 },
  status: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: SPACE.lg,
    height: 36,
  },
  counter: { fontSize: 14, color: COLORS.inkSoft, fontWeight: '600' },
  counterNum: { fontSize: 17, color: COLORS.ink, fontWeight: '800' },
  moves: { fontSize: 13, color: COLORS.muted, fontWeight: '600', minWidth: 66, textAlign: 'right' },
  bannerSlot: { height: 44, justifyContent: 'center', paddingHorizontal: SPACE.lg },
  banner: {
    backgroundColor: COLORS.surfaceAlt,
    borderRadius: RADIUS.sm,
    paddingHorizontal: SPACE.md,
    paddingVertical: 6,
    alignSelf: 'center',
  },
  bannerText: { fontSize: 13, color: COLORS.ink, fontWeight: '600', textAlign: 'center' },
  boardArea: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  toolbar: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: SPACE.lg,
    paddingVertical: SPACE.md,
  },
  starsBox: { alignItems: 'center', gap: SPACE.xs, marginVertical: SPACE.xs },
  newBest: { fontSize: 13, fontWeight: '700', color: COLORS.hint },
  statsRow: { flexDirection: 'row', justifyContent: 'space-around', paddingVertical: SPACE.xs },
  stat: { alignItems: 'center', minWidth: 70 },
  statValue: { fontSize: 22, fontWeight: '800', color: COLORS.ink },
  statLabel: { ...TYPE.caption },
  reward: { textAlign: 'center', fontSize: 15, fontWeight: '700', color: COLORS.hint },
  pair: { flexDirection: 'row', gap: SPACE.sm },
  flex: { flex: 1, paddingHorizontal: SPACE.md },
});
