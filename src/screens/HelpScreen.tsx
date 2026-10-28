import { useEffect, useMemo, type ReactNode } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { Icon, type IconName } from '../components/Icon';
import { StaticBoard } from '../components/StaticBoard';
import { Card, Page, Screen, SectionTitle, TopBar } from '../components/ui';
import { RULES } from '../config/gameConfig';
import { COLORS, RADIUS, SPACE, TYPE } from '../config/theme';
import { unpackLevel } from '../game/geometry';
import type { LevelDef } from '../game/types';
import { completeOnboarding } from '../state/progress';
import { useStore } from '../state/store';

const demo = (w: number, h: number, a: string): LevelDef => unpackLevel({ w, h, a }, { id: 'help', number: 0, tier: 'tutorial' });

const TOOLS: readonly { icon: IconName; title: string; text: string }[] = [
  { icon: 'heart', title: 'Hearts', text: `You have ${RULES.lives} per attempt. Tapping a blocked arrow costs one (except in the tutorial).` },
  { icon: 'bulb', title: 'Hint', text: 'Highlights an arrow that can leave right now, with its path. Uses one hint.' },
  { icon: 'scan', title: 'Scan', text: `Shows an arrow's path and which arrows block it. ${RULES.scansPerLevel} per attempt.` },
  { icon: 'undo', title: 'Undo', text: 'Puts the last arrow back. Hearts and mistakes are not refunded.' },
  { icon: 'star', title: 'Stars', text: '3 stars for no mistakes and no hints. Your best result per level is kept.' },
];

export function HelpScreen() {
  const store = useStore();
  const boards = useMemo(
    () => ({
      tap: demo(4, 3, '01RR'),
      blocked: demo(4, 4, '01RR 30DDD'),
      order: demo(4, 5, '20R 01RR 33UU 24LL'),
    }),
    [],
  );

  useEffect(() => {
    store.update(completeOnboarding);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <Screen>
      <TopBar title="How to play" />
      <Page>
        <Step n={1} title="Tap an arrow" text="It slides off the board in the direction it points, keeping its shape.">
          <StaticBoard level={boards.tap} cell={30} colors={{ 0: COLORS.hint }} />
        </Step>
        <Step
          n={2}
          title="It can leave only when its exit path is clear"
          text="Everything its body would sweep through on the way out must be empty. Here the orange arrow blocks the red one."
        >
          <StaticBoard level={boards.blocked} cell={30} colors={{ 0: COLORS.error, 1: COLORS.blocker }} />
        </Step>
        <Step n={3} title="Remove blocking arrows first" text="Send the orange arrow out, and the red one is free to go.">
          <StaticBoard level={boards.blocked} cell={30} colors={{ 1: COLORS.hint }} />
        </Step>
        <Step n={4} title="Clear every arrow to finish" text="Work out the order. Every level can always be solved.">
          <StaticBoard level={boards.order} cell={26} />
        </Step>

        <SectionTitle>Tools</SectionTitle>
        <Card>
          {TOOLS.map((t, i) => (
            <View key={t.title} style={[styles.tool, i < TOOLS.length - 1 && styles.divider]}>
              <Icon name={t.icon} size={22} color={COLORS.ink} />
              <View style={styles.flex}>
                <Text style={styles.toolTitle}>{t.title}</Text>
                <Text style={styles.toolText}>{t.text}</Text>
              </View>
            </View>
          ))}
        </Card>
      </Page>
    </Screen>
  );
}

function Step({ n, title, text, children }: { n: number; title: string; text: string; children: ReactNode }) {
  return (
    <Card style={styles.step}>
      <View style={styles.stepHead}>
        <View style={styles.num}>
          <Text style={styles.numText}>{n}</Text>
        </View>
        <Text style={[TYPE.heading, styles.flex]}>{title}</Text>
      </View>
      <View style={styles.board}>{children}</View>
      <Text style={styles.text}>{text}</Text>
    </Card>
  );
}

const styles = StyleSheet.create({
  step: { padding: SPACE.lg, gap: SPACE.md },
  stepHead: { flexDirection: 'row', alignItems: 'center', gap: SPACE.md },
  num: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: COLORS.ink,
    alignItems: 'center',
    justifyContent: 'center',
  },
  numText: { color: COLORS.white, fontWeight: '800' },
  board: {
    alignItems: 'center',
    paddingVertical: SPACE.sm,
    backgroundColor: COLORS.background,
    borderRadius: RADIUS.md,
  },
  text: { ...TYPE.body, color: COLORS.inkSoft },
  flex: { flex: 1 },
  tool: { flexDirection: 'row', gap: SPACE.md, padding: SPACE.lg, alignItems: 'flex-start' },
  divider: { borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: COLORS.border },
  toolTitle: { fontSize: 15, fontWeight: '700', color: COLORS.ink },
  toolText: { fontSize: 13, color: COLORS.inkSoft, lineHeight: 19, marginTop: 2 },
});
