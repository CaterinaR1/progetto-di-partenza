# Review di `src/main/java/com/lipari/bank/movement/`

- correlationId: `review-local`
- avvio: 15:13:50.765
- durata totale: 192.0s
- spesa: 347562/500000 token, costo 0.0000
- soglia del gate: HIGH
- codice recensito: non modificato
- esito del gate: **BLOCCATO (almeno un rilievo >= HIGH)**

## Copertura

| Lente | Stato | Partenza | Durata | Token | Findings |
|---|---|---|---|---|---|
| movement-domain-reviewer | OK | 15:13:50.765 | 183.5s | 143001 | 13 |
| compliance-amount-reviewer | OK | 15:13:50.829 | 161.0s | 48386 | 9 |
| api-contract-reviewer | OK | 15:13:50.857 | 191.9s | 95762 | 8 |
| performance-reviewer | OK | 15:13:50.883 | 59.2s | 60413 | 3 |

## Riepilogo per gravita' (per il cancello)

- CRITICAL: 4
- HIGH: 8
- MEDIUM: 14
- LOW: 5

## Findings riconciliati

### 1. [CRITICAL] src/main/java/com/lipari/bank/movement/MovementController.java:20

- lenti: api-contract-reviewer
- descrizione: L'endpoint POST /api/movements/transfer non verifica che l'utente autenticato possieda il conto sorgente: qualsiasi chiamante con un JWT valido può trasferire denaro da qualsiasi accountId (IDOR/BOLA).
- correzione proposta: Confrontare il customerId del conto sorgente (from.customerId) con l'identità del principal JWT e restituire 403/404 se non corrisponde, prima di eseguire l'addebito.

### 2. [CRITICAL] src/main/java/com/lipari/bank/movement/MovementService.java:36

- lenti: movement-domain-reviewer
- descrizione: Il controllo fondi (linee 31-43) e' un read-modify-write senza lock pessimistico ne' @Version: due transfer concorrenti dallo stesso conto leggono lo stesso saldo, superano entrambi il check e al commit 'last write wins', creando denaro (addebito una volta, accredito due). Verificato sui dati reali: conto 1 = 1000.00 e conto 2 = 500.00 via finbank_mcp_get_account_balance; due bonifici concorrenti da 600.00 passerebbero entrambi il controllo.
- correzione proposta: Rendere atomico controllo+addebito: acquisire i conti con lock pessimistico (es. @Lock(PESSIMISTIC_WRITE) su una findByIdForUpdate) o introdurre un campo @Version su Account e aggiornare il saldo con UPDATE condizionale (decremento solo se balance >= importo), gestendo l'OptimisticLockException con retry.

### 3. [CRITICAL] src/main/java/com/lipari/bank/movement/MovementService.java:76  **[CONFLITTO]**

- lenti: movement-domain-reviewer, performance-reviewer
- gravita' per lente: movement-domain-reviewer=HIGH, performance-reviewer=CRITICAL (gate = CRITICAL)
- descrizione: N+1 in buildStatement: accountRepo.findById(m.getAccountId()) viene eseguito dentro il ciclo per ogni movimento, e l'oggetto 'acc' caricato non viene mai utilizzato (query morta). Su un conto con molti movimenti produce una query per riga. | N+1 query: accountRepo.findById viene eseguito per ogni movimento del conto dentro il ciclo di buildStatement, generando N query aggiuntive proporzionali al numero di movimenti; il valore restituito non viene nemmeno usato.
- correzione proposta: Rimuovere la query inutilizzata dall'interno del ciclo; se serve il conto, caricarlo una sola volta fuori dal ciclo oppure non caricarlo affatto. | Rimuovere la query per movimento (l'Account non serve al calcolo) oppure, se realmente necessario, caricare i conti in un'unica query con findAllById degli id distinti o con @EntityGraph/JOIN FETCH, evitando l'accesso al repository dentro il ciclo.

### 4. [CRITICAL] src/main/java/com/lipari/bank/movement/MovementService.java:79

