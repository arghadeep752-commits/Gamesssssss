import { useState } from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import type { LegalId } from '../legal/docs';
import { APP_INFO } from '../legal/docs';
import { HINT_COST, REVIVE_COST } from '../state/economy';
import { useStore, type Settings } from '../state/store';
import { Icon, type IconName } from '../ui/Icon';
import { Btn, Pressy, Sheet, Toggle } from '../ui/kit';
import { SPACE, useTheme } from '../ui/theme';

export function SettingsSheet({ onClose, onLegal }: { onClose: () => void; onLegal: (doc: LegalId) => void }) {
  const t = useTheme();
  const { save, update, reset } = useStore();
  const [help, setHelp] = useState(false);
  const [confirm, setConfirm] = useState(false);
  const set = (k: keyof Settings) => (v: boolean) => update((s) => ({ ...s, settings: { ...s.settings, [k]: v } }));

  if (help) {
    const rows: [IconName, string][] = [
      ['play', 'Tap an arrow and it slides out the way it points, its body following behind.'],
      ['close', 'It can only leave if no other arrow sits in front of its head. A blocked tap costs a heart.'],
      ['heart', 'You have 3 hearts per level. Clear every arrow to win; fewer mistakes earn more stars and coins.'],
      ['plus', 'Pinch or use the zoom bar to zoom in on big boards; drag with one finger to move around.'],
      ['grid', 'The # button shows grid lines that make long rows easier to follow.'],
      ['bulb', `A hint lights up an arrow that can leave right now. Out of hints? One costs ${HINT_COST} coins.`],
      ['chest', 'Every 5 levels opens a reward chest. Solve all daily challenges in a month for a trophy.'],
    ];
    return (
      <Sheet onBackdrop={onClose}>
        <Text style={[styles.title, { color: t.text }]}>How to play</Text>
        {rows.map(([icon, text]) => (
          <View key={text} style={styles.helpRow}>
            <View style={[styles.helpIcon, { backgroundColor: t.accentSoft }]}>
              <Icon name={icon} size={18} color={t.accent} filled={icon === 'heart'} />
            </View>
            <Text style={[styles.helpText, { color: t.text }]}>{text}</Text>
          </View>
        ))}
        <Text style={[styles.small, { color: t.sub }]}>Out of hearts? Revive once for {REVIVE_COST} coins.</Text>
        <Btn label="Got it" onPress={() => setHelp(false)} />
      </Sheet>
    );
  }

  const link = (icon: IconName, label: string, doc: LegalId) => (
    <Pressy key={doc} onPress={() => onLegal(doc)} label={label} style={styles.linkRow}>
      <Icon name={icon} size={20} color={t.sub} />
      <Text style={[styles.linkText, { color: t.text }]}>{label}</Text>
      <Icon name="chevronRight" size={18} color={t.faint} />
    </Pressy>
  );

  return (
    <Sheet onBackdrop={onClose}>
      <View style={styles.head}>
        <Text style={[styles.title, { color: t.text }]}>Settings</Text>
        <Pressy onPress={onClose} label="Close" style={[styles.close, { backgroundColor: t.surfaceAlt }]}>
          <Icon name="close" size={18} color={t.text} />
        </Pressy>
      </View>
      <ScrollView style={styles.scroll} contentContainerStyle={styles.scrollBody} showsVerticalScrollIndicator={false}>
        <Toggle icon="sound" label="Sound effects" value={save.settings.sound} onChange={set('sound')} />
        <Toggle icon="vibrate" label="Vibration" value={save.settings.haptics} onChange={set('haptics')} />
        <Toggle icon="moon" label="Dark mode" value={save.settings.dark} onChange={set('dark')} />
        <Toggle icon="thin" label="Thin arrows" value={save.settings.thin} onChange={set('thin')} />
        <Toggle icon="grid" label="Grid lines" value={save.settings.grid} onChange={set('grid')} />
        <View style={[styles.divider, { backgroundColor: t.border }]} />
        <Pressy onPress={() => setHelp(true)} label="How to play" style={styles.linkRow}>
          <Icon name="help" size={20} color={t.sub} />
          <Text style={[styles.linkText, { color: t.text }]}>How to play</Text>
          <Icon name="chevronRight" size={18} color={t.faint} />
        </Pressy>
        {link('shield', 'Privacy Policy', 'privacy')}
        {link('doc', 'Terms of Use', 'terms')}
        {link('sparkle', 'Licenses & Credits', 'licenses')}
        {link('info', 'About', 'about')}
        <View style={[styles.divider, { backgroundColor: t.border }]} />
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
        <Text style={[styles.version, { color: t.faint }]}>
          {APP_INFO.name} {APP_INFO.version} · {APP_INFO.developer} · offline · no ads
        </Text>
      </ScrollView>
    </Sheet>
  );
}

const styles = StyleSheet.create({
  head: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  title: { fontSize: 24, fontWeight: '900' },
  close: { width: 36, height: 36, borderRadius: 18, alignItems: 'center', justifyContent: 'center' },
  scroll: { maxHeight: 520 },
  scrollBody: { paddingBottom: 4 },
  helpRow: { flexDirection: 'row', alignItems: 'center', gap: SPACE.md },
  helpIcon: { width: 34, height: 34, borderRadius: 17, alignItems: 'center', justifyContent: 'center' },
  helpText: { flex: 1, fontSize: 14, lineHeight: 20, fontWeight: '500' },
  small: { fontSize: 13, fontWeight: '600', textAlign: 'center' },
  divider: { height: 1, marginVertical: 6 },
  linkRow: { flexDirection: 'row', alignItems: 'center', gap: SPACE.md, paddingVertical: 11 },
  linkText: { flex: 1, fontSize: 16, fontWeight: '600' },
  reset: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, paddingVertical: 10 },
  resetText: { fontSize: 15, fontWeight: '700' },
  version: { textAlign: 'center', fontSize: 12, fontWeight: '600', marginTop: 4 },
});
