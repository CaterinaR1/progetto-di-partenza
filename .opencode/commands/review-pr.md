---
description: Code review del LipariBank su un percorso: lancia la suite multi-agent (4 lenti in parallelo) e riporta i findings nel formato unico.
agent: build
---

Esegui una code review del LipariBank sul target indicato.

Target: $ARGUMENTS
Se $ARGUMENTS e' vuoto, usa `src/main/java/com/lipari/bank/movement/`.

Passi:

1. Verifica che il target esista (`Test-Path`, o `test -e`). Se non esiste,
   fermati subito con un errore esplicito e non lanciare nulla.
2. Lancia la suite multi-agent (quattro lenti ortogonali in parallelo, gate HIGH):
   `python starter_collega_giorno_02/starter-collega/code_review_suite.py $ARGUMENTS --gate HIGH`
   Se hai usato il target di default, passa quel percorso.
3. Riporta l'esito in chiaro: codice di uscita della suite (0 nessun rilievo,
   1 rilievo >= soglia o copertura incompleta, 2 errore di config, 3 tetto
   superato), copertura dei reviewer (quanti `OK`/`FALLITO`/`ILLEGGIBILE`) e
   numero di findings riconciliati. I dettagli sono in `review-report.md` e
   `review-report.json`.
4. Presenta ogni finding nel formato della skill `review-format`: `file`, `riga`,
   `gravita` (CRITICAL/HIGH/MEDIUM/LOW), `descrizione`, `correzione_proposta`
   (proposta e **NON applicata**). Output come array JSON.
5. **Non modificare mai il codice revisionato.** Se un finding riguarda il dominio
   dei movimenti, segnala che il subagent `movement-domain-reviewer` puo' invocare
   i tool MCP `finbank_mcp_*` (`get_account_balance`, `simulate_transfer_what_if`)
   per verificare i valori contro i saldi reali.
