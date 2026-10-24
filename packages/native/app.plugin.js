/**
 * Expo config plugin for @devdarshan/native. Runs during `expo prebuild` and:
 *  - caps WRITE_EXTERNAL_STORAGE at Android 9 (maxSdkVersion 28), or removes it;
 *  - signs release builds with the key given through DEVDARSHAN_KEYSTORE_* env vars;
 *  - enables R8 + resource shrinking (DEVDARSHAN_MINIFY, default "true");
 *  - optionally splits APKs per ABI (DEVDARSHAN_ABI_SPLITS=true);
 *  - keeps the APK small: native libraries and the JS bundle are stored compressed,
 *    and only English and Hindi resources are packaged from libraries;
 *  - gives Gradle enough memory for CI.
 *
 * Usage in app.config.ts:  ['@devdarshan/native', { legacyStorage: true }]
 */
const {
  createRunOncePlugin,
  withAndroidManifest,
  withAppBuildGradle,
  withGradleProperties,
} = require('expo/config-plugins');
const pkg = require('./package.json');

const MARKER = '// @devdarshan/native: release signing, minification and ABI splits';

const GRADLE_BLOCK = `
${MARKER}
def ddEnv = { String name ->
    def value = System.getenv(name)
    return (value == null || value.trim().isEmpty()) ? null : value.trim()
}
def ddKeystorePath = ddEnv("DEVDARSHAN_KEYSTORE_PATH")
def ddMinify = (ddEnv("DEVDARSHAN_MINIFY") ?: "true") == "true"
def ddAbiSplits = (ddEnv("DEVDARSHAN_ABI_SPLITS") ?: "false") == "true"

android {
    defaultConfig {
        // Libraries ship translations for ~80 languages; the app UI is English + Hindi.
        resourceConfigurations += ["en", "hi"]
    }
    if (ddKeystorePath != null) {
        signingConfigs {
            devdarshanRelease {
                storeFile file(ddKeystorePath)
                storePassword ddEnv("DEVDARSHAN_KEYSTORE_PASSWORD")
                keyAlias(ddEnv("DEVDARSHAN_KEY_ALIAS") ?: "devdarshan")
                keyPassword(ddEnv("DEVDARSHAN_KEY_PASSWORD") ?: ddEnv("DEVDARSHAN_KEYSTORE_PASSWORD"))
                storeType "PKCS12"
            }
        }
    }
    buildTypes {
        release {
            if (ddKeystorePath != null) {
                signingConfig signingConfigs.devdarshanRelease
            }
            minifyEnabled ddMinify
            shrinkResources ddMinify
        }
    }
    if (ddAbiSplits) {
        splits {
            abi {
                enable true
                reset()
                include "armeabi-v7a", "arm64-v8a", "x86_64"
                universalApk true
            }
        }
    }
}
`;

// Same block for a Kotlin DSL android/app/build.gradle.kts.
const KOTLIN_BLOCK = `
${MARKER}
val ddEnv: (String) -> String? = { name -> System.getenv(name)?.trim()?.takeIf { it.isNotEmpty() } }
val ddKeystorePath = ddEnv("DEVDARSHAN_KEYSTORE_PATH")
val ddMinify = (ddEnv("DEVDARSHAN_MINIFY") ?: "true") == "true"
val ddAbiSplits = (ddEnv("DEVDARSHAN_ABI_SPLITS") ?: "false") == "true"

android {
    defaultConfig {
        // Libraries ship translations for ~80 languages; the app UI is English + Hindi.
        resourceConfigurations += listOf("en", "hi")
    }
    if (ddKeystorePath != null) {
        signingConfigs {
            create("devdarshanRelease") {
                storeFile = file(ddKeystorePath)
                storePassword = ddEnv("DEVDARSHAN_KEYSTORE_PASSWORD")
                keyAlias = ddEnv("DEVDARSHAN_KEY_ALIAS") ?: "devdarshan"
                keyPassword = ddEnv("DEVDARSHAN_KEY_PASSWORD") ?: ddEnv("DEVDARSHAN_KEYSTORE_PASSWORD")
                storeType = "PKCS12"
            }
        }
    }
    buildTypes {
        getByName("release") {
            if (ddKeystorePath != null) {
                signingConfig = signingConfigs.getByName("devdarshanRelease")
            }
            isMinifyEnabled = ddMinify
            isShrinkResources = ddMinify
        }
    }
    if (ddAbiSplits) {
        splits {
            abi {
                isEnable = true
                reset()
                include("armeabi-v7a", "arm64-v8a", "x86_64")
                isUniversalApk = true
            }
        }
    }
}
`;

