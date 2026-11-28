import * as Reanimated from 'react-native-reanimated';
import * as Worklets from 'react-native-worklets';

type AnyFn = (...args: never[]) => void;
type Scheduler = { scheduleOnUI?: (fn: AnyFn, ...args: unknown[]) => void; runOnUI?: (fn: AnyFn) => (...args: unknown[]) => void };

const W = Worklets as unknown as Scheduler;
const R = Reanimated as unknown as Scheduler;

/**
 * Runs a worklet on the UI thread with the given arguments, in one go, so all
 * shared values it touches change in the same frame. Works with both the
 * current (`scheduleOnUI`) and the older (`runOnUI`) API names.
 */
export function onUI<A extends unknown[]>(fn: (...args: A) => void, ...args: A): void {
  const f = fn as unknown as AnyFn;
  if (typeof W.scheduleOnUI === 'function') W.scheduleOnUI(f, ...args);
  else if (typeof W.runOnUI === 'function') W.runOnUI(f)(...args);
  else if (typeof R.runOnUI === 'function') R.runOnUI(f)(...args);
}
