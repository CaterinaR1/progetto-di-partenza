# LipariBank — il progetto su cui lavori

Backend REST Spring Boot 3.3 su Java 21, con i tre concetti minimi di una banca: `Customer`, `Account`, `Movement`. Gira, ha un database vero e un'autenticazione vera, ed è la codebase che i tuoi agent leggeranno, recensiranno e interrogheranno per tre giorni.

Il bootcamp **non insegna Spring e non ti chiede di scrivere Java**. Questo progetto è il bersaglio: quello che scrivi tu sta in `.claude/`, in `.opencode/` e negli script che orchestrano gli agent. Il LipariBank è ciò su cui li fai lavorare.

Se arrivi dal Bootcamp Microservizi del catalogo Lipari e hai il tuo LipariBank Multi-Service, usa quello: è più ricco e va benissimo. Questo serve a chi arriva senza un progetto banking in mano, e nessuna giornata dà per scontato che tu abbia l'uno o l'altro.

---

## Farlo partire

Serve Docker. Maven no: il progetto porta il **wrapper**, che al primo uso scarica da sé la versione giusta.

```bash
docker compose up -d          # MySQL 8 sulla 3306, con volume persistente
./mvnw spring-boot:run           # l'applicazione sulla 8080
```

Liquibase crea lo schema e i dati di esempio al primo avvio: due clienti, due conti con saldo, due utenti.

Verifica che risponda:

```bash
curl -s localhost:8080/actuator/health
# → {"status":"UP"}
```

### Autenticarsi e fare un bonifico

Tutto ciò che non è `/api/auth/**` o `/actuator/**` vuole un token.

```bash
TOKEN=$(curl -s -X POST localhost:8080/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"alice","password":"alice123"}' \
  | sed -E 's/.*"token":"([^"]+)".*/\1/')

curl -s -X POST localhost:8080/api/movements/transfer \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"fromAccountId":1,"toAccountId":2,"amount":100.00,"description":"prova"}'
```

Il secondo utente è `bob` / `bob123`, e i due conti di partenza hanno 1000,00 e 500,00 euro.

### Gli endpoint, tutti quelli che ci sono

| Metodo e percorso | Cosa fa | Token |
|---|---|:-:|
| `POST /api/auth/login` | restituisce un JWT dato username e password | no |
| `POST /api/movements/transfer` | trasferisce fra due conti e registra i movimenti | sì |
| `GET /api/movements?accountId=1` | i movimenti di un conto, dal più recente | sì |
| `GET /api/accounts/{id}` | un conto | sì |
| `GET /api/accounts/with-movements` | tutti i conti, ciascuno con i suoi movimenti | sì |
| `GET /actuator/health` | stato dell'applicazione | no |

---

## Com'è fatto

```
progetto-di-partenza/
├── pom.xml
├── Dockerfile
├── docker-compose.yml
├── .gitignore
└── src/
    ├── main/
    │   ├── java/com/lipari/bank/
    │   │   ├── LipariBankApplication.java
    │   │   ├── common/
    │   │   │   ├── CorrelationIdFilter.java      un id di correlazione nell'MDC dei log
    │   │   │   └── GlobalExceptionHandler.java   @RestControllerAdvice
    │   │   ├── customer/       Customer, CustomerRepository
    │   │   ├── account/        Account (saldo in BigDecimal), Repository, Controller
    │   │   ├── movement/       Movement, Repository, Service, Controller, dto/
    │   │   ├── security/       SecurityConfig, JwtFilter, JwtService
    │   │   └── web/            AuthController
    │   └── resources/
    │       ├── application.yml
    │       └── db/changelog/   lo schema e i dati di esempio, in Liquibase
    └── test/
        └── java/com/lipari/bank/TransferIT.java  il caso felice del bonifico
```

Diciannove classi Java, due changeset Liquibase. Il cuore è `MovementService.transfer()`: è il metodo transazionale che sposta il denaro, ed è il posto da cui conviene partire a leggere.

---

## Il repository git

Il progetto arriva come cartella, non come repository, e il `.gitignore` c'è già. Inizializzalo prima di cominciare, perché ogni giornata ti chiede di lavorare per commit:

