#!/usr/bin/env python3
"""Packs the resolved Dart/Flutter sources into kit/ so the code can be
statically analysed on a machine that cannot reach pub.dev.

The kit contains: the Dart SDK (without DevTools), the Flutter framework
packages, every resolved pub package (lib/ + pubspec.yaml + android/ build
files), the generated Android template and a report of resolved versions.
It is a development aid only; release builds run in hime-android.yml.
"""
import json
import os
import shutil
import subprocess
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(os.environ.get("GITHUB_WORKSPACE", ".")).resolve()
FLUTTER_ROOT = Path(os.environ["FLUTTER_ROOT"]).resolve()
KIT = ROOT / "kit"


def uri_to_path(uri: str, base: Path) -> Path:
    if uri.startswith("file://"):
        return Path(unquote(urlparse(uri).path)).resolve()
    return (base / uri).resolve()


def copy_tree(src: Path, dst: Path, ignore=None) -> None:
    if src.exists():
        shutil.copytree(src, dst, dirs_exist_ok=True, ignore=ignore, symlinks=False)


def main() -> None:
    if KIT.exists():
        shutil.rmtree(KIT)
    KIT.mkdir()

    cfg_path = ROOT / ".dart_tool" / "package_config.json"
    cfg = json.loads(cfg_path.read_text())
    base = cfg_path.parent
    mapping = []
    for pkg in cfg["packages"]:
        root = uri_to_path(pkg["rootUri"], base)
        name = pkg["name"]
        if root == ROOT:
            continue
        try:
            rel = root.relative_to(FLUTTER_ROOT)
            kit_rel = Path("flutter") / rel
        except ValueError:
            kit_rel = Path("pub") / root.name
        dst = KIT / kit_rel
        dst.mkdir(parents=True, exist_ok=True)
        copy_tree(root / "lib", dst / "lib")
        for f in ("pubspec.yaml", "analysis_options.yaml", "CHANGELOG.md"):
            if (root / f).exists():
                shutil.copy2(root / f, dst / f)
        android = root / "android"
        if android.exists():
            for f in android.rglob("*"):
                if f.is_file() and (f.suffix in {".gradle", ".kts", ".xml", ".properties", ".pro"}):
                    out = dst / "android" / f.relative_to(android)
                    out.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(f, out)
        mapping.append({
            "name": name,
            "path": str(kit_rel),
            "packageUri": pkg.get("packageUri", "lib/"),
            "languageVersion": pkg.get("languageVersion"),
        })
    (KIT / "package_map.json").write_text(json.dumps(mapping, indent=1))

    sdk = FLUTTER_ROOT / "bin" / "cache" / "dart-sdk"
    copy_tree(sdk, KIT / "dart-sdk", ignore=shutil.ignore_patterns("devtools"))
    copy_tree(Path("/tmp/gen/hime_template/android"), KIT / "android_template",
              ignore=shutil.ignore_patterns("*.jar", ".gradle"))
    copy_tree(Path("/tmp/gen/hime_template/lib"), KIT / "template_lib")
    for f in ("pubspec.lock", "flutter-version.txt", "flutter-version.json", "pub-get.log"):
        if (ROOT / f).exists():
            shutil.copy2(ROOT / f, KIT / f)

    lock = (ROOT / "pubspec.lock").read_text()
    report = [
        (ROOT / "flutter-version.txt").read_text(),
        "Direct dependencies:",
    ]
    current = None
    for line in lock.splitlines():
        if line.startswith("  ") and not line.startswith("    ") and line.strip().endswith(":"):
            current = line.strip()[:-1]
        if line.strip().startswith("dependency: \"direct") and current:
            report.append(f"  {current}")
        if line.strip().startswith("version:") and current:
            report[-1] = report[-1] if not report[-1].strip() == current else f"  {current} {line.split(':', 1)[1].strip()}"
    size = subprocess.run(["du", "-sh", str(KIT)], capture_output=True, text=True).stdout
    report.append("Kit size: " + size)
    (KIT / "report.txt").write_text("\n".join(report) + "\n")
    print("\n".join(report))


if __name__ == "__main__":
    main()
