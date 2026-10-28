import AsyncStorage from '@react-native-async-storage/async-storage';
import { STORAGE_KEYS } from '../config/appInfo';
import { LEVEL_COUNT } from '../levels';
import { defaultSave, parseSaveText, type SaveData } from '../state/saveSchema';

/**
 * Persistence for the single save object. Reads fall back from the main copy
 * to the last known-good backup to safe defaults, so a damaged write can never
 * stop the game from starting. Only the game's own keys are ever touched.
 */
export interface LoadResult {
  readonly save: SaveData;
  readonly source: 'main' | 'backup' | 'new' | 'recovered';
}

export async function loadSave(): Promise<LoadResult> {
  const now = Date.now();
  let mainText: string | null = null;
  let backupText: string | null = null;
  try {
    mainText = await AsyncStorage.getItem(STORAGE_KEYS.save);
  } catch {
    mainText = null;
  }
  const main = parseSaveText(mainText, LEVEL_COUNT, now);
  if (main) {
    // Refresh the backup with this known-good copy (best effort).
    AsyncStorage.setItem(STORAGE_KEYS.backup, JSON.stringify(main)).catch(() => undefined);
    return { save: main, source: 'main' };
  }
  try {
    backupText = await AsyncStorage.getItem(STORAGE_KEYS.backup);
  } catch {
    backupText = null;
  }
  const backup = parseSaveText(backupText, LEVEL_COUNT, now);
  if (backup) return { save: backup, source: 'backup' };
  return { save: defaultSave(now), source: mainText || backupText ? 'recovered' : 'new' };
}

export async function writeSave(save: SaveData): Promise<boolean> {
  try {
    await AsyncStorage.setItem(STORAGE_KEYS.save, JSON.stringify(save));
    return true;
  } catch {
    return false;
  }
}

/** Removes only Arrow Flow's own saved data. */
export async function deleteSave(): Promise<boolean> {
  try {
    await AsyncStorage.multiRemove([STORAGE_KEYS.save, STORAGE_KEYS.backup]);
    return true;
  } catch {
    return false;
  }
}
