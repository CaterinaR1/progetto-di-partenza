> Scrivi le tue risposte sotto ogni domanda. 2-5 frasi per risposta — risposta da senior in 30-60 secondi a colloquio reale.
> A fine, applica la rubrica di auto-valutazione e annota il livello (junior/mid/senior) + 1 paragrafo di feedback a te stesso.

## Fase 1 — Cosa hai costruito (target 10 min)

**D1.1** — Dimmi come hai separato i tre reviewer. Qual è la regola, e chi vince quando due la rivendicano?
Risposta: ho separato i retriever in codice, documentazione e risorse esterne. Per quanto riguarda il frontmatter ho creato un yaml definendo le descrizioni di routnig e i vincoli di attivazione espliciti. In merito alla regola delle sovrapposizioni l'importante è definire dei confini chiari per ogni tipo di risorsa inserendo istruzioni negative. Se vi emergono responsabilità per lo stesso problema allora l'orchestratore esegue un fallback con risposte finali per entrambi

**D1.2** — Cosa fa, esattamente?

Risposta: Un subagent è un assistente specializzato e definito come file md con yaml frontmatter e viene attivato quandoprende il controllo del task tramite un proprio system prompt o un proprio modello e lo troviamo dentro /agents

**D1.3** — Quando viene invocato? (Routing automatico? Slash command? Esplicito via Task tool?)

Risposta: il subagent viene invocato nel momento in cui prende il controllo per task attraverso un proprio system prompt o un proprio modello

## Fase 2 — Perché quelle scelte (target 10 min)

**D2.1** — Perché Read+Grep+Glob+Bash e non Edit nelle tools?

Risposta: Sono dei tools, e sono tutti strumenti di sola lettura quindi escludiamo il tool edit perchè il retriever ha il compito di recuperare dati non di scrivere codice

**D2.2** — Perché Sonnet e non Opus?

Risposta: Sonnet è meno costoso, tempo di latenza minore, precisione maggiore nell'eseguire istruzioni strutturate mentre Opus è più costoso con un maggiore tempo di latenza

**D2.3** — Cosa scriveresti diversamente nel system prompt se riguardando il codice ora?

Risposta: Aggiungerei uno schema di output in formato json o a blocchi così da avere un output con dati puliti, esplicitare degli esempi così da rendere il prompt più comprensibile, fornire delle soglie massime per il numero di ricerche così da limitare le spese, queste "tecniche" vengono utilizzate in modo da ridurre tempi di latenza e ottimizzare il contesto fornito all'orchestratore

## Fase 3 — Scenari edge (target 5 min)

**D3.1** — Il routing automatico non funziona — il subagent non viene mai invocato. Cosa controlli?

Risposta: controllo nel frontmatter per verificare che vi siano le corrette e sufficient keyword , verificare i path forniti che siano corretti, verificare la formattazione del frontmatter in quanto potrebbero e sserci degli errori, inserire degli esempi così da rendere il prompt più comprensibile

**D3.2** — Il subagent funziona ma le review sono troppo generiche. Cosa cambi?

Risposta: aggiungere degli esempi così da fornire un contesto più chiaro, inserire dei riferimenti puntuali, magari potremmo aggiungere delle bounding box così da fornire le coordinate esatte dei dati che si vogliono leggere.

## Fase 4 — Apertura (target 5 min)

**D4.1** — Differenza subagent vs skill vs slash command per te?

Risposta: subagent: agente autonomo specializzato definito come file markdown con yaml frontmatter che viene attivato quando prende il controllo del task attraverso il proprio system prompt
skill: è un manuale caricato nel contesto è la conoscena/procedura riutilizzabile
slash command: comandi rapidi d'interfaccia invocati dall'utente per avviare un'azione predefinita

**D4.2** — Cosa hai pensato di Superpowers come asset framework?

Risposta: è un framework di skill che permette di estendere le capacità di Claude, trasforma le procedure ripetitive in linee guida riutilizzabili r oyyimizza l'uso dei token caricando le capacità solo quando è necessario

**D4.3** — Cosa NON sai ancora fare in Claude Code? (onestà metacognitiva)

Risposta: Non posso sscrivere o aggiornare file direttamente sul compute dell'utente, non posso eseguire script su ambiente in sandbox, non posso interagire con dispositivi fisici o esterni al sandbox sicuro

---

## Rubrica auto-valutazione (compila a fine)

Per ogni risposta, assegna un punteggio:
- **0** = non risposta o palesemente errata
- **1** = risposta vaga / generica / "ho letto"
- **2** = risposta concreta con esempio dal proprio codice
- **3** = risposta da senior — concreto + motivato + con un *trade-off* esplicito o un anti-pattern citato

| Fase | Domanda | Punti (0-3) | Note |
|---|---|:-:|---|
| 1 | D1.1 frontmatter | 1 |  |
| 1 | D1.2 cosa fa | 1 |  |
| 1 | D1.3 invocazione | 1 |  |
| 2 | D2.1 tools | 1 |  |
| 2 | D2.2 modello | 1 |  |
| 2 | D2.3 retrospettiva prompt |  | 2 |
| 3 | D3.1 routing rotto |  | 2 |
| 3 | D3.2 review generiche | 1 |  |
| 4 | D4.1 distinzione |  | 2 |
| 4 | D4.2 Superpowers | 1 |  |
| 4 | D4.3 onestà metacognitiva | 1 |  |
| **Totale (max 33)** |  | **_14__ / 33** |  |

**Livello indicativo**:
- **0-11** → junior — rivedere il Giorno 1 da zero, ripartendo dalle pagine *Subagent — l'assistente specializzato che vive nel repo* e *Skill — il manuale operativo (e quando usare cosa)* del Deep Dive
- **12-22** → mid — il bootcamp è andato, ma manca consolidamento. Rifare Project Work G1 dopo 7 giorni di pratica autonoma
- **23-30** → senior funzionale — pronto per il G2
- **31-33** → senior con postura Lipari-mature — pronto per il delivery cliente

**Feedback a te stesso** (1 paragrafo, ~80 parole):
Aggiungere degli esempi così da mostrare più padronanza dei concetti elencati, riguarderei i concetti più importanti e fondamentali così da farli più miei ed esprimerli in modo più chiaro.