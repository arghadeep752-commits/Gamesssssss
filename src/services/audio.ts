import { createAudioPlayer, setAudioModeAsync, type AudioPlayer } from 'expo-audio';

/**
 * Sound effects: real recorded/produced sounds from Kenney's "Interface Sounds"
 * pack (CC0 public domain, kenney.nl). Every call is fire-and-forget and wrapped
 * so audio problems can never interrupt gameplay.
 */
export type Sfx = 'tap' | 'move' | 'blocked' | 'fail' | 'complete' | 'coin' | 'reward' | 'hint' | 'star' | 'toggle' | 'unlock';

type Clip = 'tap' | 'move1' | 'move2' | 'move3' | 'blocked' | 'fail' | 'complete' | 'coin' | 'reward' | 'hint' | 'star' | 'toggle' | 'unlock';

const SOURCES: Record<Clip, number> = {
  tap: require('../../assets/sounds/tap.wav'),
  move1: require('../../assets/sounds/move1.wav'),
  move2: require('../../assets/sounds/move2.wav'),
  move3: require('../../assets/sounds/move3.wav'),
  blocked: require('../../assets/sounds/blocked.wav'),
  fail: require('../../assets/sounds/fail.wav'),
  complete: require('../../assets/sounds/complete.wav'),
  coin: require('../../assets/sounds/coin.wav'),
  reward: require('../../assets/sounds/reward.wav'),
  hint: require('../../assets/sounds/hint.wav'),
  star: require('../../assets/sounds/star.wav'),
  toggle: require('../../assets/sounds/toggle.wav'),
  unlock: require('../../assets/sounds/unlock.wav'),
};

/** Players per clip; more than one lets rapid repeats overlap cleanly. */
const POOL: Partial<Record<Clip, number>> = { move1: 2, move2: 2, move3: 2, star: 2, coin: 2 };
const VOLUME: Partial<Record<Clip, number>> = { tap: 0.55, toggle: 0.55, move1: 0.8, move2: 0.8, move3: 0.8 };
const MOVES: Clip[] = ['move1', 'move2', 'move3'];

let sfxOn = true;
let appActive = true;
let modeSet = false;
let moveTurn = 0;
const pools: Partial<Record<Clip, AudioPlayer[]>> = {};
const cursors: Partial<Record<Clip, number>> = {};

function ensureMode() {
  if (modeSet) return;
  modeSet = true;
  setAudioModeAsync({
    playsInSilentMode: false,
    interruptionMode: 'mixWithOthers',
    shouldPlayInBackground: false,
    allowsRecording: false,
  }).catch(() => undefined);
}

function pool(name: Clip): AudioPlayer[] {
  let p = pools[name];
  if (!p) {
    p = [];
    for (let i = 0; i < (POOL[name] ?? 1); i++) {
      const player = createAudioPlayer(SOURCES[name]);
      player.volume = VOLUME[name] ?? 0.75;
      p.push(player);
    }
    pools[name] = p;
    cursors[name] = 0;
  }
  return p;
}

function play(name: Clip) {
  const p = pool(name);
  const i = cursors[name] ?? 0;
  cursors[name] = (i + 1) % p.length;
  const player = p[i];
  player.seekTo(0).catch(() => undefined);
  player.play();
}

export function playSfx(name: Sfx): void {
  if (!sfxOn || !appActive) return;
  try {
    ensureMode();
    if (name === 'move') {
      moveTurn = (moveTurn + 1) % MOVES.length;
      play(MOVES[moveTurn]);
    } else {
      play(name);
    }
  } catch {
    // Audio is optional; ignore device or decoder errors.
  }
}

/** Creates the players for the most frequent effects ahead of time. */
export function preloadSfx(): void {
  if (!sfxOn) return;
  try {
    ensureMode();
    for (const c of ['tap', 'move1', 'move2', 'move3', 'blocked'] as Clip[]) pool(c);
  } catch {
    // ignore
  }
}

export function configureAudio(settings: { sfx: boolean }): void {
  sfxOn = settings.sfx;
  if (!sfxOn) releaseAudio();
}

export function setAudioAppActive(active: boolean): void {
  appActive = active;
}

export function releaseAudio(): void {
  for (const key of Object.keys(pools) as Clip[]) {
    for (const p of pools[key] ?? []) {
      try {
        p.remove();
      } catch {
        // ignore
      }
    }
    delete pools[key];
  }
}
