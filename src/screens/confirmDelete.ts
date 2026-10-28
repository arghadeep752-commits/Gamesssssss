import { Alert } from 'react-native';
import type { useNav } from '../app/navigation';
import type { useStore } from '../state/store';

/**
 * Asks for confirmation, then erases only Arrow Flow's own saved data
 * (progress, settings, records) and returns to a fresh Home screen.
 */
export function confirmDeleteData(store: ReturnType<typeof useStore>, nav: ReturnType<typeof useNav>): void {
  Alert.alert(
    'Delete local game data?',
    'This permanently erases your levels, stars, hints, daily records, achievements and settings on this device. It cannot be undone.',
    [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Delete',
        style: 'destructive',
        onPress: () => {
          store.resetAll().then((ok) => {
            nav.resetTo({ name: 'home' });
            Alert.alert(
              ok ? 'Data deleted' : 'Could not delete everything',
              ok ? 'Arrow Flow has been reset on this device.' : 'Please try again, or clear the app data in Android settings.',
            );
          });
        },
      },
    ],
    { cancelable: true },
  );
}
