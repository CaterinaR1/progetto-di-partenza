# Transcript — prompt manuale "quali tool MCP hai" (Giorno 3)

Prova del punto di consegna: *"Prompt manuale 'quali tool MCP hai' lista i 3 tool."*

Comando (sessione OpenCode reale, server `finbank_mcp` registrato in
`.opencode/opencode.json`):

```
set LIPARIBANK_USERNAME=svc_mcp
set LIPARIBANK_PASSWORD=<password utente di servizio, non nel repo>
opencode run "Quali tool MCP hai a disposizione? Elencali tutti con una riga di descrizione ciascuno."
```

Modello: `opencode/big-pickle`. Exit code: 0.

## Risposta del modello

Ho 3 tool MCP del server **finbank**:

- **`finbank_get_account_balance`** — Legge il saldo reale di un conto dal backend LipariBank (sola lettura, account_id 1 o 2).
- **`finbank_list_recent_movements`** — Elenca i movimenti recenti di un conto con limite massimo applicato dal server (max 50).
- **`finbank_simulate_transfer_what_if`** — Simula un bonifico restituendo saldi prima/dopo e esito, senza spostare denaro.

## Nota di verifica (onesta)

Il modello elenca correttamente **3 tool** con descrizioni pertinenti, ma abbrevia
il prefisso del server: scrive `finbank_get_account_balance`. I nomi canonici
**registrati** in OpenCode sono `finbank_mcp_<tool>` (prefisso = nome del server):

- `finbank_mcp_get_account_balance`
- `finbank_mcp_list_recent_movements`
- `finbank_mcp_simulate_transfer_what_if`

I nomi nudi esposti dal server sono `get_account_balance`,
`list_recent_movements`, `simulate_transfer_what_if` (vedi
`inspector-tools-list.json`). La chiamata reale del reviewer di dominio ha usato i
nomi con prefisso `finbank_mcp_` con successo: vedi
`review-test-giorno3-audit.jsonl` e `review-test-giorno3-output.json`.

La discrepanza e' un'imprecisione del modello nel riportare i nomi, non un tool
mancante: l'insieme dei 3 tool e' quello atteso.
