/**
 * Turbo Native Module spec (codegen input, see "codegenConfig" in package.json).
 *
 * Implemented in android/app/src/main/java/com/calcpro/app/CalcKitModule.kt:
 * small synchronous key-value storage on SharedPreferences, plus the system
 * keyboard haptic for key presses.
 */
import type { TurboModule } from 'react-native';
import { TurboModuleRegistry } from 'react-native';

export interface Spec extends TurboModule {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem(key: string): void;
  haptic(kind: string): void;
}

export default TurboModuleRegistry.get<Spec>('CalcKit');
