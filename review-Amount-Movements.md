[
  {
    "file": "src/main/java/com/lipari/bank/movement/dto/TransferRequest.java",
    "riga": 18,
    "gravita": "HIGH",
    "descrizione": "Manca validazione sul numero di decimali di amount (@Digits): importi con scala > 2 (es. 10.999) superano la validazione del DTO, ma le colonne DB di Account.balance e Movement.amount sono dichiarate con precision=19, scale=2, quindi l'importo richiesto viene arrotondato/troncato a persistenza, producendo discordanza tra importo validato, saldi aggiornati e movimenti registrati.",
    "correzione_proposta": "Aggiungere @Digits(integer = 17, fraction = 2) sul campo amount e, nel service, normalizzare con req.getAmount().setScale(2, RoundingMode.HALF_UP) prima di eseguire i calcoli di saldo e di registrare i movimenti."
  },
  {
    "file": "src/main/java/com/lipari/bank/movement/dto/TransferRequest.java",
    "riga": 17,
    "gravita": "MEDIUM",
    "descrizione": "Il message dichiara \"amount must be > 0\" ma @DecimalMin(value = \"0.01\") con inclusive=true (default) impone amount >= 0.01: importi validi ma inferiori a 0.01 (es. 0.005) vengono rifiutati con un messaggio fuorviante rispetto al vincolo effettivo.",
    "correzione_proposta": "Uniformare message a \"amount must be >= 0.01\"; se l'intento ├¿ consentirequalsiasi importo strettamente maggiore di zero, usare @DecimalMin(value = \"0\", inclusive = false, message = \"amount must be > 0\")."
  },
  {
    "file": "src/main/java/com/lipari/bank/movement/dto/TransferRequest.java",
    "riga": 18,
    "gravita": "MEDIUM",
    "descrizione": "Assenza di upper bound sull'importo: nessun @DecimalMax limita amount alla capacit├á della colonna DB (precision 19, scale 2, massimo 99999999999999999.99), quindi valori maggiori vengono accettati dalla validazione e falliscono solo in fase di persistenza dei saldi/movimenti.",
    "correzione_proposta": "Aggiungere @DecimalMax(value = \"99999999999999999.99\", message = \"amount exceeds maximum allowed\") sul campo amount per allineare il vincolo del DTO al formato supportato dallo schema."
  },
  {
    "file": "src/main/java/com/lipari/bank/movement/dto/TransferRequest.java",
    "riga": 18,
    "gravita": "MEDIUM",
    "descrizione": "Il DTO non trasporta n├® valida la valuta dell'importo: Account ha il campo currency (default EUR), ma un trasferimento tra conti di valute diverse eseguirebbe subtract/add su importi di valute differenti senza conversione, violando la correttezza finanziaria dell'operazione monetaria.",
    "correzione_proposta": "Verificare nel service prima della modifica dei saldi che from.getCurrency().equals(to.getCurrency()) e lanciare errore altrimenti, oppure esplicitare la valuta nel DTO e validarla rispetto a quella dei conti coinvolti."
  },
  {
    "file": "src/main/java/com/lipari/bank/movement/dto/TransferRequest.java",
    "riga": 18,
    "gravita": "MEDIUM",
    "descrizione": "Lungo il percorso di trasferimento che consuma amount non ├¿ prevista alcuna applicazione delle soglie AML: importi >= 5.000 EUR non vengono registrati in audit trail e importi >= 10.000 EUR non comportano alcuna segnalazione, n├® ├¿ presente copertura per alert PEP su importi >= 1.000 EUR.",
    "correzione_proposta": "Nel service che consuma req.getAmount(), aggiungere la verifica delle soglie AML: registrazione audit per importi >= 5.000 EUR, invio di report/segmentation per importi >= 10.000 EUR e alert PEP per importi >= 1.000 EUR, tracciando correlationId, userId ed executedAt."
  }
]