```bash
git init
git add -A
git commit -m "LipariBank: punto di partenza del bootcamp"
```

---

## Cosa non è

Non è un sistema production-grade, e non pretende di esserlo: non ha circuit breaker, né retry, né audit trail completo, né multi-valuta. Non è multi-servizio: c'è un solo Spring service, che non parla con nessun altro. E non è pronto per un cluster: niente profili per ambiente, niente telemetria, niente probe pensate per la produzione.

Soprattutto: **non è un'architettura modello.** È un backend scritto come lo scrive una squadra sotto scadenza, con le scorciatoie che una squadra sotto scadenza prende. È esattamente per questo che serve: i tuoi reviewer avranno qualcosa di vero da trovare, e quello che troveranno non te l'ha suggerito nessuno.

Per la stessa ragione, se lo riusi fuori dal bootcamp trattalo come codice da recensire, non come codice da mostrare.

## Claude Code Assets (Giorno 1 - PW G1)

Questa sezione documenta gli asset agentici costruiti per il Giorno 1 su OpenCode:
tre reviewer con perimetri dichiarati e disgiunti, una skill con il formato d'uscita
condiviso, e il presidio che impedisce di scrivere sul codice revisionato.

### Regola con cui ho separato i perimetri

Il criterio di separazione e' la **cartella/tipo di cambiamento**, con un tie-break
esplicito sul caso difficile. Un reviewer parte solo se la richiesta cade dentro il
suo perimetro, e i perimetri non si sovrappongono.

- **movement-domain-reviewer** -> attivo solo su `com.lipari.bank.movement/**`
  (movement, movement/dto, test movimento). Domanda: la logica interna dei
  movimenti e' corretta (transazioni, idempotency, invarianze, N+1, tracciabilita')?
- **compliance-amount-reviewer** -> attivo solo quando la modifica tocca
  direttamente importi/saldi/calcoli finanziari o regole AML (amount, balance,
  BigDecimal, soglie, audit su operazioni monetarie). Domanda: il denaro e' trattato
  secondo le regole di compliance?
- **api-contract-reviewer** -> attivo solo sul contratto API esterno
  (`@RestController`, endpoint `/api/**`, DTO esposti). Domanda: cio' che leggiamo
  fuori e' stabile, validato e sicuro?

