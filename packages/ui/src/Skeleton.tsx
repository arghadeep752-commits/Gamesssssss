import { useEffect } from 'react';
import { Animated, Easing, type StyleProp, type ViewStyle } from 'react-native';
import { useTheme } from './theme';

/**
 * Every skeleton on screen shares ONE native-driven pulse, which runs only while
 * at least one skeleton is mounted (cheap on low-end phones).
 */
const pulse = new Animated.Value(0);
let mounted = 0;
let loop: Animated.CompositeAnimation | null = null;

function retain() {
  mounted += 1;
  if (mounted === 1) {
    loop = Animated.loop(
      Animated.sequence([
        Animated.timing(pulse, { toValue: 1, duration: 650, easing: Easing.inOut(Easing.quad), useNativeDriver: true }),
        Animated.timing(pulse, { toValue: 0, duration: 650, easing: Easing.inOut(Easing.quad), useNativeDriver: true }),
      ]),
    );
    loop.start();
  }
}

function release() {
  mounted = Math.max(0, mounted - 1);
  if (mounted === 0 && loop) {
    loop.stop();
    loop = null;
  }
}

const opacity = pulse.interpolate({ inputRange: [0, 1], outputRange: [0.55, 1] });

export function Skeleton({ style, radius }: { style?: StyleProp<ViewStyle>; radius?: number }) {
  const { colors, radii } = useTheme();
  useEffect(() => {
    retain();
    return release;
  }, []);
  return (
    <Animated.View
      accessibilityElementsHidden
      importantForAccessibility="no-hide-descendants"
      style={[{ backgroundColor: colors.skeletonBase, borderRadius: radius ?? radii.md, opacity }, style]}
    />
  );
}
