import { useEffect, useState } from 'react';
import { AppState } from 'react-native';
import { localDateKey } from '../levels/daily';

/** Today's local date key; refreshes when the app returns to the foreground. */
export function useTodayKey(): string {
  const [key, setKey] = useState(() => localDateKey(new Date()));
  useEffect(() => {
    const sub = AppState.addEventListener('change', (state) => {
      if (state === 'active') setKey(localDateKey(new Date()));
    });
    return () => sub.remove();
  }, []);
  return key;
}
