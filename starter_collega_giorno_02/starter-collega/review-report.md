# Review di `src/main/java/com/lipari/bank/movement/`

- correlationId: `review-local`
- avvio: 15:07:23.775
- durata totale: 329.2s
- spesa: 279762/500000 token, costo 0.0000
- soglia del gate: HIGH
- codice recensito: non modificato
- esito del gate: **BLOCCATO (almeno un rilievo >= HIGH)**

## Copertura

| Lente | Stato | Partenza | Durata | Token | Findings |
|---|---|---|---|---|---|
| movement-domain-reviewer | OK | 15:07:23.775 | 329.2s | 82526 | 12 |
| compliance-amount-reviewer | OK | 15:07:23.801 | 108.6s | 79123 | 8 |
| api-contract-reviewer | OK | 15:07:23.818 | 54.8s | 51186 | 10 |
| performance-reviewer | OK | 15:07:23.841 | 159.0s | 66927 | 4 |

## Riepilogo per gravita' (per il cancello)

- CRITICAL: 2
- HIGH: 11
- MEDIUM: 17
- LOW: 4

## Findings riconciliati

### 1. [CRITICAL] src/main/java/com/lipari/bank/movement/MovementService.java:31

- lenti: movement-domain-reviewer
- descrizione: Check-then-act sul saldo senza lock pessimistico: due transfer concorrenti sullo stesso conto superano entrambi il controllo fondi sufficienti (riga 36) prima del salvataggio, producendo saldo negativo (overdraft non autorizzato).
- correzione proposta: Caricare from e to con lock pessimistico (es. @Lock(LockModeType.PESSIMISTIC_WRITE) su un metodo dedicato di AccountRepository) prima di leggere i saldi, oppure eseguire un UPDATE condizionale atomico del saldo con controllo importo>=amount nella stessa query.

### 2. [CRITICAL] src/main/java/com/lipari/bank/movement/MovementService.java:72

- lenti: compliance-amount-reviewer
- descrizione: 
- correzione proposta: 

### 3. [HIGH] src/main/java/com/lipari/bank/movement/MovementController.java:26

- lenti: api-contract-reviewer
- descrizione: L'endpoint espone direttamente l'entity JPA Movement (anche alla riga 34): il contratto pubblico e' accoppiato alla persistenza e ogni modifica del modello interno diventa un breaking change.
- correzione proposta: Introdurre un DTO di risposta (es. MovementResponse) con mapping esplicito e restituire quello, mantenendo l'entity confinata al layer di persistenza

### 4. [HIGH] src/main/java/com/lipari/bank/movement/MovementController.java:26

- lenti: api-contract-reviewer
- descrizione: Gli endpoint GET non applicano alcun controllo di autorizzazione/ownership su accountId: un chiamante puo' leggere movimenti ed estratti conto di conti non propri.
- correzione proposta: Verificare autenticazione e appartenenza del conto all'utente autenticato prima di restituire i dati, o delegare a un layer di security dedicato

### 5. [HIGH] src/main/java/com/lipari/bank/movement/MovementRepository.java:7

- lenti: performance-reviewer
- descrizione: findByAccountIdOrderByExecutedAtDesc restituisce una List non paginata: gli endpoint GET /api/movements e /statement/{accountId} materializzano l'intera cronologia dei movimenti di un conto in memoria e la serializzano integralmente, con costo crescente senza bound.
- correzione proposta: Accettare un parametro Pageable (o @Limit) e restituire Page/Movie ridotto, applicando paginazione con cap di righe per richiesta negli endpoint esposti.

### 6. [HIGH] src/main/java/com/lipari/bank/movement/MovementService.java:26

- lenti: movement-domain-reviewer
- descrizione: Operazione transfer non idempotente: nessuna idempotency key in TransferRequest né deduplica lato servizio, quindi un retry del client (es. timeout di rete) duplica addebito, accredito e i due movimenti.
- correzione proposta: Aggiungere un campo idempotencyKey @NotNull al TransferRequest e persistere la chiave in univocità (constraint unique); prima di elaborare, verificare se la chiave è già stata processata e restituire la risposta precedente, mantenendo l'inserimento della chiave nella stessa transazione del transfer.

### 7. [HIGH] src/main/java/com/lipari/bank/movement/MovementService.java:36