- lenti: compliance-amount-reviewer
- descrizione: Il controllo di soglia AML (>= 10000 EUR) e' un blocco if vuoto: nessuna segnalazione, audit o escalation viene prodotta quando un movimento supera la soglia, violando l'obbligo di reporting antiriciclaggio.
- correzione proposta: Emettere una segnalazione AML (es. amlReportService.report(m)) e un record di audit permanente quando m.getAmount() >= 10000, registrando anche i movimenti >= 5000 in audit log con importo, conti coinvolti e timestamp.

### 5. [HIGH] src/main/java/com/lipari/bank/movement/Movement.java:29

- lenti: compliance-amount-reviewer
- descrizione: L'entity Movement non contiene i campi di audit trail monetario obbligatori (correlationId, userId, ipAddress): ogni operazione su importi non e' tracciabile in modo completo secondo le regole AML.
- correzione proposta: Aggiungere colonne correlationId, userId e ipAddress all'entity (e popolarle nel service a ogni creazione di movimento), mantenendo executedAt gia' presente.

### 6. [HIGH] src/main/java/com/lipari/bank/movement/MovementController.java:26

- lenti: api-contract-reviewer
- descrizione: GET /api/movements e GET /statement/{accountId} (riga 32) restituiscono i movimenti di qualsiasi accountId senza alcuna verifica di proprietà: lettura non autorizzata dei dati finanziari di conti altrui.
- correzione proposta: Validare che il conto richiesto appartenga al customer dell'utente autenticato e restituire 403/404 in caso contrario, centralizzando il controllo in un metodo di servizio.

### 7. [HIGH] src/main/java/com/lipari/bank/movement/MovementController.java:26

- lenti: api-contract-reviewer
- descrizione: L'entity JPA Movement è esposta direttamente come tipo di risposta dei GET (anche riga 32): il contratto pubblico dipende dallo schema della tabella e ogni modifica all'entità diventa un breaking change per i client.
- correzione proposta: Introdurre un DTO pubblico MovementResponse (campi id, accountId, type, amount, counterpartyAccountId, description, executedAt) e mappare esplicitamente l'entity verso il DTO nei metodi del controller.

### 8. [HIGH] src/main/java/com/lipari/bank/movement/MovementRepository.java:7

- lenti: performance-reviewer
- descrizione: findByAccountIdOrderByExecutedAtDesc restituisce una List senza bound: per conti con molti movimenti carica l'intera collezione in memoria senza paginazione, con costo DB, memoria e rete non limitato.
- correzione proposta: Esporre una variante paginata Page<Movement> findByAccountIdOrderByExecutedAtDesc(Long accountId, Pageable pageable) e applicarla negli endpoint, mantenendo la List solo dove il volume e' garantito limitato.

### 9. [HIGH] src/main/java/com/lipari/bank/movement/MovementService.java:26

- lenti: movement-domain-reviewer
- descrizione: transfer() non ha alcun meccanismo di idempotenza: un retry della POST /api/movements/transfer (timeout di rete, doppio invio) esegue un secondo addebito/accredito con side effect reale, senza chiave di deduplicazione.
- correzione proposta: Accettare un idempotency key/correlationId nel TransferRequest, persisterlo (es. tabella transfer con vincolo unique) e rifiutare/restituire l'esito gia' registrato se la chiave e' stata gia' processata.

### 10. [HIGH] src/main/java/com/lipari/bank/movement/MovementService.java:26

- lenti: compliance-amount-reviewer
- descrizione: Il transfer non esegue alcun controllo AML a monte: importi >= 10000 non vengono segnalati, >= 5000 non registrati in audit, e non risultano PEP/watchlist screening, violando le soglie operative obbligatorie.
- correzione proposta: Prima di registrare i movimenti, verificare l'importo contro le soglie AML (>= 5000 audit, >= 10000 segnalazione) e integrare PEP screening e watchlist sul controparte quando applicabile, con esito persistito.

### 11. [HIGH] src/main/java/com/lipari/bank/movement/MovementService.java:40

- lenti: compliance-amount-reviewer
- descrizione: L'aggiornamento dei saldi e' un read-modify-write senza lock ottimistico/pessimistico ne' controllo di concorrenza: due transfer concorrenti sullo stesso conto possono perdere aggiornamenti, causando underflow o violazione della conservazione del denaro.
- correzione proposta: Usare findById con pessimistic locking (es. @Lock(PESSIMISTIC_WRITE) o findWithLock) e rieffettuare il controllo fondi sufficienti dopo l'acquisizione del lock, all'interno della stessa transazione.

