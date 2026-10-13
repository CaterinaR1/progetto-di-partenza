# Caso 1

## Sintomo

Nel repository c'è un hook che scrive una riga di log a ogni uso di uno strumento. Dopo mezza giornata di lavoro il file di log ha migliaia di righe: ci finisce dentro ogni lettura di ogni file, comprese quelle che non c'entrano con la review.

Quando serve davvero — capire quali strumenti ha usato il reviewer su una certa pull request — quel file non risponde alla domanda: è troppo lungo per essere letto, e non c'è modo di separare le azioni che contano dal rumore.

## Come riprodurlo

1. Configura `.claude/settings.json` con `BUGGY/settings.json`.
2. Apri `claude` sul repository e chiedi una review di un file qualsiasi.
3. Guarda `~/.claude-audit.log`: conta le righe, e conta quante riguardano qualcosa che ti interessa.
