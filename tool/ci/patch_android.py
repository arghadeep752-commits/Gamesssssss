#!/usr/bin/env python3
"""Turns the Android project produced by `flutter create --org app --project-name hime`
into Hime's Android app: manifest, native call glue, icons, splash, signing and
build settings. Run from the repository root after `flutter create`.
"""
import os
import re
import shutil
import sys

ROOT = os.getcwd()
ANDROID = os.path.join(ROOT, "android")
APP = os.path.join(ANDROID, "app")
OVERLAY = os.path.join(ROOT, "android_overlay")
PACKAGE_DIR = os.path.join(APP, "src", "main", "kotlin", "app", "hime")


def die(msg):
    print(f"patch_android: {msg}", file=sys.stderr)
    sys.exit(1)


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def patch_gradle():
    path = os.path.join(APP, "build.gradle.kts")
    if not os.path.exists(path):
        die("android/app/build.gradle.kts not found - run flutter create first")
    g = read(path)

    if 'namespace = "app.hime"' not in g:
        die("unexpected namespace; flutter create must use --org app --project-name hime")

    g = g.replace("minSdk = flutter.minSdkVersion", "minSdk = maxOf(flutter.minSdkVersion, 24)")
    # permission_handler_android needs to be compiled against API 37.
    g = g.replace("compileSdk = flutter.compileSdkVersion", "compileSdk = maxOf(flutter.compileSdkVersion, 37)")

    # Java 8+ APIs used by flutter_local_notifications.
    g = re.sub(
        r"compileOptions \{",
        "compileOptions {\n        isCoreLibraryDesugaringEnabled = true",
        g,
        count=1,
    )

    keystore = '''
val keystoreProperties = Properties()
val keystoreFile = rootProject.file("key.properties")
if (keystoreFile.exists()) {
    keystoreFile.inputStream().use { stream -> keystoreProperties.load(stream) }
}

'''
    g = "import java.util.Properties\n\n" + g
    g = g.replace("android {", keystore + "android {", 1)

    signing = '''
    signingConfigs {
        create("release") {
            if (keystoreFile.exists()) {
                storeFile = file(keystoreProperties.getProperty("storeFile"))
                storePassword = keystoreProperties.getProperty("storePassword")
                keyAlias = keystoreProperties.getProperty("keyAlias")
                keyPassword = keystoreProperties.getProperty("keyPassword")
            }
        }
    }
'''
    g = g.replace("    buildTypes {", signing + "\n    buildTypes {", 1)

    release_old = re.search(r"release \{.*?\n        \}", g, flags=re.S)
    if not release_old:
        die("release build type not found")
    release_new = '''release {
            signingConfig = if (keystoreFile.exists()) signingConfigs.getByName("release") else signingConfigs.getByName("debug")
            isMinifyEnabled = false
            isShrinkResources = false
        }'''
    g = g[: release_old.start()] + release_new + g[release_old.end():]

    g += '''
dependencies {
    coreLibraryDesugaring("com.android.tools:desugar_jdk_libs:2.1.5")
    implementation("androidx.core:core-ktx:1.15.0")
}
'''
    write(path, g)
    print("patched app/build.gradle.kts")


def copy_tree(src, dst):
    for base, _dirs, files in os.walk(src):
        rel = os.path.relpath(base, src)
        for name in files:
            target_dir = os.path.join(dst, rel)
            os.makedirs(target_dir, exist_ok=True)
            shutil.copy2(os.path.join(base, name), os.path.join(target_dir, name))


def patch_sources():
    shutil.copy2(os.path.join(OVERLAY, "AndroidManifest.xml"), os.path.join(APP, "src", "main", "AndroidManifest.xml"))
    os.makedirs(PACKAGE_DIR, exist_ok=True)
    for name in ("MainActivity.kt", "CallService.kt"):
        shutil.copy2(os.path.join(OVERLAY, "kotlin", name), os.path.join(PACKAGE_DIR, name))
    res = os.path.join(APP, "src", "main", "res")
    # The template's default launcher PNGs are replaced by the overlay.
    copy_tree(os.path.join(OVERLAY, "app", "src", "main", "res"), res)
    night = os.path.join(res, "values-night", "styles.xml")
    if os.path.exists(night):
        os.remove(night)
    print("copied manifest, Kotlin sources and resources")


def patch_properties():
    path = os.path.join(ANDROID, "gradle.properties")
    p = read(path)
    # Hosted CI runners have ~7 GB of RAM.
    p = re.sub(r"org\.gradle\.jvmargs=.*", "org.gradle.jvmargs=-Xmx4G -XX:MaxMetaspaceSize=1G -XX:+HeapDumpOnOutOfMemoryError", p)
    if "android.suppressUnsupportedCompileSdk" not in p:
        p += "\nandroid.suppressUnsupportedCompileSdk=37\n"
    if "org.gradle.caching" not in p:
        p += "\norg.gradle.caching=true\n"
    write(path, p)
    print("patched gradle.properties")


if __name__ == "__main__":
    patch_gradle()
    patch_sources()
    patch_properties()
    print("Android project ready")