// Store .so files compressed in the APK (smaller download; Android extracts them on
// install). Only needed when the template doesn't already read expo.useLegacyPackaging.
const GROOVY_PACKAGING = `
android {
    packagingOptions {
        jniLibs {
            useLegacyPackaging true
        }
    }
}
`;
const KOTLIN_PACKAGING = `
android {
    packaging {
        jniLibs {
            useLegacyPackaging = true
        }
    }
}
`;

function withReleaseGradle(config) {
  return withAppBuildGradle(config, (cfg) => {
    if (cfg.modResults.contents.includes(MARKER)) return cfg;
    const groovy = cfg.modResults.language === 'groovy';
    let block = groovy ? GRADLE_BLOCK : KOTLIN_BLOCK;
    if (!cfg.modResults.contents.includes('expo.useLegacyPackaging')) {
      block += groovy ? GROOVY_PACKAGING : KOTLIN_PACKAGING;
    }
    cfg.modResults.contents = `${cfg.modResults.contents.trimEnd()}\n${block}`;
    return cfg;
  });
}

function withStoragePermission(config, legacyStorage) {
  return withAndroidManifest(config, (cfg) => {
    const manifest = cfg.modResults.manifest;
    const name = 'android.permission.WRITE_EXTERNAL_STORAGE';
    manifest['uses-permission'] = manifest['uses-permission'] || [];
    const permissions = manifest['uses-permission'];
    const existing = permissions.filter((p) => p.$ && p.$['android:name'] === name);
    if (legacyStorage) {
      if (existing.length === 0) {
        permissions.push({ $: { 'android:name': name, 'android:maxSdkVersion': '28' } });
      } else {
        existing.forEach((p) => {
          delete p.$['tools:node'];
          p.$['android:maxSdkVersion'] = '28';
        });
      }
    }
    return cfg;
  });
}

function setProperty(items, key, value) {
  const item = items.find((i) => i.type === 'property' && i.key === key);
  if (item) item.value = value;
  else items.push({ type: 'property', key, value });
}

function withGradleTuning(config) {
  return withGradleProperties(config, (cfg) => {
    setProperty(cfg.modResults, 'org.gradle.jvmargs', '-Xmx3072m -XX:MaxMetaspaceSize=1024m -XX:+HeapDumpOnOutOfMemoryError -Dfile.encoding=UTF-8');
    setProperty(cfg.modResults, 'kotlin.daemon.jvmargs', '-Xmx1536m');
    setProperty(cfg.modResults, 'org.gradle.parallel', 'true');
    // Lighter APKs: compressed native libraries and a compressed JS (Hermes) bundle.
    setProperty(cfg.modResults, 'expo.useLegacyPackaging', 'true');
    setProperty(cfg.modResults, 'android.enableBundleCompression', 'true');
    return cfg;
  });
}

function withDevDarshanNative(config, props = {}) {
  const legacyStorage = props.legacyStorage !== false;
  config = withStoragePermission(config, legacyStorage);
  config = withReleaseGradle(config);
  config = withGradleTuning(config);
  return config;
}

module.exports = createRunOncePlugin(withDevDarshanNative, pkg.name, pkg.version);
