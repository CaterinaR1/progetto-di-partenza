#!/bin/bash
# Avvio in streamable-http per l'Inspector col browser.
# FIX rispetto allo starter del collega: bind su 127.0.0.1, non 0.0.0.0 —
# un server che tocca dati bancari non va esposto su tutte le interfacce.
# L'avvio normale (Claude Code / OpenCode / Inspector CLI) e' la stdio:
#     python finbank-mcp/server.py

export LIPARIBANK_USERNAME="${LIPARIBANK_USERNAME:-svc_mcp}"
export LIPARIBANK_PASSWORD="${LIPARIBANK_PASSWORD:?imposta LIPARIBANK_PASSWORD (vedi README FASE 3)}"

fastmcp run server.py \
  --transport streamable-http \
  --host 127.0.0.1 \
  --port 8765
