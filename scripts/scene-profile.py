#!/usr/bin/env python3
import json
import shlex
import sys
from pathlib import Path


def flatten(prefix, value, output):
    if isinstance(value, dict):
        for key, child in value.items():
            flatten(f"{prefix}_{key}" if prefix else key, child, output)
    elif not isinstance(value, list):
        output[prefix.upper()] = value


if len(sys.argv) != 2:
    raise SystemExit(f"Usage: {sys.argv[0]} <profile.json>")

profile = json.loads(Path(sys.argv[1]).read_text())
values = {}
flatten("", profile, values)
for key, value in values.items():
    print(f"{key}={shlex.quote(str(value))}")
