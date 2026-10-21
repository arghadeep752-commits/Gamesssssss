import { useNavigation } from '@react-navigation/native';
import { useCallback } from 'react';
import type { Wallpaper } from '@devdarshan/shared';
import { usePreviewSessions } from '../state/previewSession';
import type { RootNavigation } from './types';

/** Opens the full-screen preview positioned on `wallpaper`, swipeable through `list`. */
export function useOpenPreview() {
  const navigation = useNavigation<RootNavigation>();
  const openSession = usePreviewSessions((s) => s.open);
  return useCallback(
    (list: Wallpaper[], wallpaper: Wallpaper) => {
      const sessionKey = openSession(list.length > 0 ? list : [wallpaper]);
      navigation.navigate('Preview', { wallpaperId: wallpaper.id, sessionKey });
    },
    [navigation, openSession],
  );
}