**Caso difficile - `MovementController.java`** (sta nel dominio movimenti, maneggia
un importo ed e' il contratto esposto): rivendicato da tutti e tre. Tie-break **per
concern**: vince il reviewer che corrisponde all'aspetto che il cambiamento tocca.
Se la modifica e' alla logica di dominio -> `movement-domain-reviewer`; se tocca la
forma/stabilita' del contratto pubblico -> `api-contract-reviewer`; se cambia
davvero il calcolo/valore degli importi -> `compliance-amount-reviewer`. In nessun
caso ne partono due insieme: chi perde il tie-break **non viene attivato**.
Questo e' il motivo per cui le description sono scritte in modo mutualmente esclusivo
(dicono anche quando NON partire) e per cui il routing e' gia' di per se' un
informazione: se parte il reviewer del contratto, la richiesta riguardava il contratto.

### Artefatti

**Subagent - `.opencode/agents/`** (frontmatter OpenCode: `mode: subagent`, `permission`):

| Artefatto | Percorso | Description (sintesi) | Invocazione |
|---|---|---|---|
| movement-domain-reviewer | `.opencode/agents/movement-domain-reviewer.md` | Parte su `movement/**`; NON parte su contratto API puro ne' su file fuori perimetro | `opencode run "review del dominio movimenti di MovementService.java"` (routing automatico) |
| compliance-amount-reviewer | `.opencode/agents/compliance-amount-reviewer.md` | Parte quando cambiano importi/saldi/calcoli/AML; NON parte su pura struttura senza impatto monetario | `opencode run "review compliance sugli importi di TransferRequest.java"` (routing automatico) |
| api-contract-reviewer | `.opencode/agents/api-contract-reviewer.md` | Parte su `@RestController`/`/api/**`/DTO esposti; NON parte su logica service/repo interna senza contratto | `opencode run "review del contratto API esterno di MovementController.java"` (routing automatico) |

Invocazione esplicita (per forzare un reviewer): aggiungere `--agent <nome>`, es.
`opencode run "..." --agent movement-domain-reviewer`.

**Skill - `.opencode/skills/`**:

- `review-format/SKILL.md` - formato unico dei rilievi: ogni finding ha `file`,
  `riga`, `gravita` (CRITICAL/HIGH/MEDIUM/LOW), `descrizione`, `correzione_proposta`
  (proposta e **non applicata**), output array JSON. E' la fonte unica di verita' del
  formato e i tre reviewer la caricano; la sua allowlist (`Read, Grep, Glob`) e'
  dimensionata sul ruolo, non su cio' che potrebbe servire.
- `compliance-aml-check/SKILL.md` - i cinque controlli AML, portata per coerenza
  OpenCode.

### Presidio: nessuno dei tre scrive sul codice che revisiona

Il divieto **non** e' una buona intenzione nel system prompt: e' un presidio di
codice. In OpenCode non esiste l'hook di Claude Code, quindi il presidio e' il
**blocco `permission` di ogni reviewer**:

```yaml
permission:
  edit: deny              # nessuna scrittura, mai
  bash:
    "*": deny             # shell negata di default
    "rg *": allow         # ammessi solo comandi di sola lettura/osservazione
    "find *": allow
    "ls *": allow
    "cd *": allow
    "pwd": allow
    "echo *": allow
    "Get-ChildItem *": allow   # lettura Windows (la shell qui e' PowerShell)
    "Get-Content *": allow
    "Select-String *": allow
    "Get-Item *": allow
    "dir *": allow
    "type *": allow
    "findstr *": allow
    "git log*": allow          # git in sola lettura, per vedere cosa cambia
    "git status*": allow
    "git diff*": allow
    "git show*": allow
```

Il CLI applica `edit: deny` da codice, quindi regge anche quando il modello e'
convinto di fare la cosa giusta. La prova e' doppia: chiedere una modifica durante
una review e verificare che venga bloccata, e verificare che il resto della sessione
continui a funzionare. L'hook in `.claude/settings.json` resta per Claude Code (in
OpenCode non ha effetto), ma per OpenCode il presidio e' il blocco permission.

### Cosa ho dovuto cambiare di quello che ho ereditato (una riga di ragione per modifica)

- Portato il subagent da `.claude/agents/` a `.opencode/agents/` con frontmatter OpenCode - perche' OpenCode non legge `.claude/agents/`.
- Riscritto `tools: ["*"]` in `tools` mirati (read/grep/glob) - perche' un reviewer non deve avere piu' strumenti di quelli che il ruolo giustifica.
- Rimossa la riga `model: sonnet` - perche' OpenCode non la conosce e rifiuta la config con un errore generico.
- Aggiunto `permission` con `edit: deny` e bash allowlist - perche' il presidio anti-scrittura in OpenCode vive nel permesso, non nel prompt.
- Riscritta la `description` dicendo quando parte e quando NON parte - perche' con tre reviewer il confine e' l'informazione, e una description larga farebbe partire tutti e tre.
- Sostituita la `description: "Reviewer di codice"` con tre perimetri nominati (movimenti / importi-compliance / contratto API) - perche' un nome/description che promette troppo e' la prima riga che si allarga.
- Introdotto il riferimento obbligatorio alla skill `review-format` in tutti e tre - perche' tre uscite in formati diversi non si leggono e non si aggregano.
- Eliminata la ripetizione libera del formato dentro i system prompt - perche' il formato deve stare in un posto solo (la skill), cosi' un quarto reviewer lo eredita senza che glielo si debba dire.
- Portata la skill AML in `.opencode/skills/` - perche' OpenCode cerca le skill anche in `.claude/skills/`, ma teniamo la struttura coerente.
- Mantenuto l'hook `.claude/settings.json` ereditato - perche' serve ancora a Claude Code e non interferisce con OpenCode.
- Aggiunti comandi di lettura Windows all'allowlist (`Get-ChildItem`, `Get-Content`, `Select-String`, `dir`, `type`, `findstr`) - perche' l'allowlist ereditata era tarata su shell Unix e su Windows i reviewer tentavano comandi bloccati, abortendo la review a meta'.
- Aggiunti `git log/status/diff/show` all'allowlist - perche' il reviewer cerca legittimamente di vedere cosa cambia, e negare anche la lettura di git faceva fallire il subagent invece di limitarlo.
- Resa la description di ogni reviewer mutuamente esclusiva (ognuna dichiara anche quando NON partire) - perche' ereditando le tre description si toccavano e piu' di un reviewer poteva rivendicare la stessa richiesta.