### 12. [HIGH] src/main/java/com/lipari/bank/movement/MovementService.java:78

- lenti: movement-domain-reviewer, compliance-amount-reviewer
- descrizione: buildStatement somma gli importi senza segno: TRANSFER_OUT/WITHDRAW e TRANSFER_IN/DEPOSIT vengono addizionati tutti come positivi, quindi il totale non rappresenta il saldo netto (es. per un transfer da 100 il conto sorgente contribuisce +100 invece di -100). | buildStatement somma tutti gli importi in modo non firmato: TRANSFER_OUT e WITHDRAW accrescono il totale quanto TRANSFER_IN e DEPOSIT, producendo un saldo estratto conto finanziariamente errato.
- correzione proposta: Applicare il segno in base al type del movimento (sottrarre per TRANSFER_OUT/WITHDRAW, sommare per TRANSFER_IN/DEPOSIT) oppure demandare la somma a una query di aggregazione con CASE sul tipo. | Derivare il segno dal tipo di movimento (DEPOSIT/TRANSFER_IN positivi, WITHDRAW/TRANSFER_OUT negativi, es. con un metodo Movement.sign() o mappatura enum) prima di sommare al totale.

### 13. [MEDIUM] src/main/java/com/lipari/bank/movement/Movement.java:11

- lenti: movement-domain-reviewer
- descrizione: L'entita' Movement non memorizza alcun correlationId e i due movimenti della stessa operazione non sono legati da un identificatore condiviso (solo il generico counterpartyAccountId). Il regolamento://aml-policy (letto via MCP) richiede correlationId, userId, ipAddress ed executedAt su ogni operazione monetaria; qui c'e' solo executedAt.
- correzione proposta: Aggiungere un campo correlationId (e gli altri campi di audit richiesti) all'entita' Movement e valorizzarlo in transfer() in modo che le due gambe condividano lo stesso identificativo.

### 14. [MEDIUM] src/main/java/com/lipari/bank/movement/MovementController.java:19

- lenti: api-contract-reviewer
- descrizione: POST /api/movements/transfer non è idempotente e non prevede alcuna chiave di idempotency: un retry del client (timeout o rete) duplica l'operazione di denaro.
- correzione proposta: Accettare un header Idempotency-Key, memorizzare la chiave con la risposta associata e rispondere con lo stesso TransferResponse sulle richieste ripetute.

### 15. [MEDIUM] src/main/java/com/lipari/bank/movement/MovementController.java:27

- lenti: movement-domain-reviewer
- descrizione: listByAccount (e statement alla riga 34) restituisce l'intera lista dei movimenti senza paginazione: il repository carica tutto in memoria, con costo crescente e non limitato sul numero di righe.
- correzione proposta: Introdurre paginazione (Pageable/Page) sull'accesso ai movimenti e applicare un limite massimo alla risposta.

### 16. [MEDIUM] src/main/java/com/lipari/bank/movement/MovementController.java:27

- lenti: api-contract-reviewer
- descrizione: Le liste di movimenti sono restituite senza paginazione né limite di elementi: per conti con molti movimenti la risposta cresce senza bound, con impatto su tempo di risposta e payload.
- correzione proposta: Accettare parametri page/size (o Pageable) con un limite massimo di default e restituire una pagina di DTO invece di List<Movement>.

### 17. [MEDIUM] src/main/java/com/lipari/bank/movement/MovementController.java:33

