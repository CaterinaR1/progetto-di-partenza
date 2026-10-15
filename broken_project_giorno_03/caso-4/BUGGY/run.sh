#!/bin/bash
# Gino: cosi' me lo ricordo.
#
# CORREZIONE (caso 4): il server era esposto su 0.0.0.0 (tutta la rete) senza
# autenticazione: chiunque raggiungesse la porta otteneva i saldi di un conto.
# In locale si lega a 127.0.0.1, raggiungibile solo dalla stessa macchina.
#
# Se serve davvero esporlo in rete NON basta cambiare l'host: su streamable-http
# l'autenticazione e' obbligatoria (FastMCP(auth=...) con Bearer token o OAuth/JWT).
# Il default sicuro per l'uso locale resta il trasporto stdio.

fastmcp run server.py \
  --transport streamable-http \
  --host 127.0.0.1 \
  --port 8765
