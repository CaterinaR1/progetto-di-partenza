[
  {
    "file": "src/main/java/com/lipari/bank/movement/MovementService.java",
    "riga": 24,
    "gravit├á": "HIGH",
    "descrizione": "Il metodo transfer non prevede alcuna chiave di idempotenza: un retry della stessa richiesta addebita/accredita nuovamente i saldi e registra movimenti duplicati.",
    "correzione_proposta": "Aggiungere un idempotency key alla TransferRequest e persistere/verificare l'esito per chiave prima di applicare saldi e movimenti, restituendo l'esito gi├á registrato in caso di retry."
  },
  {
    "file": "src/main/java/com/lipari/bank/movement/MovementService.java",
    "riga": 38,
    "gravit├á": "HIGH",
    "descrizione": "Lettura-modifica-scrittura del saldo avviene senza locking (Account non ha @Version n├® lock pessimistico): trasferimenti concorrenti possono superare il controllo fondi e portare a saldi errati (lost update).",
    "correzione_proposta": "Bloccare i conti coinvolti con lock pessimistico (SELECT ... FOR UPDATE) o introdurre @Version con gestione dell'optimistic lock, rileggendo i saldi all'interno della transazione."
  },
  {
    "file": "src/main/java/com/lipari/bank/movement/MovementService.java",
    "riga": 29,
    "gravit├á": "MEDIUM",
    "descrizione": "Non viene verificato lo status dei conti: un conto non ACTIVE (es. bloccato/chiuso) pu├▓ comunque essere addebitato o accreditato.",
    "correzione_proposta": "Validare che sia 'from' sia 'to' abbiano status attivo prima di applicare saldi e movimenti, rifiutando l'operazione in caso contrario."
  },
  {
    "file": "src/main/java/com/lipari/bank/movement/MovementService.java",
    "riga": 38,
    "gravit├á": "MEDIUM",
    "descrizione": "Non viene verificata la coerenza di valuta tra i due conti: il trasferimento applica l'importo senza controllo di currency n├® conversione FX.",
    "correzione_proposta": "Confrontare from.getCurrency() e to.getCurrency() e rifiutare il trasferimento (o applicare cambio esplicito) se le valute differiscono."
  },
  {
    "file": "src/main/java/com/lipari/bank/movement/MovementService.java",
    "riga": 34,
    "gravit├á": "MEDIUM",
    "descrizione": "Il service non valida l'importo (positivit├á/non-null) dipendendo solo da @Valid sul controller; una chiamata interna con amount null genera NPE e con amount <= 0 altera i saldi.",
    "correzione_proposta": "Aggiungere validazione di dominio all'inizio del metodo: req != null, amount != null e amount.compareTo(BigDecimal.ZERO) > 0, lanciando un'eccezione di dominio dedicata."
  },
  {
    "file": "src/main/java/com/lipari/bank/movement/MovementService.java",
    "riga": 35,
    "gravit├á": "MEDIUM",
    "descrizione": "La condizione di fondi insufficienti viene segnalata con IllegalArgumentException, mappata dal GlobalExceptionHandler a HTTP 400, confondendo un errore di dominio con un errore di input.",
    "correzione_proposta": "Introdurre un'eccezione di dominio (es. InsufficientFundsException) e mapparla a HTTP 409/422 nel GlobalExceptionHandler."
  },
  {
    "file": "src/main/java/com/lipari/bank/movement/MovementService.java",
    "riga": 61,
    "gravit├á": "MEDIUM",
    "descrizione": "TransferResponse.transferId espone solo l'id del movimento TRANSFER_OUT; i movimenti out/in non condividono un riferimento comune e non sono correlabili come singola transazione.",
    "correzione_proposta": "Persistere un identificativo di trasferimento condiviso (transferId/correlationId) su entrambi i movimenti e valorizzarlo nella risposta."
  },
  {
    "file": "src/main/java/com/lipari/bank/movement/MovementService.java",
    "riga": 49,
    "gravit├á": "MEDIUM",
    "descrizione": "Il correlationId presente nel MDC (CorrelationIdFilter) non viene propagato n├® registrato sui movimenti, rendendo difficoltosa la tracciabilit├á end-to-end del trasferimento.",
    "correzione_proposta": "Aggiungere il campo correlationId al Movement e valorizzarlo leggendo MDC.get(\"correlationId\") al momento della registrazione dei movimenti."
  },
  {
    "file": "src/main/java/com/lipari/bank/movement/MovementService.java",
    "riga": 49,
    "gravit├á": "LOW",
    "descrizione": "executedAt viene calcolato con due chiamate distinte a Instant.now() (righe 49 e 58), quindi i movimenti OUT e IN della stessa transazione hanno timestamp potenzialmente diversi.",
    "correzione_proposta": "Calcolare un unico Instant executedAt all'inizio della registrazione e assegnarlo a entrambi i movimenti."
  }
]
