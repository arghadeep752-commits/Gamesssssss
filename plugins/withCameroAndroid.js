/**
 * Android build settings for Camero Plus, applied during `expo prebuild`:
 * - Gradle memory and target ABIs for CI builds
 * - JS bundled into debug builds too, so the debug APK runs without a dev server
 * - Optional release signing from environment variables (falls back to the debug key)
 * - Large heap for full-resolution photo rendering
 */
const { withGradleProperties, withAppBuildGradle, withAndroidManifest } = require('expo/config-plugins');

function setProperty(props, key, value) {
  const existing = props.find((p) => p.type === 'property' && p.key === key);
  if (existing) existing.value = value;
  else props.push({ type: 'property', key, value });
}

module.exports = function withCameroAndroid(config) {
  config = withGradleProperties(config, (cfg) => {
    setProperty(cfg.modResults, 'org.gradle.jvmargs', '-Xmx4608m -XX:MaxMetaspaceSize=1024m -Dfile.encoding=UTF-8');
    setProperty(cfg.modResults, 'reactNativeArchitectures', 'armeabi-v7a,arm64-v8a');
    setProperty(cfg.modResults, 'org.gradle.parallel', 'true');
    return cfg;
  });

  config = withAppBuildGradle(config, (cfg) => {
    let gradle = cfg.modResults.contents;
    if (!gradle.includes('debuggableVariants = []')) {
      gradle = gradle.replace(/react\s*\{/, (m) => `${m}\n    debuggableVariants = []`);
    }
    if (!gradle.includes('CAMERO_KEYSTORE')) {
      gradle = gradle.replace(
        /signingConfigs\s*\{/,
        (m) => `${m}
        release {
            if (System.getenv("CAMERO_KEYSTORE")) {
                storeFile file(System.getenv("CAMERO_KEYSTORE"))
                storePassword System.getenv("CAMERO_KEYSTORE_PASSWORD")
                keyAlias System.getenv("CAMERO_KEY_ALIAS")
                keyPassword System.getenv("CAMERO_KEY_PASSWORD")
            }
        }`
      );
      const target = 'signingConfig signingConfigs.debug';
      const buildTypes = gradle.indexOf('buildTypes');
      const release = buildTypes >= 0 ? gradle.indexOf('release', buildTypes) : -1;
      const sig = release >= 0 ? gradle.indexOf(target, release) : -1;
      if (sig >= 0) {
        gradle =
          gradle.slice(0, sig) +
          'signingConfig System.getenv("CAMERO_KEYSTORE") ? signingConfigs.release : signingConfigs.debug' +
          gradle.slice(sig + target.length);
      }
    }
    cfg.modResults.contents = gradle;
    return cfg;
  });

  config = withAndroidManifest(config, (cfg) => {
    const app = cfg.modResults.manifest.application && cfg.modResults.manifest.application[0];
    if (app) app.$['android:largeHeap'] = 'true';
    return cfg;
  });

  return config;
};
