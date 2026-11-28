#!/usr/bin/env node
/**
 * Applies the upstream Reanimated fix "skip sync updates for unmounted views"
 * (software-mansion/react-native-reanimated#10435, shipped in 4.7) to the 4.5.x
 * copy in node_modules, which the Android build compiles from source.
 *
 * Why: on React Native 0.86, every event dispatched during a draw pass makes
 * Reanimated re-apply all registered animated props through
 * MountingManager.updatePropsSynchronously. A view that was just unmounted is
 * still registered for a moment, so the call throws and Reanimated logs the
 * full ~150-frame stack trace on the UI thread. Leaving a board unmounts ~140
 * animated views at once; the resulting burst of stack traces froze the app
 * (ANR) in emulator runs. The fix checks MountingManager.getViewExists first
 * and logs any remaining failure in one line.
 *
 * Idempotent; runs from `postinstall` and again in CI right before prebuild.
 */
const fs = require('fs');
const path = require('path');

const MARK = 'arrowflow: skip unmounted views';
const TAG = '[patch-reanimated]';

let file;
try {
  const pkg = require.resolve('react-native-reanimated/package.json', { paths: [process.cwd()] });
  file = path.join(path.dirname(pkg), 'android/src/main/java/com/swmansion/reanimated/NativeProxy.kt');
} catch {
  console.log(`${TAG} react-native-reanimated is not installed; nothing to do`);
  process.exit(0);
}
if (!fs.existsSync(file)) {
  console.error(`${TAG} ${file} not found`);
  process.exit(1);
}

let src = fs.readFileSync(file, 'utf8');
if (src.includes(MARK)) {
  console.log(`${TAG} already applied`);
  process.exit(0);
}
if (src.includes('getViewExists')) {
  console.log(`${TAG} this Reanimated version already has the fix`);
  process.exit(0);
}

const anchorRe = /(\r?\n[ \t]*@DoNotStrip\r?\n[ \t]*fun synchronouslyUpdateUIProps\()/;
const callRe = /([ \t]*)updatePropsSynchronouslyMethod\.invoke\(mountingManager, viewTag, props\)(\r?\n)/;
const logRe = /Log\.w\("Reanimated", "synchronouslyUpdateUIProps failed for tag \$viewTag", e\)/;
const missing = [
  ['synchronouslyUpdateUIProps declaration', anchorRe],
  ['updatePropsSynchronously call', callRe],
  ['failure log', logRe],
].filter(([, re]) => !re.test(src));
if (missing.length) {
  console.error(`${TAG} NativeProxy.kt has changed (missing: ${missing.map(([n]) => n).join(', ')}); not patched`);
  process.exit(1);
}

src = src.replace(
  anchorRe,
  (whole) =>
    '\n' +
    `    // ${MARK} (upstream fix #10435)\n` +
    '    private val getViewExistsMethod: java.lang.reflect.Method? by lazy {\n' +
    '        runCatching {\n' +
    '            mountingManager.javaClass.methods\n' +
    '                .firstOrNull { it.name.startsWith("getViewExists") && it.parameterTypes.size == 1 }\n' +
    '                ?.apply { isAccessible = true }\n' +
    '        }.getOrNull()\n' +
    '    }\n' +
    '\n' +
    '    private var staleSkipLogged = false\n' +
    whole,
);
src = src.replace(callRe, (_m, indent, nl) =>
  [
    `${indent}if (getViewExistsMethod?.invoke(mountingManager, viewTag) != false) {`,
    `${indent}    updatePropsSynchronouslyMethod.invoke(mountingManager, viewTag, props)`,
    `${indent}} else if (!staleSkipLogged) {`,
    `${indent}    staleSkipLogged = true`,
    `${indent}    Log.i("Reanimated", "arrowflow: skipping sync updates for unmounted views")`,
    `${indent}}`,
  ].join(nl) + nl,
);
src = src.replace(logRe, () => 'Log.w("Reanimated", "synchronouslyUpdateUIProps failed for tag $viewTag: ${e.cause ?: e}")');

fs.writeFileSync(file, src);
console.log(`${TAG} applied to ${path.relative(process.cwd(), file)}`);
