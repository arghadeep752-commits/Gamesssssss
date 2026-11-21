#!/usr/bin/env python3
"""Copies a Unity log with the Unity account name taken out, so it can be put on the CI release.

    python3 ci/redact_log.py SRC DST        (the account comes from the UNITY_EMAIL environment variable)
"""
import os
import sys

src, dst = sys.argv[1], sys.argv[2]
email = os.environ.get("UNITY_EMAIL", "")
text = open(src, errors="replace").read()
secrets = {email, email.replace("@", "%40"), email.split("@")[0]} if email else set()
for s in sorted(secrets, key=len, reverse=True):
    if len(s) >= 4:
        text = text.replace(s, "<unity-account>")
open(dst, "w").write(text)
print("%s: %d lines" % (dst, text.count("\n")))
