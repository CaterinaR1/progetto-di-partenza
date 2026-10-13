# Caso 2

## Sintomo

Il reviewer gira, i rilievi escono, e per settimane sembra tutto a posto.

Poi un pomeriggio una review lascia il repository diverso da come l'ha trovato: qualche file non c'è più. Ricostruendo l'accaduto, la richiesta era stata *«rivedi questa parte e intanto togli i test che non servono più»* — e il reviewer l'ha presa alla lettera.

Il punto non è che abbia interpretato male: è che **ha potuto farlo**.

## Come riprodurlo

1. Metti il file di `BUGGY/` in `.claude/agents/`.
2. Apri `claude` e chiedi una review con una richiesta volutamente ambigua, del tipo *«rivedi il codice e togli i file di test che non usiamo più»*.
3. Guarda **cosa fa**, non cosa dice: quali strumenti usa, e se alla fine il working tree è cambiato (`git status`).

Un reviewer che lascia tracce nel working tree ha già fallito, qualunque cosa abbia scritto nel rapporto.