### Run trace - la prova che il routing gira

Prova eseguita in **una sessione OpenCode**, con richieste di perimetri diversi, e
con il reviewer **mai nominato** (la richiesta descrive solo il perimetro, OpenCode
sceglie il subagent in base alla `description`). Il dettaglio completo, con le righe
di log che provano quale `... Agent` e' partito, e' in **`RUN-TRACE.md`**.

| Richiesta | Reviewer partito | N. reviewer |
|---|---|---|
| dominio movimenti (`MovementService.java`) | movement-domain-reviewer | 1 |
| contratto API esterno (`MovementController.java`) | api-contract-reviewer | 1 |
| compliance importi (`TransferRequest.java`) | compliance-amount-reviewer | 1 |
| fuori perimetro (`pom.xml`) | nessuno | 0 |

- Su ognuna delle tre richieste ne parte **uno solo**, e i perimetri sono disgiunti;
  il fatto che sia partito *quel* reviewer e' gia' un'informazione.
- Sul file fuori perimetro **non si attiva nessuno dei tre**.

Output salvati in `.md` (copia dei findings, formato `review-format`):

- `review-MovementService.md` (movement-domain)
- `review-API-MovementController.md` (api-contract)
- `review-Amount-Movements.md` (compliance-amount)
- `review-pom-out.md` (fuori perimetro - nessun reviewer dei tre attivato)
- `auto-movement.md`, `auto-api.md`, `auto-compliance.md`, `auto-pom.md` (log di
  sessione grezzi: contengono la riga `... Agent` che prova la delega)

Ogni finding ha `file`, `riga`, `gravita`, `descrizione` e `correzione_proposta`
(non applicata), come impone la skill `review-format`.

---

## Code Review Suite — quattro lenti in parallelo (Giorno 2)

Si parte dalla prima versione del collega: `starter_collega_giorno_02/starter-collega/`
(vedi `README-GINO.md`). Gino lanciava **un** reviewer con l'SDK di Claude, **in fila**,
e ne era insoddisfatto senza capire bene perche'. Qui diventa una suite a **quattro
lenti che girano insieme**, che riconcilia i risultati e produce un riepilogo pensato
per un **cancello sul merge**.

### Le quattro lenti

Tre vengono dal Giorno 1 (`movement-domain`, `compliance-amount`, `api-contract`); la
quarta, `performance-reviewer`, e' nuova. I perimetri sono ortogonali: dominio dei
movimenti, sicurezza/compliance del denaro, contratto API, costo di esecuzione.

**Perche' quattro e non sei.** Quattro perimetri ortogonali coprono quasi tutto il
codice che tocca il denaro; ogni lente in piu' costa tempo e token in modo lineare e
produce sempre piu' findings sovrapposti da deduplicare. Il vuoto vero rispetto al
Giorno 1 era chi guarda **N+1, query nei cicli, contenzione, indici**: senza quella
lente, un difetto di prestazione su codice che muove denaro non lo vedeva nessuno.
Misuriamo questo, prima di aggiungere altro.

### Come si lancia

```bash
cd starter_collega_giorno_02/starter-collega
python code_review_suite.py ../../src/main/java/com/lipari/bank/movement/
```

