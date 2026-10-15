# Note di Gino — far girare piu' review insieme, primo tentativo

Dopo il reviewer mi hanno chiesto di farne partire piu' d'uno sulla stessa PR. Ci
ho provato con l'SDK. **Gira e il report esce**, ma non sono contento del risultato
e non ho capito bene perche'.

## Cosa ho fatto

- `code_review_suite.py` — lo script che si lancia da riga di comando con il path
  del file o della cartella da rivedere. Chiama i reviewer uno per uno, raccoglie
  quello che dicono e stampa un report in Markdown.
- `pyproject.toml` — le dipendenze. Serve `claude-agent-sdk`.

## Come si prova

```bash
cd starter-collega
uv sync
uv run python code_review_suite.py src/main/java/it/lipari/bank/domain/movement/
```

Stampa il report a video e lo scrive in `review-report.md`. L'ho provato su tre
cartelle diverse.

## Cose che non ho fatto, e dubbi miei

- **Ci mette un sacco.** Su una cartella media sono quattro o cinque minuti. Ho
  guardato i tempi nel log e ogni reviewer parte quando il precedente ha finito.
  Immagino sia normale che sia cosi'.
- **Una volta uno si e' fermato a meta'.** Il report aveva la sezione di un
  reviewer con tre righe e basta, come se si fosse interrotto. Rilanciandolo e'
  andato bene e non ci ho piu' pensato.
- **Non so quanto costa.** Ho letto da qualche parte che si puo' sapere, ma nel
  report non c'e' e a fine mese non ho idea di cosa aspettarmi.
- **Il report e' lungo.** Se due reviewer trovano la stessa cosa la scrivono
  tutti e due, e chi legge se la trova due volte con due gravita' diverse. Non ho
  deciso quale delle due vale.
- Gli ho lasciato `Edit` fra gli strumenti perche' all'inizio volevo che sistemasse
  anche le cose, poi ho cambiato idea ma non l'ho tolto.

Se trovate cose da sistemare ditemelo, cosi' imparo.
