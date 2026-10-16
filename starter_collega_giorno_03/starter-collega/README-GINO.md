# Note di Gino — il server MCP sul FinBank, primo tentativo

Mi hanno detto di provare a esporre qualche dato del LipariBank come server MCP.
**Gira, Inspector lo vede e i tool rispondono**: gli chiedo il saldo di un conto e
il saldo torna.

## Cosa ho fatto

- `server.py` — il server con FastMCP. Due tool: uno legge il saldo di un conto,
  l'altro fa un bonifico.
- `run.sh` — lo script con cui lo avvio, cosi' me lo ricordo.
- `pyproject.toml` — le dipendenze.

## Come si prova

```bash
cd starter-collega
uv sync
./run.sh
# da un altro terminale:
npx @modelcontextprotocol/inspector
# poi in Inspector: connect a http://localhost:8765, e prova get_balance
```

## Cose che non ho fatto, e dubbi miei

- **Dall'assistente non parte da solo.** In Inspector i tool rispondono, ma quando
  chiedo a Claude «quanto c'e' sul conto 42» spesso non lo usa e mi risponde che
  non ha accesso ai dati. Se glielo dico esplicitamente va. Non ho capito perche'.
- **Il bonifico l'ho messo perche' ci stava.** Funziona: l'ho provato una volta con
  il conto di test e i soldi si sono mossi davvero. Poi mi e' venuto un dubbio e
  non l'ho piu' toccato, ma l'ho lasciato li'.
- **L'ho aperto su tutte le interfacce** per provarlo dal portatile del collega. In
  ufficio funziona.
- Non ho messo niente sui documenti di policy: quelli si leggono dal repository e
  non ho capito se avrei dovuto esporli anche da qui.
- I tipi degli argomenti li ho tenuti larghi, cosi' non davano errore.

Se trovate cose da sistemare ditemelo, cosi' imparo.
