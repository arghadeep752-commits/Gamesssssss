import { createAudioPlayer, setAudioModeAsync, type AudioPlayer } from 'expo-audio';

/**
 * Sound effects and background music. Every call is fire-and-forget and
 * wrapped so audio problems can never interrupt gameplay. Settings and app
 * focus are pushed in from the store and the lifecycle hook.
 */
export type Sfx = 'tap' | 'move' | 'blocked' | 'complete' | 'reward' | 'achievement';

const SOURCES: Record<Sfx, number> = {
  tap: require('../../assets/sounds/tap.wav'),
  move: require('../../assets/sounds/move.wav'),
  blocked: require('../../assets/sounds/blocked.wav'),
  complete: require('../../assets/sounds/complete.wav'),
  reward: require('../../assets/sounds/reward.wav'),
  achievement: require('../../assets/sounds/achievement.wav'),
};
const MUSIC_SOURCE: number = require('../../assets/sounds/music.m4a');

/** Players per effect; more than one lets rapid moves overlap cleanly. */
const POOL_SIZE: Record<Sfx, number> = { tap: 1, move: 2, blocked: 1, complete: 1, reward: 1, achievement: 1 };
const SFX_VOLUME = 0.7;
const MUSIC_VOLUME = 0.28;

let sfxOn = true;
let musicOn = false;
let appActive = true;
let modeSet = false;
const pools: Partial<Record<Sfx, AudioPlayer[]>> = {};
const cursors: Partial<Record<Sfx, number>> = {};
let music: AudioPlayer | null = null;

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

function pool(name: Sfx): AudioPlayer[] {
  let p = pools[name];
  if (!p) {
    p = [];
    for (let i = 0; i < POOL_SIZE[name]; i++) {
      const player = createAudioPlayer(SOURCES[name]);
      player.volume = SFX_VOLUME;
      p.push(player);
    }
    pools[name] = p;
    cursors[name] = 0;
  }
  return p;
}

export function playSfx(name: Sfx): void {
  if (!sfxOn || !appActive) return;
  try {
    ensureMode();
    const p = pool(name);
    const i = cursors[name] ?? 0;
    cursors[name] = (i + 1) % p.length;
    const player = p[i];
    player.seekTo(0).catch(() => undefined);
    player.play();
  } catch {
    // Audio is optional; ignore device or decoder errors.
  }
}

/** Creates the players for the most frequent effects ahead of time. */
export function preloadSfx(): void {
  if (!sfxOn) return;
  try {
    ensureMode();
    pool('move');
    pool('blocked');
  } catch {
    // ignore
  }
}

function syncMusic() {
  try {
    if (musicOn && appActive) {
      ensureMode();
      if (!music) {
        music = createAudioPlayer(MUSIC_SOURCE);
        music.loop = true;
        music.volume = MUSIC_VOLUME;
      }
      music.play();
    } else if (music) {
      music.pause();
    }
  } catch {
    // ignore
  }
}

export function configureAudio(settings: { sfx: boolean; music: boolean }): void {
  sfxOn = settings.sfx;
  musicOn = settings.music;
  if (!sfxOn) releaseSfx();
  syncMusic();
}

export function setAudioAppActive(active: boolean): void {
  appActive = active;
  syncMusic();
}

function releaseSfx() {
  for (const key of Object.keys(pools) as Sfx[]) {
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

export function releaseAudio(): void {
  releaseSfx();
  if (music) {
    try {
      music.remove();
    } catch {
      // ignore
    }
    music = null;
  }
}
