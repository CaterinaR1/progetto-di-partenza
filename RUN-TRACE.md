# Run trace - routing dei tre reviewer (LipariBank, PW G1)

Prova eseguita su **OpenCode** nella stessa sessione progettuale (stesso repository,
stesso `.opencode/`). In ogni prova il reviewer **non e' stato nominato**: la richiesta
descrive solo il perimetro, e OpenCode seleziona da solo il subagent corretto in base
alla `description`. Sotto ogni prova c'e' la riga di log della sessione che mostra
**quale** subagent e' partito (equivalente testuale dello screenshot).

## Prova 1 - dominio movimenti

Richiesta:

    opencode run "Fai la review del dominio movimenti di
    src/main/java/com/lipari/bank/movement/MovementService.java
    e produci i findings in formato JSON."

Log sessione (estratto):

    > build - big-pickle
      Skill "review-format"
      Glob "src/main/java/com/lipari/bank/movement/**/*.java" 6 matches
      - Review MovementService.java  Movement-Domain-Reviewer Agent
      check Review MovementService.java  Movement-Domain-Reviewer Agent

Reviewer partito: **Movement-Domain-Reviewer Agent** (uno solo).

Findings: -> `review-MovementService.md`

## Prova 2 - contratto API esterno

Richiesta:

    opencode run "Review del contratto API esposto all'esterno:
    src/main/java/com/lipari/bank/movement/MovementController.java.
    Applica il reviewer del contratto API esterno."

Log sessione (estratto):

    - Review contratto API MovementController  Api-Contract-Reviewer Agent
    check Review contratto API MovementController  Api-Contract-Reviewer Agent

Reviewer partito: **Api-Contract-Reviewer Agent** (uno solo, diverso dal precedente).

Findings: -> `review-API-MovementController.md`

## Prova 3 - compliance sugli importi

Richiesta:

    opencode run "Review compliance sugli importi di
    src/main/java/com/lipari/bank/movement/dto/TransferRequest.java:
    applica il reviewer della compliance sugli importi e produci i findings in JSON."

Log sessione (estratto):

    - Review importi TransferRequest  Compliance-Amount-Reviewer Agent
    check Review importi TransferRequest  Compliance-Amount-Reviewer Agent

Reviewer partito: **Compliance-Amount-Reviewer Agent** (uno solo).

Findings: -> `review-Amount-Movements.md`

## Prova 4 - fuori da tutti e tre i perimetri

Richiesta:

    opencode run "Fai la review di pom.xml (configurazione della build)."

Esito: **nessuno** dei tre reviewer specializzati parte. Il file di build resta
fuori dai tre perimetri. Dettaglio in `review-pom-out.md`.

## Esito complessivo

| Richiesta | Reviewer partito | Numero reviewer |
|---|---|---|
| dominio movimenti (`MovementService.java`) | movement-domain-reviewer | 1 |
| contratto API esterno (`MovementController.java`) | api-contract-reviewer | 1 |
| compliance importi (`TransferRequest.java`) | compliance-amount-reviewer | 1 |
| fuori perimetro (`pom.xml`) | nessuno | 0 |

- Su ognuna delle tre richieste **ne parte uno solo**, e i perimetri sono disgiunti:
  il fatto che sia partito *quel* reviewer e' gia' un'informazione.
- I rilievi dei tre hanno la stessa forma (skill `review-format`): `file`, `riga`,
  `gravita`, `descrizione`, `correzione_proposta` (non applicata).
- Sul file fuori perimetro non si attiva nessuno.

## Nota sui file di log grezzi

`auto-movement.md`, `auto-api.md`, `auto-compliance.md`, `auto-pom.md` sono i log
di sessione grezzi (contengono la riga `... Agent` che prova la delega e l'output
completo). I file `review-*.md` contengono gli stessi findings ripuliti nel solo
formato JSON.
