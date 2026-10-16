# Regolamento operativo — bonifico (transfer)

Fonte delle regole di backend: `src/main/java/com/lipari/bank/movement/`
(`MovementService.java`, `dto/TransferRequest.java`). Le righe citate sono
quelle del repository al momento della scrittura. Questo file e' la copia
esposta dal server MCP come `regolamento://transfer-policy`.

## Regole che il backend applica davvero

| Regola | Sorgente |
|---|---|
| sorgente e destinazione devono essere conti **diversi** | `MovementService.java:27-29` |
| entrambi i conti devono **esistere** | `MovementService.java:31-34` |
| il saldo sorgente deve essere **>= importo** (fondi sufficienti) | `MovementService.java:36-38` |
| importo **minimo 0.01** | `TransferRequest` `@DecimalMin("0.01")` |
| operazione **transazionale**: saldi e due movimenti insieme | `MovementService.transfer()` `@Transactional` |

## Tetto del server MCP (non e' una regola bancaria)

`finbank-mcp` rifiuta in simulazione importi **oltre 50.000 EUR**
(`FINBANK_MAX_TRANSFER`): e' un tetto di questo server, dichiarato per evitare
che un argomento fuori scala produca calcoli privi di senso. Il backend
LipariBank non ha un massimo per operazione: non attribuire a questa cifra
un significato regolamentare.

## Cosa NON fa questo server

- Non esegue bonifici: non esiste alcun percorso che modifichi un saldo.
- Non applica le soglie AML: le trovi in `regolamento://aml-policy`.
- Non scrive audit nel backend: tiene solo il proprio log delle invocazioni.
