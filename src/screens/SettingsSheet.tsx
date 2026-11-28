import { useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { useStore, type Settings } from '../state/store';
import { Icon } from '../ui/Icon';
import { Btn, Pressy, Sheet, Toggle } from '../ui/kit';
import { SPACE, useTheme } from '../ui/theme';

const VERSION = '2.0.0';

export function SettingsSheet({ onClose, startWithHelp = false }: { onClose: () => void; startWithHelp?: boolean }) {
  const t = useTheme();
  const { save, update, reset } = useStore();
  const [help, setHelp] = useState(startWithHelp);
  const [confirm, setConfirm] = useState(false);
  const set = (k: keyof Settings) => (v: boolean) => update((s) => ({ ...s, settings: { ...s.settings, [k]: v } }));

  if (help) {
    return (
      <Sheet onBackdrop={onClose}>
        <Text style={[styles.title, { color: t.text }]}>How to play</Text>
        {[
          ['play', 'Tap an arrow and it slides out the way it points, its body following behind.'],
          ['close', 'It can only leave if no other arrow sits in front of its head. A blocked tap costs a heart.'],
          ['heart', 'You have 3 hearts per level. Clear every arrow to win.'],
          ['bulb', 'Stuck? A hint lights up an arrow that can leave right now.'],
          ['trophy', 'Solve every daily challenge in a month to earn its trophy.'],
        ].map(([icon, text]) => (
          <View key={text} style={styles.helpRow}>
            <View style={[styles.helpIcon, { backgroundColor: t.accentSoft }]}>
              <Icon name={icon as 'play'} size={18} color={t.accent} filled={icon === 'heart' || icon === 'trophy'} />
            </View>
            <Text style={[styles.helpText, { color: t.text }]}>{text}</Text>
          </View>
        ))}
        <Btn label="Got it" onPress={() => (startWithHelp ? onClose() : setHelp(false))} />
      </Sheet>
    );
  }

  return (
    <Sheet onBackdrop={onClose}>
      <View style={styles.head}>
        <Text style={[styles.title, { color: t.text }]}>Settings</Text>
        <Pressy onPress={onClose} label="Close" style={[styles.close, { backgroundColor: t.surfaceAlt }]}>
          <Icon name="close" size={18} color={t.text} />
        </Pressy>
      </View>
      <View>
        <Toggle icon="sound" label="Sound effects" value={save.settings.sound} onChange={set('sound')} />
        <Toggle icon="music" label="Music" value={save.settings.music} onChange={set('music')} />
        <Toggle icon="vibrate" label="Vibration" value={save.settings.haptics} onChange={set('haptics')} />
        <Toggle icon="moon" label="Dark mode" value={save.settings.dark} onChange={set('dark')} />
      </View>
      <Btn label="How to play" icon="help" kind="secondary" onPress={() => setHelp(true)} />
      <Pressy
        onPress={() => {
          if (!confirm) {
            setConfirm(true);
            return;
          }
          reset();
          setConfirm(false);
          onClose();
        }}
        label="Reset progress"
        style={styles.reset}
      >
        <Icon name="trash" size={18} color={t.error} />
        <Text style={[styles.resetText, { color: t.error }]}>{confirm ? 'Tap again to erase all progress' : 'Reset progress'}</Text>
      </Pressy>
      <Text style={[styles.version, { color: t.faint }]}>Arrow Flow {VERSION} · offline · no ads</Text>
    </Sheet>
  );
}

const styles = StyleSheet.create({
  head: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  title: { fontSize: 24, fontWeight: '900' },
  close: { width: 36, height: 36, borderRadius: 18, alignItems: 'center', justifyContent: 'center' },
  helpRow: { flexDirection: 'row', alignItems: 'center', gap: SPACE.md },
  helpIcon: { width: 36, height: 36, borderRadius: 18, alignItems: 'center', justifyContent: 'center' },
  helpText: { flex: 1, fontSize: 15, lineHeight: 21, fontWeight: '500' },
  reset: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, paddingVertical: 8 },
  resetText: { fontSize: 15, fontWeight: '700' },
  version: { textAlign: 'center', fontSize: 12, fontWeight: '600' },
});