- lenti: movement-domain-reviewer
- descrizione: Il vincolo importo > 0 è dichiarato solo nel DTO (@DecimalMin); se transfer viene invocato da un altro servizio con importo negativo, il controllo fondi passa (compareTo di saldo positivo contro negativo è >= 0) e il verso del trasferimento si inverte: il mittente viene accreditato e il destinatario addebitato.
- correzione proposta: Validare all'inizio del metodo transfer: if (req.getAmount() == null || req.getAmount().signum() <= 0) throw new IllegalArgumentException("amount must be > 0");, replicando l'invariante di dominio anche nel servizio e non solo nella validazione API.

### 8. [HIGH] src/main/java/com/lipari/bank/movement/MovementService.java:51

- lenti: compliance-amount-reviewer
- descrizione: 
- correzione proposta: 

### 9. [HIGH] src/main/java/com/lipari/bank/movement/MovementService.java:76

- lenti: movement-domain-reviewer
- descrizione: N+1 nel ciclo di buildStatement: accountRepo.findById viene eseguito per ogni movimento e la variabile acc risultante non viene mai utilizzata, producendo una query al database per riga oltre che codice morto.
- correzione proposta: Eliminare del tutto il caricamento del conto dentro il ciclo (acc non è usato); se servisse in futuro, raggruppare gli accountId distinti e caricarli una sola volta con findAllById prima del loop.

### 10. [HIGH] src/main/java/com/lipari/bank/movement/MovementService.java:76

- lenti: compliance-amount-reviewer
- descrizione: 
- correzione proposta: 

### 11. [HIGH] src/main/java/com/lipari/bank/movement/MovementService.java:76

- lenti: performance-reviewer
- descrizione: N+1 query: accountRepo.findById viene eseguito una volta per ogni movimento della lista (una SELECT per riga), allungando la transazione read-only proporzionalmente alla cronologia del conto; il risultato acc risulta inoltre inutilizzato.
- correzione proposta: Rimuovere la lookup dell'account dal ciclo se non necessaria, altrimenti risolverla con una singola query (JOIN FETCH o IN sui accountId distinti) caricando l'account una sola volta fuori dal loop.

### 12. [HIGH] src/main/java/com/lipari/bank/movement/MovementService.java:78

- lenti: movement-domain-reviewer
- descrizione: Il totale dell'estratto conto somma tutti gli importi senza applicare il segno per tipo di movimento: TRANSFER_OUT, DEPOSIT e WITHDRAW sono trattati come incrementi, quindi il saldo calcolato è errato per qualsiasi conto con prelievi o trasferimenti in uscita.
- correzione proposta: Derivare il segno dal tipo: sottrarre l'importo per TRANSFER_OUT e WITHDRAW, sommarlo per TRANSFER_IN e DEPOSIT (es. monto = monto.add(signFor(m.getType()).multiply(m.getAmount()));), o preferibilmente calcolare il saldo via query aggregata SUM con CASE sulla colonna type.

### 13. [HIGH] src/main/java/com/lipari/bank/movement/MovementService.java:79

- lenti: compliance-amount-reviewer
- descrizione: 
- correzione proposta: 

### 14. [MEDIUM] src/main/java/com/lipari/bank/movement/Movement.java:19

- lenti: compliance-amount-reviewer
- descrizione: 
- correzione proposta: 

### 15. [MEDIUM] src/main/java/com/lipari/bank/movement/Movement.java:22

- lenti: compliance-amount-reviewer
- descrizione: 
- correzione proposta: 

### 16. [MEDIUM] src/main/java/com/lipari/bank/movement/MovementController.java:21

- lenti: api-contract-reviewer
- descrizione: Il POST /transfer non prevede chiave di idempotenza: invii duplicati della stessa richiesta generano trasferimenti multipli, rendendo il contratto non idempotente su un'operazione monetaria.
- correzione proposta: Accettare un header di idempotency key e deduplicare le richieste ripetute restituendo la stessa risposta

### 17. [MEDIUM] src/main/java/com/lipari/bank/movement/MovementController.java:26

- lenti: compliance-amount-reviewer
- descrizione: 
- correzione proposta: 

### 18. [MEDIUM] src/main/java/com/lipari/bank/movement/MovementController.java:26

- lenti: api-contract-reviewer
- descrizione: La lista movimenti non e' paginata: la risposta cresce illimitatamente e mancano parametri page/size nel contratto, con payload non deterministico.
- correzione proposta: Esporre parametri di paginazione (Pageable o page/size) e restituire una struttura paginata (Page<MovementResponse>) con metadati

