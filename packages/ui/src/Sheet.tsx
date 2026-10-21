import { useEffect, useRef, type ReactNode } from 'react';
import { Animated, Easing, Modal, Pressable, StyleSheet, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { AppText } from './AppText';
import { useTheme } from './theme';

export interface SheetProps {
  visible: boolean;
  onClose: () => void;
  title?: string;
  subtitle?: string;
  children: ReactNode;
  /** Prevent closing (e.g. while an operation runs). */
  dismissable?: boolean;
}

/** A lightweight bottom sheet built on Modal + the native-driven Animated API. */
export function Sheet({ visible, onClose, title, subtitle, children, dismissable = true }: SheetProps) {
  const { colors, spacing, radii } = useTheme();
  const insets = useSafeAreaInsets();
  const translate = useRef(new Animated.Value(320)).current;

  useEffect(() => {
    if (visible) {
      translate.setValue(320);
      Animated.timing(translate, {
        toValue: 0,
        duration: 240,
        easing: Easing.out(Easing.cubic),
        useNativeDriver: true,
      }).start();
    }
  }, [visible, translate]);

  const requestClose = () => {
    if (dismissable) onClose();
  };

  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={requestClose} statusBarTranslucent>
      <View style={styles.root}>
        <Pressable
          style={[StyleSheet.absoluteFill, { backgroundColor: colors.overlay }]}
          onPress={requestClose}
          accessibilityRole="button"
          accessibilityLabel="Close"
        />
        <Animated.View
          style={[
            styles.sheet,
            {
              backgroundColor: colors.surface,
              borderTopLeftRadius: radii.xl,
              borderTopRightRadius: radii.xl,
              paddingBottom: insets.bottom + spacing.lg,
              transform: [{ translateY: translate }],
            },
          ]}
        >
          <View style={[styles.handle, { backgroundColor: colors.borderStrong }]} />
          {title ? (
            <View style={{ paddingHorizontal: spacing.xl, paddingBottom: spacing.sm }}>
              <AppText variant="heading">{title}</AppText>
              {subtitle ? (
                <AppText variant="caption" color="textMuted" style={{ marginTop: 2 }}>
                  {subtitle}
                </AppText>
              ) : null}
            </View>
          ) : null}
          {children}
        </Animated.View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    justifyContent: 'flex-end',
  },
  sheet: {
    paddingTop: 8,
  },
  handle: {
    width: 36,
    height: 4,
    borderRadius: 2,
    alignSelf: 'center',
    marginBottom: 12,
  },
});
