#!/usr/bin/env python3
"""Surface Unity build errors as GitHub annotations and upload the full logs to a
PRIVATE draft release (only people with write access can see drafts)."""
import argparse
import glob
import json
import os
import re
import subprocess
import sys

COMPILE_RE = re.compile(r"^(Assets/[^\(\n]+)\((\d+),(\d+)\): error (CS\d+): (.*)$")
KEY_PATTERNS = [
    "Error building Player", "BuildFailedException", "[ZS-BUILD]", "[ZS-ERR]",
    "CommandInvokationFailure", "What went wrong", "executeMethod class",
    "Scripts have compiler errors", "No valid Unity Editor license",
    "License is not active", "Failed to activate", "Exception:", "error:",
    "FAILURE:", "Build failed", "Aborting batchmode", "Il2Cpp", "il2cpp",
]


def esc(s):
    return s.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def annotate(level, title, msg, file=None, line=None):
    props = [f"title={esc(title)[:200]}"]
    if file:
        props.append(f"file={file}")
    if line:
        props.append(f"line={line}")
    print(f"::{level} {','.join(props)}::{esc(msg[:6000])}")


def read(path):
    try:
        with open(path, "r", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def collect_logs(ws):
    home = os.path.expanduser("~")
    candidates = [os.path.join(ws, "Logs", "build.log")]
    candidates += glob.glob(os.path.join(ws, "Logs", "*.log"))
    candidates += glob.glob(os.path.join(home, ".config", "unity3d", "Unity", "*.log"))
    candidates += glob.glob(os.path.join(home, ".config", "unity3d", "Editor.log"))
    candidates += glob.glob(os.path.join(home, ".config", "unity3d", "Unity", "Licensing", "*.log"))
    seen, out = set(), []
    for c in candidates:
        if os.path.isfile(c) and c not in seen:
            seen.add(c)
            out.append(c)
    return out


def analyse(build_log):
    text = read(build_log)
    lines = text.splitlines()
    compile_errors = []
    for ln in lines:
        m = COMPILE_RE.match(ln.strip())
        if m and m.group(0) not in compile_errors:
            compile_errors.append(m.group(0))
    key = []
    for i, ln in enumerate(lines):
        if any(p in ln for p in KEY_PATTERNS):
            ctx = lines[i:i + 6] if ("What went wrong" in ln or "CommandInvokationFailure" in ln) else [ln]
            for c in ctx:
                c = c.rstrip()
                if c and c not in key:
                    key.append(c)
    return lines, compile_errors, key


def gh_api(*args, data=None):
    cmd = ["gh", "api", *args]
    r = subprocess.run(cmd, input=data, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"gh api failed: {' '.join(args)}: {r.stderr.strip()}", file=sys.stderr)
        return None
    try:
        return json.loads(r.stdout) if r.stdout.strip() else {}
    except json.JSONDecodeError:
        return {}


def upload_logs(files, status):
    repo = os.environ.get("GH_REPO")
    tag = os.environ.get("LOGS_TAG", "zombie-strike-logs")
    token = os.environ.get("GH_TOKEN")
    if not (repo and token):
        return
    releases = gh_api(f"repos/{repo}/releases?per_page=100") or []
    rel = next((r for r in releases if r.get("tag_name") == tag), None)
    if rel is None:
        rel = gh_api(f"repos/{repo}/releases", "-X", "POST", "-f", f"tag_name={tag}",
                     "-f", "name=Zombie Strike build logs (private draft)", "-F", "draft=true",
                     "-f", "body=Private draft holding the latest build logs. Safe to delete.")
    if not rel or "id" not in rel:
        print("Could not create the logs release", file=sys.stderr)
        return
    rid = rel["id"]
    existing = {a["name"]: a["id"] for a in rel.get("assets", [])}
    run = os.environ.get("GITHUB_RUN_NUMBER", "?")
    sha = os.environ.get("GITHUB_SHA", "")[:7]
    status_path = os.path.join(os.environ.get("RUNNER_TEMP", "/tmp"), "status.txt")
    with open(status_path, "w") as f:
        f.write(f"run={run}\nsha={sha}\nstatus={status}\n")
    uploads = [(status_path, "status.txt")]
    for p in files:
        name = os.path.basename(p).replace(" ", "_")
        uploads.append((p, name))
    for path, name in uploads:
        if name in existing:
            gh_api(f"repos/{repo}/releases/assets/{existing[name]}", "-X", "DELETE")
        url = f"https://uploads.github.com/repos/{repo}/releases/{rid}/assets?name={name}"
        r = subprocess.run(["curl", "-sS", "-X", "POST", "-H", f"Authorization: Bearer {token}",
                            "-H", "Content-Type: text/plain", "--data-binary", f"@{path}", url],
                           capture_output=True, text=True)
        print(f"uploaded {name}: rc={r.returncode}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", required=True)
    ap.add_argument("--status", default="unknown")
    a = ap.parse_args()

    logs = collect_logs(a.workspace)
    print("Logs found:", logs)
    build_log = os.path.join(a.workspace, "Logs", "build.log")

    if a.status != "success" and os.path.isfile(build_log):
        lines, compile_errors, key = analyse(build_log)
        for ce in compile_errors[:8]:
            m = COMPILE_RE.match(ce)
            annotate("error", f"{m.group(4)} {os.path.basename(m.group(1))}:{m.group(2)}", ce,
                     file=m.group(1), line=m.group(2))
        if key:
            annotate("error", "Unity build errors", "\n".join(key[:120]))
        annotate("warning", "End of the Unity log", "\n".join(lines[-90:]))
    elif a.status != "success":
        annotate("warning", "No Unity build log", "The build stopped before Unity ran (see earlier steps).")

    if a.status != "success":
        # surface the licensing client's own error (without the account email)
        lic = os.path.join(os.path.expanduser("~"), ".config", "unity3d", "Unity", "Unity.Licensing.Client.log")
        text = read(lic)
        msgs = re.findall(r'"message"\s*:\s*"([^"]+)"', text)
        errs = [ln for ln in text.splitlines() if " ERROR " in ln]
        if msgs or errs:
            email = re.compile(r"[A-Za-z0-9._%+#-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
            detail = "\n".join([email.sub("<email>", e)[-400:] for e in errs[-4:]] + ["Unity says: " + m for m in msgs[-3:]])
            hint = ""
            if any("Invalid Credential" in m for m in msgs):
                hint = "Unity rejected the email/password. Re-enter UNITY_EMAIL and UNITY_PASSWORD exactly (no extra characters).\n"
            annotate("error", "Unity licensing", hint + detail)

    try:
        upload_logs(logs, a.status)
    except Exception as e:  # never fail the job because of log upload
        print(f"log upload failed: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
