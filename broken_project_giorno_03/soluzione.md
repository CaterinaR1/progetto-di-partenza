# Soluzione — Broken Project Giorno 3 (caso-1 … caso-4)

Consegna: testo nel campo **Testo Online**. Per ogni caso: cosa ho riconosciuto / da quale indizio / cosa ho cambiato. Per i due difetti di sicurezza (casi 3 e 4) una quarta riga: come me ne accorgerei in un sistema che non ho scritto io.

Metodo: diagnosi e verifica con l'**introspezione del server** (`mcp.list_tools()`: nome, descrizione, schema JSON) prima e dopo il fix — non leggendo il codice e fidandosi. File corretti in place: `caso-{1,2,3}/BUGGY/server.py` e `caso-4/BUGGY/run.sh`.

---

## Caso 1

- **Riconosciuto:** il tool dichiarava un solo parametro `params` di tipo oggetto *senza campi* — nessun contratto, quindi il modello inventava chiavi, passava oggetti vuoti o il valore giusto sotto un nome sbagliato.
- **Indizio (dal server, non dal codice):** nell'elenco dei tool lo schema era `{"params": {"type": "object", "additionalProperties": true}}` senza `properties`, e la descrizione era solo "Query account info." — niente da cui capire cosa passargli.
- **Cambiato:** parametro nominato e tipizzato `account_id: int`, corpo reale (GET `/api/accounts/{id}` + `raise_for_status`), docstring con "Use this when… / Args / Returns". Lo schema ora espone `account_id: integer` con descrizione.

## Caso 2

- **Riconosciuto:** il tool c'era ed era invocabile, ma il reviewer non lo usava **mai**: la descrizione non diceva *quando* usarlo, quindi il modello non lo collegava al compito.
- **Indizio (dal server, non dal codice):** la descrizione era solo "Get balance." — nessun contesto né trigger; dall'elenco dei tool non emergeva il caso d'uso "review → verifica il saldo reale".
- **Cambiato:** docstring con "Use this tool when… / Do NOT…" che nomina esplicitamente il caso review, parametro `id` → `account_id`, sezione Returns.

## Caso 3 (sicurezza)

- **Riconosciuto:** il server esponeva un tool che esegue un bonifico **reale** (`execute_transfer` = POST su `/api/movements/transfer` in production); il reviewer l'ha usato e ha spostato €100.
- **Indizio (dal server, non dal codice):** nell'elenco compariva un **verbo d'effetto** — nome `execute_transfer`, descrizione "Execute a transfer in production". Dalla mia macchina il comportamento era identico al corretto: non si vede provando il proprio lavoro.
- **Cambiato:** rimosso il POST; ora espone solo `simulate_transfer_what_if`, **read-only** (solo GET + calcolo locale). Least privilege: chi fa review non ha strumenti che scrivono.
- **Come me ne accorgerei in un sistema non mio:** enumerare tutti i tool raggiungibili dall'agente e marcare quelli con **effetto di scrittura** (nomi tipo execute/transfer/delete, e a valle POST/PUT/DELETE); confrontare il permesso concesso col compito (una review non deve poter scrivere); controllare l'audit per scritture non autorizzate e **separare server read-only da server mutanti**.

## Caso 4 (sicurezza)

- **Riconosciuto:** il server era raggiungibile dalla **rete senza autenticazione**; un collega da un'altra macchina leggeva i saldi senza che gli fosse chiesto nulla.
- **Indizio (dalla configurazione, non dal codice):** il lancio usava `--transport streamable-http --host 0.0.0.0 --port 8765` **senza auth**. Dalla mia macchina identico al corretto → si vede solo da fuori o in audit.
- **Cambiato:** bind a `--host 127.0.0.1` (solo loopback) nel `run.sh`, con nota che per l'esposizione in rete serve `auth=` (Bearer/JWT) e che il default sicuro resta `stdio`. Verificato: `0.0.0.0:8765` = tutte le interfacce, `127.0.0.1:8765` = solo locale.
- **Come me ne accorgerei in un sistema non mio:** inventariare l'esposizione di rete — cercare endpoint MCP **in ascolto** (scan/`netstat`) e per ognuno controllare bind address + trasporto + presenza di auth; provare la chiamata **da un'altra rete**; imporre che `streamable-http` richieda sempre autenticazione e che l'host di default sia loopback.

---

## Nota di verifica

Diagnosi e conferma fatte con l'introspezione del server (`mcp.list_tools()`: nome, descrizione, schema JSON) prima/dopo il fix. Esito:

- caso 1: schema `params` (object vuoto) → `account_id: integer`;
- caso 2: descrizione "Get balance." → descrizione con trigger d'uso;
- caso 3: nessun tool mutante (nessun verbo HTTP `post/put/patch/delete` residuo);
- caso 4: bind di rete `0.0.0.0` → `127.0.0.1` (loopback).

I tre `server.py` compilano.
