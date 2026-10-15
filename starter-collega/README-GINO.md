# Note di Gino — il controllo sulle review, prima versione

Ciao! Il responsabile mi aveva chiesto di provare a mettere in piedi il controllo
automatico sulle PR dei movimenti, e ci ho passato un pomeriggio. Non e' finito e
non sono sicuro di tutto, ma **parte e funziona**: gli chiedo una review di un file
di `domain/movement` e i rilievi escono.

## Cosa ho fatto

- `.claude/agents/code-reviewer.md` — il reviewer. Ha la checklist di dominio che
  mi sono fatto dare dal collega senior: transazioni atomiche, idempotency, importi
  in `BigDecimal`, BCrypt, JWT, audit trail, N+1.
- `.claude/skills/compliance-aml-check/SKILL.md` — la skill con i cinque controlli
  antiriciclaggio. Si attiva quando il discorso tocca soglie, PEP o watchlist.
- `.claude/settings.json` + `.claude/scripts/log-tool.py` — un hook che scrive su
  un file di log ogni volta che viene usato uno strumento. Mi serviva per capire
  cosa stava succedendo. All'inizio l'avevo messo tutto dentro il `settings.json`
  su una riga sola, poi non ci capivo piu' niente e l'ho spostato in uno script.

## Come si prova

Dalla radice del repository del LipariBank, con Claude Code gia' installato:

```bash
cp -r starter-collega/.claude .          # se .claude non c'e' ancora
claude
> fammi la review di src/main/java/it/lipari/bank/domain/movement/MovementService.java
```

I rilievi escono in JSON con severity, file e riga. L'ho provato su tre file di
`domain/movement` e su due di `domain/account`, e le cose che ha trovato erano
vere — una l'aveva mancata anche la review umana della settimana prima.

## Cose che non ho fatto, e dubbi miei

- **A volte devo dirgli io di usarlo.** Se scrivo «review questo file» ogni tanto
  la review me la fa lui nella chat normale invece di passare dal reviewer. Non ho
  capito da cosa dipende. Quando succede glielo dico esplicitamente e va.
- **Il log e' diventato enorme.** Ci finisce dentro tutto, anche le letture di file
  che non c'entrano niente. Volevo tenerne solo un pezzo ma non ho trovato come.
- **Una volta mi ha riscritto un file** mentre gli avevo chiesto solo di guardarlo.
  Gli avevo detto «review e sistema quello che puoi», quindi forse e' colpa mia di
  come gliel'ho chiesto.
- Non ho provato cosa succede se il file di log non e' scrivibile. Sul mio portatile
  lo e'.
- L'ho fatto solo per i movimenti. Per gli importi e per le API verso l'esterno non
  ho toccato niente: mi sembrava che bastasse allargare la descrizione di questo,
  ma non ho avuto tempo di provarci.

Se trovate cose da sistemare ditemelo, cosi' imparo.
