---
name: review-format
description: |-
  Skill per formato d'uscita condiviso dei reviewer del LipariBank.
  SI attiva quando viene richiesto di produrre findings di code review.
  Fissa un formato unico e non modificabile dei rilievi (fonte unica di verità).
allowed-tools: [Read, Grep, Glob]
---

# Review Format - Formato unico dei findings

Tutti i reviewer del LipariBank DEVONO produrre i rilievi seguendo ESATTAMENTE questo formato.

## Regole del formato
- Ogni rilievo deve avere ESATTAMENTE questi campi: file, riga, gravità, descrizione, correzione_proposta
- ile: percorso completo del file relativo alla root del repository (es. src/main/java/com/lipari/bank/movement/MovementService.java)
- iga: numero di riga (intero, >= 1). Se non determinabile con certezza, specifica riga più prossima/pertinente.
- gravità: uno tra CRITICAL, HIGH, MEDIUM, LOW (MAIUSCOLO)
- descrizione: spiegazione concisa (1-2 righe), obiettiva, tecnica, senza giudizi generici
- correzione_proposta: correzione concreta e applicabile PROPOSTA E NON APPLICATA
- Output: array JSON di findings (vuoto [] se nessun rilievo)
- Tono neutrale, tecnico. Nessun testo introduttivo/conclusivo. Non modificare mai codice.

## Esempio
`json
[
  {
    "file": "src/main/java/com/lipari/bank/movement/MovementService.java",
    "riga": 45,
    "gravità": "HIGH",
    "descrizione": "Manca controllo coerenza tra addebito e registrazione movimento",
    "correzione_proposta": "Verificare atomicità dell'operazione mantenendo transazione unica e stato consistente"
  }
]
`
