import React from 'react';
import { StyleSheet, View } from 'react-native';

import { palette, space } from '../theme/tokens';
import { Button } from './Button';
import { Sheet } from './Sheet';
import { T } from './T';

type Props = {
  visible: boolean;
  title: string;
  message?: string;
  confirmLabel: string;
  cancelLabel?: string;
  danger?: boolean;
  busy?: boolean;
  onConfirm: () => void;
  onClose: () => void;
};

/** A question with one action and a way out. Used for deleting and discarding. */
export function ConfirmSheet({ visible, title, message, confirmLabel, cancelLabel = 'Cancel', danger, busy, onConfirm, onClose }: Props) {
  return (
    <Sheet visible={visible} onClose={onClose} title={title} scroll={false}>
      <View style={styles.body}>
        {message ? (
          <T variant="body" color={palette.ash}>
            {message}
          </T>
        ) : null}
        <View style={styles.actions}>
          <Button label={cancelLabel} kind="secondary" onPress={onClose} style={styles.flex} />
          <Button label={confirmLabel} kind={danger ? 'danger' : 'primary'} busy={busy} onPress={onConfirm} style={styles.flex} />
        </View>
      </View>
    </Sheet>
  );
}

const styles = StyleSheet.create({
  body: { paddingHorizontal: space.lg, paddingTop: space.xs, gap: space.lg },
  actions: { flexDirection: 'row', gap: space.sm },
  flex: { flex: 1 },
});
