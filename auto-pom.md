opencode.exe : [0m
In C:\Users\Caterina Rando\AppData\Roaming\npm\opencode.ps1:14 car:3
+   & "$basedir/node_modules/opencode-ai/bin/opencode.exe"   $args
+   ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : NotSpecified: ([0m:String) [], RemoteException
    + FullyQualifiedErrorId : NativeCommandError
 
> build ┬À big-pickle
[0m
[0mÔåÆ [0mSkill "review-format"
[0mÔ£▒ [0mGlob "**/pom.xml"[90m 1 match[0m
[0mÔåÆ [0mRead pom.xml
[0mÔ£▒ [0mGrep "Testcontainers|@SpringBootTest|h2|jdbc:h2"[90m in src ┬À 1 match[0m
[0mÔåÆ [0mRead src/test/java/com/lipari/bank/TransferIT.java
[0mÔ£▒ [0mGlob "src/test/resources/**"[90m 0 matches[0m
[0mÔ£▒ [0mGlob "src/main/resources/**"[90m 3 matches[0m
[0mÔåÆ [0mRead src/main/resources/application.yml
```json
[
  {
    "file": "pom.xml",
    "riga": 104,
    "gravita": "HIGH",
    "descrizione": "Manca maven-failsafe-plugin: il test TransferIT (*IT) non rientra negli include di surefire e nessun plugin lo esegue, quindi non viene mai eseguito durante la build.",
    "correzione_proposta": "Aggiungere maven-failsafe-plugin con executions integration-test e verify (oppure rinominare la classe seguendo la convenzione *Test), in modo che venga eseguito almeno con mvn verify."
  },
  {
    "file": "pom.xml",
    "riga": 11,
    "gravita": "HIGH",
    "descrizione": "Spring Boot 3.3.4 ├¿ fuori supporto (EOL): non riceve pi├╣ patch di sicurezza n├® aggiornamenti di dipendenze tramite il parent BOM.",
    "correzione_proposta": "Aggiornare spring-boot-starter-parent all'ultima versione 3.x supportata (es. 3.5.x) e verificare la compatibilit├á di dipendenze e configurazione."
  },
  {
    "file": "pom.xml",
    "riga": 85,
    "gravita": "MEDIUM",
    "descrizione": "org.testcontainers:mysql ├¿ dichiarata con versione hardcoded 1.20.3 e non ├¿ utilizzata da alcun test (nessun @Testcontainers/@Container nel progetto); la versione bypassa la gestione del BOM di Spring Boot.",
    "correzione_proposta": "Scegliere tra: rimuovere la dipendenza, oppure introdurre testcontainers-bom in dependencyManagement allineato al BOM di Spring Boot (rimuovendo la versione hardcoded) e usare davvero Testcontainers nei test."
  },
  {
    "file": "pom.xml",
    "riga": 96,
    "gravita": "MEDIUM",
    "descrizione": "h2 ├¿ dichiarata a scope test ma non esiste alcuna configurazione di profilo test (nessun application-test.yml): TransferIT con @ActiveProfiles(\"test\") ricade su application.yml e si connette a MySQL, rendendo la dipendenza inutilizzata.",
    "correzione_proposta": "Oppure rimuovere h2 e configurare un datasource di test (es. profilo test con Testcontainers o H2), oppure eliminare la dipendenza se i test devono usare MySQL reale."
  },
  {
    "file": "pom.xml",
    "riga": 24,
    "gravita": "LOW",
    "descrizione": "La property jjwt.version fissa manualmente 0.12.6 sovrascrivendo la versione gi├á gestita dal BOM di Spring Boot, con rischio di divergenza in futuri upgrade.",
    "correzione_proposta": "Rimuovere la property jjwt.version e le relative <version> dalle dipendenze jjwt, lasciando che sia il BOM di Spring Boot a gestire la versione."
  },
  {
    "file": "pom.xml",
    "riga": 18,
    "gravita": "LOW",
    "descrizione": "<packaging>jar</packaging> ├¿ ridondante: jar ├¿ il valore di default quando non specificato.",
    "correzione_proposta": "Eliminare l'elemento <packaging> dal POM."
  }
]
```
