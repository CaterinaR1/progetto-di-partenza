[
  {
    "file": "src/main/java/com/lipari/bank/movement/MovementService.java",
    "riga": 36,
    "gravità": "CRITICAL",
    "descrizione": "Il guard dei fondi confronta il saldo con BigDecimal.ZERO invece che con req.getAmount(): un bonifico oltre il saldo disponiente supera il controllo e porta il conto sorgente in negativo. Verificato sui dati reali: saldo conto 2 = 500.00 EUR e saldo conto 1 = 1000.00 EUR (finbank_mcp_get_account_balance); simulazione 600.00 da conto 2 a conto 1 con finbank_mcp_simulate_transfer_what_if -> would_succeed=false, reason \"fondi insufficienti: saldo sorgente 500.00 < importo 600.00 (MovementService.java:36-38)\", cioe' l'esito atteso dal backend e dal regolamento regolamento://transfer-policy (\"il saldo sorgente deve essere >= importo\"), mentre il codice modificato accetterebbe l'operazione con saldo finale -100.00.",
    "correzione_proposta": "Ripristinare if (from.getBalance().compareTo(req.getAmount()) < 0) { throw new IllegalArgumentException(\"insufficient funds\"); } confrontando quindi saldo sorgente e importo come richiesto da regolamento://transfer-policy."
  },
  {
    "file": "src/main/java/com/lipari/bank/movement/MovementService.java",
    "riga": 37,
    "gravità": "MEDIUM",
    "descrizione": "Il messaggio dell'eccezione e' diventato \"negative balance\", che non descrive la condizione realmente rilevante (saldo sorgente < importo, caso verificato: conto 2 = 500.00 EUR vs importo 600.00 via finbank_mcp_get_account_balance/finbank_mcp_simulate_transfer_if) e non corrisponde piu' all'esito \"fondi insufficienti\" documentato in regolamento://transfer-policy.",
    "correzione_proposta": "Ripristinare il messaggio \"insufficient funds\" (o un codice/errore equivalente stabile) in modo che il dominio esponga la condizione di fondi insufficienti coerentemente con regolamento://transfer-policy."
  },
  {
    "file": "src/main/java/com/lipari/bank/movement/MovementService.java",
    "riga": 40,
    "gravità": "MEDIUM",
    "descrizione": "Check-then-act sul saldo senza lock: la lettura del saldo, il controllo e la riscrittura (righe 36-43) non sono protetti da pessimistic lock/versione, quindi due transfer concorrenti sullo stesso conto possono superare entrambi il guard; difetto preesistente ma presente proprio sulla riga del controllo fondi toccata dalla modifica.",
    "correzione_proposta": "Caricare il conto sorgente con @Lock(LockModeType.PESSIMISTIC_WRITE) (o usare ottimistic locking con @Version) prima della verifica fondi, mantenendo l'intera operazione nella stessa transazione @Transactional."
  }
]
