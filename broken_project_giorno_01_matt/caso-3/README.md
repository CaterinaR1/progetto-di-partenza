# Caso 3

## Sintomo

Il file c'è, è al posto giusto, e se lo chiami per nome risponde.

Ma quando chiedi una review normalmente — *«rivedi `MovementService.java`»* — la review te la fa la sessione principale, e il reviewer che hai scritto non entra mai in gioco. Te ne accorgi solo perché i rilievi non hanno la forma che gli avevi imposto.

Funziona, insomma, ma solo se ti ricordi di invocarlo tu. E un controllo che devi ricordarti di far partire, prima o poi non parte.

## Come riprodurlo

1. Metti il file di `BUGGY/` in `.claude/agents/`.
2. Apri `claude` e chiedi una review **senza nominarlo**.
3. Guarda se viene delegato a qualcuno o no.
4. Poi rifallo nominandolo esplicitamente, e confronta le due risposte.

La differenza fra le due prove è tutto quello che ti serve.
