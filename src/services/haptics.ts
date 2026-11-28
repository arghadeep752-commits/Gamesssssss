import * as Haptics from 'expo-haptics';

/**
 * Optional vibration feedback. Disabled entirely when the player turns
 * vibration off; failures (for example devices without a vibrator) are ignored
 * so haptics can never block gameplay.
 */
let enabled = true;

export function configureHaptics(on: boolean): void {
  enabled = on;
}

export function hapticBlocked(): void {
  if (!enabled) return;
  Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium).catch(() => undefined);
}

export function hapticMove(): void {
  if (!enabled) return;
  Haptics.selectionAsync().catch(() => undefined);
}

export function hapticSuccess(): void {
  if (!enabled) return;
  Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => undefined);
}

export function hapticFailure(): void {
  if (!enabled) return;
  Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error).catch(() => undefined);
}