- lenti: api-contract-reviewer
- descrizione: Il risultato di buildStatement (totale dell'estratto conto) viene calcolato e scartato: l'endpoint /statement/{accountId} non restituisce il dato che produce, con lavoro inutile ad ogni chiamata.
- correzione proposta: Restituire un DTO StatementResponse contenente totale e movimenti (oppure rimuovere la chiamata a buildStatement se il totale non è parte del contratto).

### 18. [MEDIUM] src/main/java/com/lipari/bank/movement/MovementController.java:34

- lenti: performance-reviewer
- descrizione: L'endpoint statement esegue due caricamenti completi della stessa collezione: buildStatement esegue gia' findByAccountIdOrderByExecutedAtDesc e la riga 34 ripete la stessa query, raddoppiando lettura e materializzazione dei movimenti (per giunta il risultato di buildStatement e' scartato).
- correzione proposta: Eseguire il caricamento una sola volta (usare il risultato ottenuto in buildStatement o unificare il calcolo e la restituzione in un unico metodo) evitando la seconda query identica.

### 19. [MEDIUM] src/main/java/com/lipari/bank/movement/MovementService.java:26

- lenti: compliance-amount-reviewer
- descrizione: Nessun rilevamento di pattern sospetti nel dominio movimenti: transfer ripetuti appena sotto la soglia 10000 (smurfing/structuring) o giri circolari fra piu' conti non vengono analizzati o segnalati.
- correzione proposta: Introducere un controllo a valle del transfer che aggrega gli importi del conto su finestra temporale (es. rolling 24h/7g) e segnala quando piu' operazioni cumulate superano la soglia AML o quando esiste un ciclo di controparti sospetto.

### 20. [MEDIUM] src/main/java/com/lipari/bank/movement/MovementService.java:31

- lenti: movement-domain-reviewer
- descrizione: transfer() non verifica lo stato dei conti: Account.status (es. ACTIVE vs BLOCKED/CLOSED) esiste ma viene ignorato, quindi e' possibile trasferire fondi da/verso un conto non operativo.
- correzione proposta: Validare che entrambi i conti abbiano status ACTIVE prima di procedere, rifiutando con errore di dominio in caso contrario.

### 21. [MEDIUM] src/main/java/com/lipari/bank/movement/MovementService.java:32

- lenti: api-contract-reviewer
- descrizione: Tutti gli errori di dominio (conto sorgente/destinazione inesistente riga 32-34, stesso conto riga 27, fondi insufficienti riga 37) sono lanciati come IllegalArgumentException e quindi mappati uniformemente a 400: il cliente non può distinguere un 404 da un conflitto di fondi.
- correzione proposta: Usare eccezioni dedicate con mapping distinti nel GlobalExceptionHandler: 404 per conto inesistente, 409 o 422 per fondi insufficienti, 400 per stesso conto.

### 22. [MEDIUM] src/main/java/com/lipari/bank/movement/MovementService.java:36

- lenti: movement-domain-reviewer
- descrizione: L'invarianza importo > 0 non e' garantita nel dominio: e' imposta solo dal @DecimalMin("0.01") sul DTO. Un importo negativo passato direttamente al service supererebbe il check (balance.compareTo(negativo) < 0 e' falso) e invertirebbe il flusso, aumentando il saldo sorgente e diminuendo il destinatario.
- correzione proposta: Aggiungere in transfer() una validazione esplicita req.getAmount() != null && req.getAmount().signum() > 0 prima di ogni altra logica.

### 23. [MEDIUM] src/main/java/com/lipari/bank/movement/MovementService.java:36

- lenti: compliance-amount-reviewer
- descrizione: Il servizio non valida internamente la positivita' dell'importo: un TransferRequest con amount negativo supererebbe il controllo fondi (compareTo < 0 e' falso) e avrebbe l'effetto opposto, accreditando il mittente e addebitando il destinatario.
- correzione proposta: Validare all'inizio di transfer() che req.getAmount() sia > 0 (e con al massimo 2 decimali), lanciando IllegalArgumentException altrimenti, indipendentemente dalla validazione del DTO.

### 24. [MEDIUM] src/main/java/com/lipari/bank/movement/MovementService.java:40

- lenti: movement-domain-reviewer
- descrizione: Nessun controllo di coerenza valuta tra conto sorgente e destinazione: Account.currency viene ignorato, quindi un importo in EUR puo' essere accreditato su un conto in valuta diversa senza conversione.
- correzione proposta: Verificare che from.currency e to.currency coincidano (o applicare un tasso di cambio esplicito) prima di addebitare/accreditare.

### 25. [MEDIUM] src/main/java/com/lipari/bank/movement/MovementService.java:79

- lenti: movement-domain-reviewer
- descrizione: Il ramo di soglia AML (>= 10000) e' un blocco vuoto: non emette alcuna segnalazione ne' audit, quindi il controllo e' codice morto che non produce effetti. Inoltre la condizione usa >= mentre regolamento://aml-policy (letta via MCP) prevede 'sopra 10.000 EUR' per la segnalazione e 'sopra 5.000 EUR' per l'audit, quindi la soglia al limite e' anche disallineata.
- correzione proposta: Implementare l'emissione di segnalazione/audit alle soglie di regolamento://aml-policy (segnalazione > 10000, audit > 5000) con la corretta semantica di confronto, oppure rimuovere il blocco se la logica appartiene a un altro componente.

### 26. [MEDIUM] src/main/java/com/lipari/bank/movement/dto/TransferRequest.java:17

- lenti: compliance-amount-reviewer
- descrizione: Il campo amount ha solo @DecimalMin("0.01") senza vincolo @Digits: importi con piu' di 2 decimali o senza tetto massimo passano la validazione, producendo saldi con scala incoerente con la colonna (precision 19, scale 2) e trasferimenti illimitati.
- correzione proposta: Aggiungere @Digits(integer = 17, fraction = 2) e un limite massimo di trasferimento configurabile (es. @DecimalMax su una property di configurazione) per prevenire overflow logico e importi non normalizzabili.

### 27. [LOW] src/main/java/com/lipari/bank/movement/MovementController.java:26

- lenti: movement-domain-reviewer
- descrizione: Il controller espone direttamente l'entita' JPA Movement come body di risposta (listByAccount e statement): il modello interno, con @Data di Lombok (equals/hashCode/toString su tutti i campi), viene serializzato/esposto senza DTO di confine.
- correzione proposta: Introdurre un DTO di risposta per i movimenti con i soli campi necessari, evitando di restituire direttamente l'entita' di persistenza.

### 28. [LOW] src/main/java/com/lipari/bank/movement/MovementController.java:33

- lenti: movement-domain-reviewer
- descrizione: L'endpoint statement invoca movementService.buildStatement(accountId) e ne scarta il risultato, per poi rieseguire findByAccountIdOrderByExecutedAtDesc: il totale calcolato (con la logica difettosa di segno) non viene mai usato e la query e' duplicata.
- correzione proposta: Rimuovere la chiamata a buildStatement da questo endpoint se il totale non viene esposto, oppure restituire il totale elaborato evitando la seconda query.

### 29. [LOW] src/main/java/com/lipari/bank/movement/MovementService.java:51

- lenti: movement-domain-reviewer
- descrizione: Le due gambe del transfer ottengono due Instant.now() distinti (linee 51 e 60), quindi lo stesso trasferimento puo' avere executedAt leggermente diversi; inoltre TransferResponse espone solo l'id della gamba OUT come 'transferId', senza legame con la gamba IN.
- correzione proposta: Calcolare un unico Instant esterno e assegnarlo a entrambi i movimenti; esporre un identificativo di trasferimento condiviso invece dell'id della sola gamba OUT.

### 30. [LOW] src/main/java/com/lipari/bank/movement/MovementService.java:51

- lenti: compliance-amount-reviewer
- descrizione: Le due legs dello stesso trasferimento usano due chiamate distinte a Instant.now(): i timestamp di addebito e accredito possono differire, indebolendo la coerenza del audit trail e l'appaiamento dei movimenti.
- correzione proposta: Catturare una sola variabile Instant eseguito = Instant.now() all'inizio dell'operazione e assegnarla sia a out che a in per garantire timestamp identici.

### 31. [LOW] src/main/java/com/lipari/bank/movement/dto/TransferRequest.java:20

- lenti: api-contract-reviewer
- descrizione: Il campo description non ha vincolo di lunghezza (@Size): il contratto accetta stringhe di dimensione arbitraria che vengono salvate ed esposte nei movimenti.
- correzione proposta: Aggiungere @Size(max = 255) (o al massimo previsto dal DB) al campo description con message esplicito.

## Divergenze di gravita' conservate

- src/main/java/com/lipari/bank/movement/MovementService.java:76 -> movement-domain-reviewer=HIGH, performance-reviewer=CRITICAL (gate = CRITICAL)
