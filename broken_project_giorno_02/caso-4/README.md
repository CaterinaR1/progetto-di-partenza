# Caso 4

## Sintomo

Il reviewer di sicurezza trova un segreto scritto in chiaro nel codice. Bene: è esattamente il suo mestiere.

Il giorno dopo, l'autore della pull request scrive sul canale del team che qualcuno gli ha toccato il branch. Il segreto non c'è più, al suo posto c'è una variabile d'ambiente, e nella storia non risulta nessuno.

Il rilievo era giusto e la correzione pure. Resta che **una review ha cambiato ciò che stava recensendo**, e da quel momento il report non descrive più il codice che l'autore aveva proposto.
