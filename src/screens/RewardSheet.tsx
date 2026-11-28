import { StyleSheet, Text, View } from 'react-native';
import Animated, { ZoomIn } from 'react-native-reanimated';
import { playSfx } from '../services/audio';
import { todayKey } from '../state/dates';
import { LOGIN_DAY7_HINTS, LOGIN_REWARDS, loginReward } from '../state/economy';
import { useStore } from '../state/store';
import { CoinIcon, Icon } from '../ui/Icon';
import { Btn, Sheet } from '../ui/kit';
import { RADIUS, useTheme } from '../ui/theme';

/** Once-a-day login reward with a 7-day streak. */
export function RewardSheet({ onClose }: { onClose: () => void }) {
  const t = useTheme();
  const { save, update } = useStore();
  const today = todayKey();
  const { available, day } = loginReward(save.login.last, save.login.day, today);

  const claim = () => {
    if (!available) return onClose();
    const coins = LOGIN_REWARDS[day - 1];
    const hints = day === LOGIN_REWARDS.length ? LOGIN_DAY7_HINTS : 0;
    playSfx('reward');
    update((s) => ({ ...s, coins: s.coins + coins, hints: s.hints + hints, login: { last: today, day } }));
    onClose();
  };

  return (
    <Sheet onBackdrop={onClose}>
      <Animated.View entering={ZoomIn.duration(300)} style={[styles.badge, { backgroundColor: t.goldSoft }]}>
        <Icon name="chest" size={40} color={t.gold} />
      </Animated.View>
      <Text style={[styles.title, { color: t.text }]}>Daily reward</Text>
      <Text style={[styles.sub, { color: t.sub }]}>Come back every day to keep your streak. Day 7 also gives {LOGIN_DAY7_HINTS} hints!</Text>
      <View style={styles.days}>
        {LOGIN_REWARDS.map((c, i) => {
          const d = i + 1;
          const past = d < day;
          const now = d === day && available;
          return (
            <View
              key={d}
              style={[
                styles.day,
                { backgroundColor: now ? t.goldSoft : t.surfaceAlt, borderColor: now ? t.gold : 'transparent' },
              ]}
            >
              <Text style={[styles.dayLabel, { color: t.sub }]}>Day {d}</Text>
              {past ? <Icon name="check" size={18} color={t.success} strokeWidth={3} /> : <CoinIcon size={18} />}
              <Text style={[styles.dayValue, { color: t.text }]}>{c}</Text>
            </View>
          );
        })}
      </View>
      <Btn label={available ? `Claim ${LOGIN_REWARDS[day - 1]} coins` : 'Come back tomorrow'} kind={available ? 'gold' : 'secondary'} onPress={claim} />
    </Sheet>
  );
}

const styles = StyleSheet.create({
  badge: { width: 76, height: 76, borderRadius: 38, alignSelf: 'center', alignItems: 'center', justifyContent: 'center' },
  title: { fontSize: 24, fontWeight: '900', textAlign: 'center' },
  sub: { fontSize: 14, fontWeight: '500', textAlign: 'center', lineHeight: 20 },
  days: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'center', gap: 6 },
  day: { width: 64, alignItems: 'center', gap: 2, borderRadius: RADIUS.sm, borderWidth: 2, paddingVertical: 8 },
  dayLabel: { fontSize: 11, fontWeight: '800' },
  dayValue: { fontSize: 14, fontWeight: '900' },
});