### 19. [MEDIUM] src/main/java/com/lipari/bank/movement/MovementController.java:32

- lenti: compliance-amount-reviewer
- descrizione: 
- correzione proposta: 

### 20. [MEDIUM] src/main/java/com/lipari/bank/movement/MovementController.java:33

- lenti: movement-domain-reviewer
- descrizione: statement() invoca buildStatement(accountId) e ne scarta il risultato, poi re-interroga lo stesso repository con la stessa query alla riga 34: doppia lettura ridondante del medesimo dataset per ogni richiesta di estratto conto.
- correzione proposta: Eliminare la chiamata a buildStatement e restituire direttamente il risultato della query (o, se serve il totale, comporre una risposta che includa sia il totale calcolato sia la lista, effettuando un'unica lettura dei movimenti condivisa tra le due elaborazioni).

### 21. [MEDIUM] src/main/java/com/lipari/bank/movement/MovementController.java:33

- lenti: api-contract-reviewer
- descrizione: L'endpoint /statement ignora il valore ritornato da buildStatement e restituisce una lista non correlata: il contratto non espone il totale che il nome dell'endpoint suggerisce.
- correzione proposta: Definire un DTO di estratto conto che includa totale e movimenti, usare il valore calcolato e rimuovere la query ridondante

### 22. [MEDIUM] src/main/java/com/lipari/bank/movement/MovementController.java:34

- lenti: performance-reviewer
- descrizione: statement() carica due volte la stessa collection nella stessa richiesta: buildStatement legge tutti i movimenti (e i conti correlati) e la riga successiva riesegue la medesima query; il risultato di buildStatement viene scartato, pagando il costo senza alcun utilizzo.
- correzione proposta: Caricare la lista una sola volta e passarla a buildStatement (o restituire direttamente il risultato), eliminando la doppia scansione della tabella movement per richiesta.

### 23. [MEDIUM] src/main/java/com/lipari/bank/movement/MovementService.java:31

- lenti: movement-domain-reviewer
- descrizione: Il transfer non verifica né lo stato degli account (consentito anche a conti CLOSED/FROZEN) né la coincidenza della valuta tra conto origine e destinazione (campo currency esistente su Account), violando invarianze di dominio bancario.
- correzione proposta: Dopo il caricamento di from e to, verificare che entrambi abbiano status="ACTIVE" e che from.getCurrency().equals(to.getCurrency()); altrimenti throw IllegalArgumentException con messaggio esplicito, prima di qualsiasi modifica ai saldi.

### 24. [MEDIUM] src/main/java/com/lipari/bank/movement/MovementService.java:32

- lenti: api-contract-reviewer
- descrizione: Gli errori 'source/target account not found' sono lanciati come IllegalArgumentException e mappati a 400: semanticamente un conto inesistente e' una risorsa non trovata (404).
- correzione proposta: Introdurre eccezioni dedicate (es. ResourceNotFoundException) mappate a 404 e distinguerle dagli errori di validazione 400

### 25. [MEDIUM] src/main/java/com/lipari/bank/movement/MovementService.java:52

- lenti: movement-domain-reviewer
- descrizione: I movimenti non tracciano il correlationId della richiesta: i record TRANSFER_OUT/TRANSFER_IN creati qui (righe 45-61) non possono essere correlati ai log della stessa operazione, indebolendo la tracciabilità interna.
- correzione proposta: Aggiungere a Movement una colonna correlation_id valorizzata in transfer() leggendola da MDC (come già fa GlobalExceptionHandler) e propagarla anche ai due record creati, così da poter ricostruire l'intera operazione.

### 26. [MEDIUM] src/main/java/com/lipari/bank/movement/MovementService.java:73

- lenti: movement-domain-reviewer
- descrizione: findByAccountIdOrderByExecutedAtDesc carica l'intero storico dei movimenti del conto in memoria senza paginazione né streaming: per conti con molti movimenti si rischia esaurimento di heap e tempi di risposta non controllati.
- correzione proposta: Usare Page<Movement> findByAccountIdOrderByExecutedAtDesc(Long accountId, Pageable pageable) (o un endpoint cursored con lastExecutedAt/lastId) e far restituire buildStatement tramite aggregazione lato database invece di materializzare la lista completa.

### 27. [MEDIUM] src/main/java/com/lipari/bank/movement/MovementService.java:73

- lenti: performance-reviewer
- descrizione: Il totale dell'estratto conto viene calcolato in memoria iterando su tutte le entity Movement caricate, quando basterebbe un'unica query aggregata: attuale costo di I/O e memoria O(n) con caricamento di righe complete inutili.
- correzione proposta: Introdurre una query aggregata nel repository (es. @Query "SELECT COALESCE(SUM(m.amount),0) FROM Movement m WHERE m.accountId = :accountId") e calcolare il totale lato database senza materializzare le righe.

### 28. [MEDIUM] src/main/java/com/lipari/bank/movement/MovementService.java:79

- lenti: movement-domain-reviewer
- descrizione: La soglia AML (>= 10000 EUR) viene rilevata ma il corpo del blocco è vuoto: nessuna segnalazione, nessun log e nessun audit trail viene emesso, rendendo l'indicatore inoperante.
- correzione proposta: Emettere almeno una registrazione audit strutturata nel ramo di superamento soglia (log.warn con accountId, importo, movementId e correlationId) e introdurre un punto di estensione per la creazione della segnalazione AML, sostituendo il blocco vuoto.

### 29. [MEDIUM] src/main/java/com/lipari/bank/movement/dto/TransferRequest.java:17

- lenti: api-contract-reviewer
- descrizione: amount non vincola la scala decimale: sono accettati valori con piu' di 2 decimali che poi vengono arrotondati dalla colonna (scale=2), con disallineamento tra richiesta accettata e importo effettivo.
- correzione proposta: Aggiungere @Digits(integer=..., fraction=2) (o validazione equivalente) e uniformare il messaggio a un limite coerente col dominio

### 30. [MEDIUM] src/main/java/com/lipari/bank/movement/dto/TransferRequest.java:20

- lenti: api-contract-reviewer
- descrizione: Il campo description non ha vincoli di lunghezza: input arbitrariamente lunghi non sono validati a contratto e possono causare errori di persistenza (500) invece di un 400.
- correzione proposta: Aggiungere @Size(max = N) coerente con la colonna DB e relativo messaggio di errore

### 31. [LOW] src/main/java/com/lipari/bank/movement/Movement.java:19

- lenti: movement-domain-reviewer
- descrizione: Il campo type è una String libera senza vincolo JPA né enum di dominio: è possibile persistere valori non previsti (DEPOSIT, WITHDRAW, TRANSFER_OUT, TRANSFER_IN), con conseguente corruzione della logica di segno in buildStatement.
- correzione proposta: Introdurre un enum MovementType (DEPOSIT, WITHDRAW, TRANSFER_OUT, TRANSFER_IN), dichiarare il campo come @Enumerated(EnumType.STRING) con nullable=false, e mappare i valori nei punti di creazione dei movimenti.

### 32. [LOW] src/main/java/com/lipari/bank/movement/MovementController.java:21

- lenti: api-contract-reviewer
- descrizione: Il trasferimento restituisce sempre 200 OK tramite ResponseEntity.ok: per un'operazione di creazione non viene indicato alcun nuovo stato risorsa.
- correzione proposta: Valutare il ritorno di 201 Created con header Location verso la risorsa transfer, mantenendo 200 per operazioni non di creazione

### 33. [LOW] src/main/java/com/lipari/bank/movement/MovementService.java:27

- lenti: api-contract-reviewer
- descrizione: Il vincolo fromAccountId != toAccountId e' gestito solo a livello di logica e non e' documentato nel contratto del DTO, con messaggio d'errore generico non strutturato.
- correzione proposta: Documentare il vincolo cross-field nel DTO/OpenAPI e restituire un errore di validazione coerente con lo schema d'errore pubblico

### 34. [LOW] src/main/java/com/lipari/bank/movement/MovementService.java:51

- lenti: movement-domain-reviewer
- descrizione: Instant.now() viene calcolato separatamente per il movimento di uscita (riga 51) e di ingresso (riga 60): i due movimenti dello stesso transfer ricevono timestamp leggermente diversi, impedendo di appaiarli per identità temporale.
- correzione proposta: Calcolare una sola volta Instant now = Instant.now(); prima di costruire i due movimenti e assegnare lo stesso valore a out.setExecutedAt(now) e in.setExecutedAt(now), così da mantenere coerenza temporale del transfer.
