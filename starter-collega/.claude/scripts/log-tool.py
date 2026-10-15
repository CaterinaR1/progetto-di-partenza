#!/usr/bin/env python3
# Gino: mi serviva per vedere cosa stava usando durante le review.
import datetime
import json
import pathlib
import sys

try:
    evento = json.load(sys.stdin)
except Exception:
    sys.exit(1)

riga = (f"{datetime.datetime.now().isoformat(timespec='seconds')} "
        f"[{evento.get('tool_name')}] {evento.get('tool_input')}\n")

with pathlib.Path.home().joinpath(".claude-audit.log").open("a", encoding="utf-8") as f:
    f.write(riga)
