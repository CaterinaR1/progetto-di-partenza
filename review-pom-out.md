# Run trace - richiesta fuori da tutti e tre i perimetri

Richiesta (nessun reviewer nominato):

    opencode run "Fai la review di pom.xml (configurazione della build)."

Esito: **nessuno dei tre reviewer specializzati si attiva.**

- movement-domain-reviewer: non parte (pom.xml e' fuori da `com.lipari.bank.movement/**`)
- compliance-amount-reviewer: non parte (nessun importo/saldo/calcolo toccato)
- api-contract-reviewer: non parte (nessun `@RestController` / endpoint `/api/**` / DTO esposto)

Verifica automatica sull'output della sessione: nessun riferimento a
`Movement-Domain-Reviewer Agent`, `Api-Contract-Reviewer Agent` o
`Compliance-Amount-Reviewer Agent`. Il file di build resta fuori dai tre perimetri,
quindi il routing non produce findings specializzati.
