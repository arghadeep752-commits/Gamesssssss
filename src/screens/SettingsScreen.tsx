import { useCallback } from 'react';
import { useNav } from '../app/navigation';
import { Card, ListRow, Page, Screen, SectionTitle, ToggleRow, TopBar } from '../components/ui';
import { playSfx } from '../services/audio';
import { hapticMove } from '../services/haptics';
import { updateSettings } from '../state/progress';
import type { Settings } from '../state/saveSchema';
import { useStore } from '../state/store';

export function SettingsScreen() {
  const nav = useNav();
  const store = useStore();
  const s = store.save.settings;
  const set = useCallback(
    (patch: Partial<Settings>) => {
      store.update((save) => updateSettings(save, patch));
    },
    [store],
  );

  return (
    <Screen>
      <TopBar title="Settings" />
      <Page>
        <SectionTitle>Sound & feel</SectionTitle>
        <Card>
          <ToggleRow
            icon="sound"
            label="Sound effects"
            value={s.sfx}
            onChange={(v) => {
              set({ sfx: v });
              if (v) playSfx('tap');
            }}
          />
          <ToggleRow icon="music" label="Music" detail="Soft background loop" value={s.music} onChange={(v) => set({ music: v })} />
          <ToggleRow
            icon="vibrate"
            label="Vibration"
            detail="Haptic feedback on moves and blocked taps"
            value={s.vibration}
            onChange={(v) => {
              set({ vibration: v });
              if (v) hapticMove();
            }}
          />
          <ToggleRow
            icon="sparkle"
            label="Reduced effects"
            detail="Fewer decorative animations. Gameplay feedback stays."
            value={s.reducedEffects}
            onChange={(v) => set({ reducedEffects: v })}
            last
          />
        </Card>

        <SectionTitle>More</SectionTitle>
        <Card>
          <ListRow icon="shield" label="Privacy Preferences" onPress={() => nav.push({ name: 'privacy' })} />
          <ListRow icon="help" label="Help" onPress={() => nav.push({ name: 'help' })} />
          <ListRow icon="info" label="About" onPress={() => nav.push({ name: 'legal', doc: 'about' })} />
          <ListRow icon="doc" label="Terms of Service" onPress={() => nav.push({ name: 'legal', doc: 'terms' })} last />
        </Card>
      </Page>
    </Screen>
  );
}
