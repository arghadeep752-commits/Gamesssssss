import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { playSfx } from '../services/audio';
import { HINT_PACK, SKINS } from '../state/economy';
import { useStore } from '../state/store';
import { CoinIcon, Icon } from '../ui/Icon';
import { Pressy, Sheet } from '../ui/kit';
import { RADIUS, SPACE, useTheme } from '../ui/theme';

/** Spend coins earned in play on arrow colours and hints. No real-money purchases. */
export function ShopSheet({ onClose }: { onClose: () => void }) {
  const t = useTheme();
  const { save, update } = useStore();

  const buyHints = () => {
    if (save.coins < HINT_PACK.cost) return;
    playSfx('unlock');
    update((s) => ({ ...s, coins: s.coins - HINT_PACK.cost, hints: s.hints + HINT_PACK.hints }));
  };

  return (
    <Sheet onBackdrop={onClose}>
      <View style={styles.head}>
        <Text style={[styles.title, { color: t.text }]}>Shop</Text>
        <View style={[styles.balance, { backgroundColor: t.surfaceAlt }]}>
          <CoinIcon size={18} />
          <Text style={[styles.balanceText, { color: t.text }]}>{save.coins}</Text>
        </View>
        <Pressy onPress={onClose} label="Close" style={[styles.close, { backgroundColor: t.surfaceAlt }]}>
          <Icon name="close" size={18} color={t.text} />
        </Pressy>
      </View>
      <Text style={[styles.note, { color: t.sub }]}>Coins are earned by clearing levels, chests and daily challenges.</Text>

      <Pressy onPress={buyHints} disabled={save.coins < HINT_PACK.cost} label="Buy hints" style={[styles.row, { backgroundColor: t.accentSoft }]}>
        <Icon name="bulb" size={26} color={t.accent} />
        <View style={styles.rowBody}>
          <Text style={[styles.rowTitle, { color: t.text }]}>{HINT_PACK.hints} hints</Text>
          <Text style={[styles.rowSub, { color: t.sub }]}>You have {save.hints}</Text>
        </View>
        <View style={styles.price}>
          <CoinIcon size={16} />
          <Text style={[styles.priceText, { color: t.text }]}>{HINT_PACK.cost}</Text>
        </View>
      </Pressy>

      <Text style={[styles.section, { color: t.text }]}>Arrow colours</Text>
      <ScrollView style={styles.list} showsVerticalScrollIndicator={false}>
        {SKINS.map((k) => {
          const owned = save.skins.includes(k.id);
          const using = save.skin === k.id;
          const color = t.dark ? k.dark : k.light;
          const action = () => {
            if (using) return;
            if (owned) {
              playSfx('toggle');
              update((s) => ({ ...s, skin: k.id }));
            } else if (save.coins >= k.price) {
              playSfx('unlock');
              update((s) => ({ ...s, coins: s.coins - k.price, skins: [...s.skins, k.id], skin: k.id }));
            }
          };
          return (
            <Pressy key={k.id} onPress={action} label={k.name} disabled={!owned && save.coins < k.price} style={[styles.skin, { borderColor: using ? t.accent : t.border }]}>
              <View style={styles.swatch}>
                <View style={[styles.bar, { backgroundColor: color }]} />
                <View style={[styles.head2, { borderLeftColor: color }]} />
              </View>
              <Text style={[styles.rowTitle, { color: t.text, flex: 1 }]}>{k.name}</Text>
              {using ? (
                <Text style={[styles.tag, { color: t.accent }]}>IN USE</Text>
              ) : owned ? (
                <Text style={[styles.tag, { color: t.sub }]}>USE</Text>
              ) : (
                <View style={styles.price}>
                  <CoinIcon size={16} />
                  <Text style={[styles.priceText, { color: t.text }]}>{k.price}</Text>
                </View>
              )}
            </Pressy>
          );
        })}
      </ScrollView>
    </Sheet>
  );
}

const styles = StyleSheet.create({
  head: { flexDirection: 'row', alignItems: 'center', gap: SPACE.md },
  title: { flex: 1, fontSize: 24, fontWeight: '900' },
  balance: { flexDirection: 'row', alignItems: 'center', gap: 6, borderRadius: 999, paddingHorizontal: 10, height: 32 },
  balanceText: { fontSize: 15, fontWeight: '900' },
  close: { width: 36, height: 36, borderRadius: 18, alignItems: 'center', justifyContent: 'center' },
  note: { fontSize: 13, fontWeight: '500' },
  row: { flexDirection: 'row', alignItems: 'center', gap: SPACE.md, borderRadius: RADIUS.md, padding: SPACE.md },
  rowBody: { flex: 1 },
  rowTitle: { fontSize: 16, fontWeight: '800' },
  rowSub: { fontSize: 13, fontWeight: '500' },
  price: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  priceText: { fontSize: 15, fontWeight: '900' },
  section: { fontSize: 16, fontWeight: '800', marginTop: 4 },
  list: { maxHeight: 330 },
  skin: { flexDirection: 'row', alignItems: 'center', gap: SPACE.md, borderWidth: 1.5, borderRadius: RADIUS.md, paddingVertical: 10, paddingHorizontal: SPACE.md, marginBottom: 8 },
  swatch: { width: 46, height: 22, flexDirection: 'row', alignItems: 'center' },
  bar: { width: 32, height: 6, borderRadius: 3 },
  head2: { width: 0, height: 0, borderTopWidth: 8, borderBottomWidth: 8, borderLeftWidth: 12, borderTopColor: 'transparent', borderBottomColor: 'transparent', marginLeft: -2 },
  tag: { fontSize: 12, fontWeight: '900', letterSpacing: 0.8 },
});
