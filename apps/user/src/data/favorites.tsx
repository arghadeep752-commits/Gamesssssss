import {
  collection,
  deleteDoc,
  doc,
  onSnapshot,
  orderBy,
  query,
  serverTimestamp,
  setDoc,
} from '@react-native-firebase/firestore';
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { COLLECTIONS } from '@devdarshan/shared';
import { db } from '../firebase';
import { useAuth } from './auth';

export type ToggleResult = 'added' | 'removed' | 'needs-sign-in';

interface FavoritesState {
  /** Liked wallpaper ids, newest first, as confirmed by Firestore (including pending local writes). */
  ids: string[];
  ready: boolean;
  isFavorite: (wallpaperId: string) => boolean;
  toggle: (wallpaperId: string) => Promise<ToggleResult>;
  remove: (wallpaperIds: string[]) => Promise<void>;
}

const FavoritesContext = createContext<FavoritesState | null>(null);

/**
 * Favourites live at users/{uid}/favorites/{wallpaperId}: one document per like,
 * keyed by the wallpaper id, so duplicates are impossible. A live listener keeps
 * every signed-in device in sync; Firestore queues offline changes and replays
 * them on reconnect. The heart flips immediately (optimistic) and rolls back if
 * the server rejects the write.
 */
export function FavoritesProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const uid = user?.uid ?? null;
  const [confirmed, setConfirmed] = useState<{ ids: string[]; ready: boolean }>({ ids: [], ready: false });
  const [optimistic, setOptimistic] = useState<ReadonlyMap<string, boolean>>(new Map());
  const uidRef = useRef(uid);
  uidRef.current = uid;

  useEffect(() => {
    setOptimistic(new Map());
    if (!uid) {
      setConfirmed({ ids: [], ready: true });
      return undefined;
    }
    setConfirmed({ ids: [], ready: false });
    const q = query(collection(db, COLLECTIONS.users, uid, COLLECTIONS.favorites), orderBy('createdAt', 'desc'));
    return onSnapshot(
      q,
      (snap) => setConfirmed({ ids: snap.docs.map((d) => d.id), ready: true }),
      () => setConfirmed((s) => ({ ...s, ready: true })),
    );
  }, [uid]);

  const confirmedSet = useMemo(() => new Set(confirmed.ids), [confirmed.ids]);

  // Drop optimistic entries once the listener reflects them.
  useEffect(() => {
    setOptimistic((current) => {
      if (current.size === 0) return current;
      let changed = false;
      const next = new Map(current);
      for (const [id, liked] of current) {
        if (confirmedSet.has(id) === liked) {
          next.delete(id);
          changed = true;
        }
      }
      return changed ? next : current;
    });
  }, [confirmedSet]);

  const isFavorite = useCallback(
    (id: string) => (optimistic.has(id) ? optimistic.get(id) === true : confirmedSet.has(id)),
    [optimistic, confirmedSet],
  );

  const toggle = useCallback(
    async (wallpaperId: string): Promise<ToggleResult> => {
      const currentUid = uidRef.current;
      if (!currentUid) return 'needs-sign-in';
      const liked = isFavorite(wallpaperId);
      const ref = doc(db, COLLECTIONS.users, currentUid, COLLECTIONS.favorites, wallpaperId);
      setOptimistic((m) => new Map(m).set(wallpaperId, !liked));
      try {
        if (liked) await deleteDoc(ref);
        else await setDoc(ref, { wallpaperId, createdAt: serverTimestamp() });
        return liked ? 'removed' : 'added';
      } catch (error) {
        setOptimistic((m) => {
          const next = new Map(m);
          next.delete(wallpaperId);
          return next;
        });
        throw error;
      }
    },
    [isFavorite],
  );

  const remove = useCallback(async (wallpaperIds: string[]) => {
    const currentUid = uidRef.current;
    if (!currentUid) return;
    await Promise.all(
      wallpaperIds.map((id) => deleteDoc(doc(db, COLLECTIONS.users, currentUid, COLLECTIONS.favorites, id))),
    );
  }, []);

  const ids = useMemo(() => {
    const base = confirmed.ids.filter((id) => optimistic.get(id) !== false);
    const added = [...optimistic.entries()].filter(([id, liked]) => liked && !confirmedSet.has(id)).map(([id]) => id);
    return [...added, ...base];
  }, [confirmed.ids, confirmedSet, optimistic]);

  const value = useMemo<FavoritesState>(
    () => ({ ids, ready: confirmed.ready, isFavorite, toggle, remove }),
    [ids, confirmed.ready, isFavorite, toggle, remove],
  );
  return <FavoritesContext.Provider value={value}>{children}</FavoritesContext.Provider>;
}

export function useFavorites(): FavoritesState {
  const value = useContext(FavoritesContext);
  if (!value) throw new Error('useFavorites must be used inside FavoritesProvider');
  return value;
}
