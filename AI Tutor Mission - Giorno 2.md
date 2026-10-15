Ruolo: sei un tech lead senior che intervista per ruolo "AI Agentic Engineer" in banca italiana.
Il candidato dichiara di aver costruito un framework multi-agentico custom per code review.

Fase 1 (10 min) — Cosa hai costruito
- Quanti subagent? Quali dimensioni di expertise?
Risposta: Ho implementato 3 reviewer subagent, con tre dimensioni di expeties divise per cartella/tipo di cambiamento e divise tra loro. La scelta della suddivisione è stata dettata dal fatto che mattano tre faileure  mode indipendenti così un errore in uno dei tre è risulta invisibile per gli altri due
- Come orchestri? Parallelo o sequenziale?
Risposta: Ho implementato 3 reviewer subagent, con tre dimensioni di expeties divise per cartella/tipo di cambiamento e divise tra loro. La scelta della suddivisione è stata dettata dal fatto che mattano tre faileure  mode indipendenti così un errore in uno dei tre è risulta invisibile per gli altri due. Se decidessimo di orchestrare più reviewer sullo stesso bersaglio allora bisognerebbe attuare la sequenziale
- Tempo medio di un run? Token medi? Cost medio?
Risposta: Le run dei tre reviewer sono durate in media circa 75 secondi (mediana 47 s), con una variabilità ampia: dai 13 secondi di una review su un file singolo ai 220 s di una run che legge più file. I token tipici sono intorno ai 16.000 in ingresso e 2.200 in uscita, più circa 2.200 di reasoning. Il costo medio di circa $1,72 con Sonnet 5.5

Fase 2 (10 min) — Decisioni architetturali
- Perché Claude Agent SDK e non LangGraph?
Risposta: Il Claude Agent SDK è verticale: risparmia il loop e l'infrastruttura poiché pensato per Claude quindi ottimo quando il problema è reaction-based e piccolo.
LangGraph è orizzontale: un motore generico per workflow con stato, cicli, ramificazioni, persistenza e approvazioni. Ottimo quando il flusso è complesso e deve essere affidabile/riavviabile.
La differenza chiave è chi controlla il flusso: nel SDK lo decide il modello, in LangGraph lo decidiamo noi, il modello è solo uno dei nodi.
Non sono esclusivi: una run del SDK può essere un nodo dentro un grafo LangGraph.
- Perché 4 subagent e non 10?
Risposta: 3 reviewer specialistici: movimenti, importi/AML, contratto API. Più 1 subagent di test. Il 4 non è un numero arbitrario: è il numero di perimetri ortogonali del problema. I tre confini non si sovrappongono, quindi ogni richiesta ha un solo "capo", 3 agenti con confini netti vincono su 10 agenti che andrebbero in conflitto tra loro. Prompt, permessi e formato vanno tenuti allineati alla skill. 10 agenti avrebbero senso solo se esistessero davvero 10 attori con perimetri disgiunti, permessi diversi e output indipendenti, team, vendor o responsabilità realmente separati.
- Come gestisci context window quando i subagent producono output prolisso?
Risposta: Delego lavori grezzi a subagent così ognuno ha la propria sessione figlio, il loro output prolisso resta lì, nella sessione parent arriva solo il messaggio finale. Poi nel prompt del Task chiedo esplicitamente una risposta sintetica e se il contesto si satura, il subagent compaction riassume automaticamente. Mentre per i reviewer configured con steps limitati vengono forzati a concludere con una sintesi.

Fase 3 (5 min) — Edge cases
- Cosa succede se un subagent va in loop?
Risposta: Se un subagent sembra bloccato in un loop, possiamo eseguire la rilevazione doom loop genera automaticamente prompt di recupero che spingono l'agente a cambiare strategia o concludere oppure attuare l'opzione steps impostata, al superamento del limite l'agente è forzato a rispondere con un riepilogo testuale del lavoro svolto; l'utente può sempre interrompere manualmente il task e riprenderlo in seguito. Senza alcun limite, il subagent continua a iterare finché il modello non decide di fermarsi o non lo interrompiamo.
- Cosa succede se l'AI inventa findings (hallucination)?
Risposta: Se i reviewer NON fossero in sola lettura (cioè con edit/bash abilitati), l'hallucination diventerebbe attiva e pericolosa. In un contesto bancario questo è critico: una "correzione" allucinata potrebbe rimuovere una validazione, allentare una soglia o manomettere un calcolo, con impatto su conformità e integrità finanziaria. Il rischio sarebbe amplificato dal fatto che i reviewer applicherebbero le modifiche in autonomia, senza un passaggio di verifica umana, rendendo difficile distinguere un fix legittimo da un danno generato da un finding inventato. Con write access servono quindi guardrail obbligatori: evidenza verbatim a supporto di ogni finding, verifica di esistenza di file/riga, applicazione solo dopo revisione/conferma e isolamento su branch con test automatici prima del merge.
- Come testi un framework multi-agent in CI?
Risposta: non testiamo l'output del modello specie se non deterministico. Testiamo l'involucro deterministico attorno agli agenti quindi budget, concorrenza, limiti di tempo, non-mutazione, formato, routing e questo lo sii fa con un runner finto 

Fase 4 (5 min) — Apertura
- Cosa NON sai fare ancora? Cosa imparerai nei prossimi 30 giorni?
Risposta: Quello che non so ancora fare è valutare un sistema non deterministico: so scrivere un reviewer, ma non so ancora metterne sotto test il comportamento routing, budget, non-mutazione così che la CI lo verifichi a ogni PR.  Nei prossimi 30 giorni vorrei trasformare gli otto casi rotti in altrettanti invarianti di CI e imparare a osservare costo e tempo per run invece di scoprirli in fattura.
- Hai mai pensato di esporre il framework come API per il team?
Risposta: Esponiamo i tre reviewer come un servizio di review interno. Il team fa POST con il target e il concern, riceve un jobId e poi ritira i findings nel formato review-format: così il controllo parte sempre, invece di dipendere da chi si ricorda di lanciare opencode run. La scelta chiave è renderla asincrona: le review durano minuti, quindi una POST sincrona si schianterebbe sui timeout sarebbe meglio coda più polling. 

Per ogni risposta, assegna un punteggio:
- **0** = non risposta o palesemente errata
- **1** = risposta vaga / generica / "ho letto"
- **2** = risposta concreta con esempio dal proprio codice
- **3** = risposta da senior — concreto + motivato + con un *trade-off* esplicito o un anti-pattern citato

| Fase | Domanda | Punti (0-3) | Note |
|---|---|:-:|---|
| 1 | D1.1  |  | 2 |
| 1 | D1.2  |  | 2 |
| 1 | D1.3  |  |   | 3
| 2 | D2.1  |  |   | 3
| 2 | D2.2  |  | 2 |
| 2 | D2.3  |  | 2 |
| 3 | D3.1  |  | 2 |
| 3 | D3.2  |  | 2 |
| 4 | D4.1  |  | 2 | 3
| 4 | D4.2  |  |  | 3
| **Totale (max 33)** |  | **_26_ / 33** |  |

Regole: non rispondi tu. Premi se vago. A fine, feedback + livello.