# Regolamento AML — LipariBank

Fonte: `.opencode/skills/compliance-aml-check/SKILL.md` (i cinque controlli
antiriciclaggio del bootcamp). Questo file e' la copia esposta dal server MCP
come `regolamento://aml-policy`: ogni citazione di una soglia deve venire da
qui, non dalla memoria del modello.

## Soglie operative

| Soglia | Effetto |
|---|---|
| movimenti **sopra 10.000 EUR** | segnalazione |
| movimenti **sopra 5.000 EUR** | registrazione nell'audit |
| movimenti di un **PEP sopra 1.000 EUR** | alert (flag `isPep`) |

## Controlli obbligatori

1. **Soglie operative** — come sopra: 10.000 EUR segnalazione, 5.000 EUR audit.
2. **PEP screening** — flag `isPep` e alert sui movimenti sopra 1.000 EUR.
3. **Watchlist screening** — `watchlistService.screen(fiscalCode)` alla
   creazione di un cliente.
4. **Audit trail** — `correlationId`, `userId`, `ipAddress` ed `executedAt`
   obbligatori su ogni operazione monetaria.
5. **Pattern di operazioni sospette** — smurfing, giri circolari, conti
   dormienti, incoerenza geografica.

## Nota sul server MCP

`finbank-mcp` **non segnala e non registra nulla**: il tool
`simulate_transfer_what_if` si limita a valorizzare `aml.flagged = true` e a
citare questa resource quando l'importo supera 10.000 EUR. La segnalazione
spetta al backend e al processo di compliance, che hanno i campi di audit
(`userId`, `ipAddress`, `correlationId`) che questo server non possiede.
