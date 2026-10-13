# Caso 4

## Sintomo

Chiedi una verifica di conformità su un cambiamento che tocca il denaro. La verifica parte, trova due cose che non vanno — e te le presenta **già sistemate**.

Nessuno gliel'ha chiesto. E il problema non è che abbia corretto male: è che il rapporto di conformità ora descrive un codice diverso da quello che era stato proposto, e chi lo legge non ha modo di saperlo.

## Come riprodurlo

1. Metti il file di `BUGGY/` in `.claude/skills/compliance-aml-check/SKILL.md`.
2. Apri `claude` e chiedi una verifica di conformità su un file che tocca gli importi.
3. Alla fine controlla `git status` e `git diff`.

Se il working tree è cambiato, la verifica non era una verifica.