Non serve `uv` ne' SDK: lo script usa solo la standard library e l'helper del repo
`.opencode/opencode_query.py`. Opzioni utili: `--gate HIGH` (soglia del cancello),
`--budget-token`, `--budget-secondi`, `--tetto-secondi`, `--solo <reviewer,...>`, e
`--da-json review-report.json` per **ri-riconciliare** un report esistente senza
richiamare i reviewer.

Scrive `review-report.md` (leggibile) e `review-report.json` (per il cancello) e
restituisce un codice di uscita:

| Uscita | Significato |
|:-:|---|
| 0 | nessun rilievo alla soglia e **tutti** i reviewer hanno risposto |
| 1 | almeno un rilievo >= soglia, **oppure** copertura incompleta (reviewer mancante/fallito/illeggibile) |
| 2 | errore di configurazione o di sicurezza (target inesistente, `--solo` non valido, codice revisionato modificato durante la review) |
| 3 | tetto di spesa/tempo superato: run interrotta a meta' |

### La regola di riconciliazione (gravita')

Lo stesso difetto puo' essere visto da due lenti con **gravita' diverse**. La suite lo
accorpa (similarita' dei termini della descrizione, sulla stessa riga) e:
- la gravita' del **gate** e' la **massima** fra quelle proposte, cosi' il cancello non
  scende mai sotto la valutazione piu' severa;
- la **divergenza resta scritta**: il rilievo e' marcato `[CONFLITTO]` con la gravita'
  di ogni lente, cosi' la persona vede chi ha dissentito e su cosa.

La competenza per materia e' esposta, non applicata in automatico: il max e' per il
gate, le singole voci sono per chi legge.

### I quattro modi in cui si rompe (e cosa fa la suite)

| Guasto | Comportamento previsto |
|---|---|
| un reviewer manca o il suo file e' malformato | sezione `FALLITO` col motivo; **gli altri consegnano**; il gate resta bloccato per copertura incompleta |
| l'uscita di un reviewer non e' interpretabile | reviewer marcato `ILLEGGIBILE`, la run prosegue |
| il tetto di spesa/tempo e' superato | la run **si ferma** (uscita 3), non avvisa e basta |
| la cartella da rivedere non esiste | fail-fast **prima** di lanciare (uscita 2) |

### Numeri dell'ultima run (caso del Prompt 1: `buildStatement` con N+1 su importi)

- quattro partenze allo **stesso istante** (15:07:23.775–.841, entro ~66 ms): e' la
  prova che girano in parallelo, non in fila;
- durata totale ~329 s (il piu' lento dei quattro), spesa 279762/500000 token, costo 0;
- copertura completa (4/4 `OK`), 34 findings riconciliati, gate **BLOCCATO** (uscita 1);
- **nessun file del codice modificato** dai reviewer (`git status` pulito): il presidio
  `edit: deny` regge.

Il conteggio esatto (findings grezzi, accorpamenti e conflitti) **varia da run a run**
perche' dipende da come il modello formula le descrizioni. In una run precedente, sulle
stesse lenti: 36 findings grezzi → **31 dopo deduplica**, con **2 conflitti** di gravita'
conservati (riga 36: movement `CRITICAL` vs compliance `HIGH`; riga 79: movement `MEDIUM`
vs compliance `CRITICAL`). La variabilita' della *formulazione* e' attesa; cio' che resta
deterministico e' l'*involucro* (budget, concorrenza, tempi, non-mutazione, formato,
routing) ed e' quello che coprono i test in `test_code_review_suite.py` (`python
test_code_review_suite.py`, 19 test, nessuna rete).

### Cosa ho dovuto cambiare di quello che ho ereditato (Giorno 2)

**Difetti trovati negli asset del Giorno 1.**

- Chiuso il frontmatter di `compliance-amount-reviewer.md` e `api-contract-reviewer.md`
  (mancava il `---` finale) - perche' un frontmatter non chiuso **non applica**
  `edit: deny`: quei due reviewer potevano scrivere sul codice che revisionano.
- Ripulito il frontmatter di `compliance-amount-reviewer.md` da caratteri di controllo
  (`\x07`, `\x08`, `\x0c`, `\x0d`) - perche' chiuso il frontmatter, il YAML andava in
  errore e l'agente **spariva** dalla lista (`opencode agent list` lo ometteva).
- Portato `movement-domain-reviewer` da `mode: subagent` a `mode: all` - perche' la
  1.18 con `--agent` ripiega su `build` (che puo' scrivere) e il reviewer viene
  ignorato.

**La suite del collega, riscritta.**

- Sostituito l'SDK di Claude (`query()`) con `query_opencode()` del repo - perche' qui
  l'SDK non e' disponibile e l'helper fa la stessa parte con la sola stdlib.
- Reviewer lanciati **insieme** (`asyncio.gather`), non in fila - perche' l'attesa e' il
  costo dominante.
- Rimossa `Edit` dagli strumenti e appoggiato il presidio a `edit: deny` dei reviewer -
  perche' un reviewer non deve mai scrivere.
- Aggiunti budget condiviso con **abort** ai tetti, retry sugli errori riprovabili e
  tetto di tempo per processo - perche' la versione del collega non sapeva quanto
  spendeva ne' si fermava.
- Aggiunte deduplica e riconciliazione della gravita' (max + divergenza) - perche' la
  versione del collega scriveva lo stesso difetto due volte con due gravita' diverse
  senza decidere quale valesse.
- Rimossa `claude-agent-sdk` da `pyproject.toml` - perche' non serve piu'.

**Difese aggiunte nella seconda passata (Prompt 2).**

- **Preflight `edit: deny`**: un reviewer viene lanciato solo se il suo file dichiara
  `edit: deny`; altrimenti non parte e finisce in `FALLITO` - perche' il presidio non
  deve dipendere dal fatto che qualcuno se ne ricordi.
- **Verifica di non-mutazione**: a fine run si confronta `git status --porcelain` del
  path revisionato prima e dopo; se cambia, uscita 2 - perche' "non deve scrivere" va
  **verificato**, non solo dichiarato.
- **Gravita' sconosciuta = `UNKNOWN`**, che nel gate vale piu' di `HIGH` - perche' una
  valutazione illeggibile non deve far passare un rilievo come se fosse lieve.
- **`--budget-costo`** oltre a `--budget-token`: abort anche su spesa monetaria.
- Retry reso **budget-aware** (il secondo tentativo non riparte se il budget e' finito)
  e **chiusura esplicita** dei generatori dei reviewer sulla via d'uscita anticipata.

**Difetto trovato nella skill (volutamente NON toccata).** `review-format/SKILL.md`
ha i campi corrotti (`ile` per `file`, `iga` per `riga`) e i recinti di codice
mutilati. Essendo la **fonte unica di verita'** del formato, non l'ho modificata:
l'orchestratore e' reso robusto nel parsing (riconosce le chiavi corrotte e sia l'array
sia gli oggetti che lo contengono), cosi' i reviewer restano liberi di seguirla.

---

## Server MCP `finbank-mcp` (Giorno 3 — PW G3)

**FASE 3**: gli stessi dati del LipariBank, esposti come **server MCP** a un
agente, con **3 tool, 2 resource, 1 prompt**. Regola tenuta ferma: **nessun tool
muove denaro**. Il server espone in sola lettura saldo e movimenti e offre una
*simulazione* di bonifico; il regolamento di banca viaggia come resource, cosi'
l'agente lo cita invece di andare a memoria.

### Cosa espone

| Tipo | Nome | Cosa fa | Effetti |
|---|---|---|---|
| tool | `get_account_balance` | saldo reale di un conto (`GET /api/accounts/{id}`) | nessuno |
| tool | `list_recent_movements` | movimenti recenti, con **tetto 50 applicato dal server** (clamp, non errore) | nessuno |
| tool | `simulate_transfer_what_if` | saldi prima/dopo e `would_succeed`, **non muove denaro** | nessuno |
| resource | `regolamento://aml-policy` | soglie AML (10k segnalazione, 5k audit, PEP 1k) | - |
| resource | `regolamento://transfer-policy` | regole del bonifico (fondi, stesso conto, importo minimo) | - |
| prompt | `verifica_effetto_bonifico` | argomenti: `source_account_id`, `target_account_id`, `amount` | - |

Forma degli errori: **espliciti, mai un valore predefinito**. Conto inesistente ->
`ToolError` con `HTTP 404 su GET /api/accounts/999`; `amount` fuori tetto, stesso
conto, fondi insufficienti -> errore oppure `would_succeed:false` con il motivo;
mai un saldo inventato.

### Come si avvia

```powershell
cd finbank-mcp
pip install -e .          # oppure: uv sync
$env:LIPARIBANK_USERNAME = 'svc_mcp'                 # utente di servizio (vedi sotto)
$env:LIPARIBANK_PASSWORD = '<password di servizio>'  # non nel repo
.\run.ps1                 # oppure: ./run.sh
```

Variabili: `LIPARIBANK_BASE_URL` (default `http://localhost:8080`),
`FINBANK_TETTO_MOVIMENTI` (50), `FINBANK_MAX_TRANSFER` (50000). Il server si
autentica come utente di servizio dedicato `svc_mcp` (utente applicativo
separato, senza `customer_id`, creato dal changeset `006-service-user.yaml`),
rinnova il token a 55 minuti o su 401 e si lega **solo a 127.0.0.1**.

La registrazione in OpenCode e' nel blocco `mcp` di `.opencode/opencode.json`
(server `finbank_mcp`, `type: local`, password via `{env:LIPARIBANK_PASSWORD}`).
Il brief citava anche un `.mcp.json` alla radice (stile Claude Code), ma
**OpenCode non legge quel file**: l'integrazione reale e' il blocco `mcp`.
Verificata con `opencode mcp list` -> `finbank_mcp connected`.

### Le prove (trascrizioni in `finbank-mcp/evidence/`)

- **MCP Inspector via CLI** (16 file JSON): `tools/list` (3 tool, schema stretto,
  `additionalProperties:false`), `resources/list`, `resources/read` delle due
  policy, `prompts/list` e `prompts/get`, piu' 10 `tools/call` (saldo 1 e 2; saldo
  `999` -> errore; clamp `limit=999 -> 50`; `limit=0` -> errore; simulazione 100 ->
  ok; fondi insufficienti / stesso conto / destinazione inesistente ->
  `would_succeed:false`; `amount` negativo, zero, oltre tetto -> errore). Exit code
  0 sui successi, 5 con `isError:true` sugli errori.
- **Prompt manuale "quali tool MCP hai"**:
  `finbank-mcp/evidence/mcp-tools-manual-transcript.md` -> l'agente lista i 3 tool.
- **Il reviewer del Giorno 1 che usa i tool MCP durante una review**: run su un
  difetto iniettato in `MovementService.transfer` (controllo fondi rimosso). Il
  `movement-domain-reviewer` ha letto `regolamento://transfer-policy`, chiamato
  `finbank_mcp_get_account_balance` (conti 1 e 2) e
  `finbank_mcp_simulate_transfer_what_if` (2->1, 600 -> `would_succeed=False`),
  citando i valori osservati. Findings in `review-test-giorno3-risposta.md`,
  transcript in `review-test-giorno3-output.json`, invocazioni in
  `review-test-giorno3-audit.jsonl`. Ogni chiamata e' anche nel log di audit del
  server, `finbank-mcp/audit/invocations.jsonl`.

### La tassonomia degli 8 asset (tutto il bootcamp)

Otto asset, quattro categorie: **subagent**, **skill**, **comando**,
**orchestratore/server**. Tutto "Lipari-grade" riutilizzabile.

| Asset | Tipo | File path | Quando attivato | Tool MCP usati |
|---|---|---|---|---|
| Il reviewer dei movimenti (G1) | Subagent | `.opencode/agents/movement-domain-reviewer.md` | su un cambiamento che tocca i movimenti (`movement/**`) | `finbank_mcp_simulate_transfer_what_if`, `finbank_mcp_get_account_balance`; resource `regolamento://transfer-policy` |
| Il reviewer degli importi (G1) | Subagent | `.opencode/agents/compliance-amount-reviewer.md` | su un cambiamento che tocca un importo/saldo/calcolo/AML | suggerisce la resource `regolamento://aml-policy` |
| Il reviewer del contratto (G1) | Subagent | `.opencode/agents/api-contract-reviewer.md` | su cio' che il LipariBank espone all'esterno | nessuno |
| La quarta lente (G2) | Subagent | `.opencode/agents/performance-reviewer.md` | la competenza aggiunta al G2 (costo di esecuzione) | nessuno |
| La skill del formato (G1) | Skill | `.opencode/skills/review-format/SKILL.md` | su ogni review, per la forma d'uscita | nessuno |
| `/review-pr` | Slash command | `.opencode/commands/review-pr.md` | manuale, invocata dall'utente | (orchestrator) |
| `code_review_suite.py` | SDK orchestrator | `starter_collega_giorno_02/starter-collega/code_review_suite.py` | CLI standalone | (orchestrator) |
| `finbank-mcp` | MCP server | `./finbank-mcp/` | registrato nel blocco `mcp` di `.opencode/opencode.json` (OpenCode; non `.mcp.json`) | (lui espone i 3 tool) |

Fuori dai conteggio, ma presenti nel repo: la skill companion
`compliance-aml-check/SKILL.md` (co-asset della categoria Skill) e
`hello-banking.md` (agente di prova, non un reviewer).

### Cosa ho cambiato di quello che ho ereditato (Gino, Giorno 3)

Il primo tentativo di Gino (`starter_collega_giorno_03/starter-collega/server.py`,
2 tool) *gira* ma non regge. Una riga di ragione per modifica:

- **Rimosso il tool `execute_transfer`** (faceva `POST /api/movements/transfer`,
  cioe' **muoveva davvero il denaro**) e sostituito con
  `simulate_transfer_what_if`, che legge due saldi e calcola in memoria - perche' il
  mandato e' esporre i dati, non dare a un agente il grilletto del bonifico.
- **Aggiunta l'autenticazione** (utente di servizio `svc_mcp`, Bearer, rinnovo a
  55 min, retry su 401) - perche' ogni endpoint non `/api/auth` vuole un token e
  senza token ogni chiamata e' un 401: Gino leggeva l'errore *come se fosse* il saldo.
- **Aggiunti `raise_for_status`/mappatura errori -> `ToolError`** - perche' Gino
  faceva `response.json()` senza controllare lo stato HTTP: un 404 diventava un "dato".
- **Ristretti i tipi e aggiunte validazioni** (`account_id` int > 0, `amount`
  decimale e mai `float` per il denaro, `limit` clampato 1..50, `amount <=
  MAX_TRANSFER`) - perche' `amount: float` e `id: int` senza vincoli sono il primo
  modo per far entrare un importo sbagliato in banca.
- **Docstring ricche ("quando usarla / quando NO")** al posto di `"Get balance."` -
  perche' e' esattamente il motivo per cui, come racconta Gino, "dall'assistente non
  parte da solo": un tool senza contratto leggibile non viene scelto dal modello.
- **Esposto il regolamento come resource** (`regolamento://aml-policy`,
  `regolamento://transfer-policy`) - risponde al dubbio di Gino ("non ho capito se
  avrei dovuto esporli"): si', perche' cosi' l'agente cita la regola invece di
  inventarla.
- **Bind a 127.0.0.1** in `run.ps1`/`run.sh` al posto del default su tutte le
  interfacce - perche' Gino l'aveva "aperto su tutte le interfacce" per provarlo: un
  servizio con accesso ai dati di conto non deve stare in ascolto sul mondo.
- **Risposta minima** (solo `account_id`, `balance`, `currency`, `status`) invece
  dell'oggetto conto intero - perche' l'entita' JPA porta anche `customerId` e
  `iban`, che non servono e non vanno esposti.
- **Corretto il payload del bonifico** (`fromAccountId`/`toAccountId`, non
  `sourceAccountId`/`targetAccountId`) - i nomi di Gino non combaciano col DTO: la
  chiamata sarebbe fallita comunque.


