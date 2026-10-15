"""Review suite del LipariBank — versione a quattro lenti in parallelo.

Si lancia con il path (file o cartella) da rivedere:

    python code_review_suite.py src/main/java/com/lipari/bank/movement/

Lancia i quattro reviewer del repository CONTEMPORANEAMENTE (non uno dopo l'altro),
raccoglie i loro findings, li riconcilia e scrive `review-report.md` e
`review-report.json`. Il riepilogo per gravita' e' pensato per un cancello sul merge.

Cosa cambia rispetto alla prima versione di Gino (vedi README-GINO.md e il README):
- niente SDK: si appoggia a `.opencode/opencode_query.py` (solo standard library);
- i reviewer partono insieme (asyncio.gather) e non in fila;
- c'e' un tetto di spesa condiviso (token e/o costo) e di tempo, per processo e
  complessivo: superato, la run si ferma davvero (uscita 3);
- i findings vengono deduplicati e, quando due lenti dissentono sulla gravita',
  il dissenso resta scritto (valore di gate = la gravita' piu' alta, divergenza conservata);
- i reviewer vengono lanciati solo se il loro file dichiara `edit: deny`, e a fine run
  si verifica che l'albero revisionato non sia cambiato.

Codici di uscita (per il cancello):
    0  nessun rilievo alla soglia del gate e tutti i reviewer hanno risposto
    1  almeno un rilievo >= soglia, oppure copertura incompleta (reviewer fallito/illeggibile)
    2  errore di configurazione o di sicurezza (target inesistente, --solo non valido,
       codice revisionato modificato durante la review)
    3  tetto di spesa/tempo superato: run interrotta a meta'
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# Su Windows la console e' cp1252 e un semplice print di una freccia o di un
# accento fa esplodere lo script a fine run, dopo che il lavoro e' gia' stato
# fatto: il report c'e' su disco e sembra che sia andato tutto storto.
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass


# --- Il repository e i reviewer -------------------------------------------------

def trova_root_repo(partenza: Path) -> Path:
    """Risale dalla posizione dello script fino alla cartella con `.opencode/opencode.json`."""
    for cartella in [partenza, *partenza.parents]:
        if (cartella / ".opencode" / "opencode.json").is_file():
            return cartella
    raise FileNotFoundError(
        "Non trovo la root del repository (una cartella con .opencode/opencode.json)"
    )


REPO_ROOT = trova_root_repo(Path(__file__).resolve().parent)
sys.path.insert(0, str(REPO_ROOT / ".opencode"))

from opencode_query import ErroreOpenCode, query_opencode  # noqa: E402

# Le quattro lenti: dominio dei movimenti, compliance sugli importi (AML),
# contratto API e prestazioni. Ognuna guarda qualcosa che le altre non guardano.
REVIEWERS = [
    "movement-domain-reviewer",
    "compliance-amount-reviewer",
    "api-contract-reviewer",
    "performance-reviewer",
]

CORRELATION_ID = "review-local"

# UNKNOWN per una gravita' non riconosciuta: vale piu' di CRITICAL, cosi' il cancello
# non scende mai sotto una valutazione di cui non capiamo il valore.
RANGO = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "UNKNOWN": 5}
ORDINE_GRAVITA = ("UNKNOWN", "CRITICAL", "HIGH", "MEDIUM", "LOW")
SINONIMI_GRAVITA = {
    "BLOCKER": "CRITICAL", "CRITICO": "CRITICAL",
    "ERROR": "HIGH", "ERRORE": "HIGH", "ALTA": "HIGH",
    "WARNING": "MEDIUM", "WARN": "MEDIUM", "MEDIA": "MEDIUM",
    "INFO": "LOW", "BASSA": "LOW",
}


class BudgetSuperato(RuntimeError):
    """Il tetto di spesa/tempo condiviso e' stato superato: la run va interrotta."""


@dataclass
class Budget:
    """Il tetto di spesa, condiviso fra i reviewer (un solo contatore)."""
    cap_token: int
    secondi: float
    cap_costo: float = 0.0
    avvio: float = field(default_factory=time.perf_counter)
    token: int = 0
    costo: float = 0.0

    def aggiungi(self, token: int, costo: float) -> None:
        self.token += token
        self.costo += costo

    def secondi_rimasti(self) -> float:
        return self.secondi - (time.perf_counter() - self.avvio)

    def superato(self) -> bool:
        if self.token >= self.cap_token:
            return True
        if self.cap_costo and self.costo >= self.cap_costo:
            return True
        return self.secondi_rimasti() <= 0


@dataclass
class Esito:
    reviewer: str
    stato: str  # "OK" | "FALLITO" | "ILLEGGIBILE"
    testo: str = ""
    findings: list[dict[str, Any]] = field(default_factory=list)
    motivo: str | None = None
    token: int = 0
    costo: float = 0.0
    partenza: str = ""
    t_rel: float = 0.0
    durata: float = 0.0


# --- Lettura dei findings dal testo del reviewer --------------------------------

def _chiave_normalizzata(k: str) -> str:
    """La chiave cosi' com'e', ma riconoscendo le varianti corrotte ('ile' per 'file')."""
    return k.strip().lower()


def _campo(d: dict[str, Any], *prefissi: str, esatti: tuple[str, ...] = ()) -> str | None:
    """Trova il valore di un campo tollerando le chiavi corrotte della skill review-format."""
    for k, v in d.items():
        kn = _chiave_normalizzata(k)
        if kn in esatti or any(kn.startswith(p) for p in prefissi):
            if v is not None:
                return v
    return None


def _estrai_json(testo: str) -> Any | None:
    """Estrae il primo valore JSON utile dal testo (array di findings o oggetto contenitore).

    Scandisce le posizioni di '[' e '{' e prova a decodificare da ciascuna con raw_decode:
    cosi' la prosa con parentesi attorno (link, esempi) non rompe l'estrazione come
    farebbe un taglio dal primo '[' all'ultimo ']'.
    """
    testo = testo.strip()
    if not testo:
        return None
    decodificatore = json.JSONDecoder()
    candidati: list[Any] = []
    for i, ch in enumerate(testo):
        if ch in "[{":
            try:
                valore, _ = decodificatore.raw_decode(testo[i:])
            except json.JSONDecodeError:
                continue
            candidati.append(valore)
    if not candidati:
        return None
    for c in candidati:  # un array e' il contenitore atteso dei findings
        if isinstance(c, list):
            return c
    return candidati[0]


def _lista_findings(dati: Any) -> list[dict[str, Any]] | None:
    """Normalizza in una lista di dict, accettando array o oggetti-contenitore.

    Restituisce None (non interpretabile) se il contenitore e' presente ma non
    contiene alcun finding: un array di stringhe o numeri non e' 'nessun rilievo'.
    """
    if isinstance(dati, list):
        if not dati:
            return []
        if any(isinstance(f, dict) for f in dati):
            return [f for f in dati if isinstance(f, dict)]
        return None
    if isinstance(dati, dict):
        for chiave in dati:
            k = _chiave_normalizzata(chiave)
            if isinstance(dati[chiave], list) and any(
                k.startswith(p) for p in ("findings", "riliev", "results", "issu", "review")
            ):
                return [f for f in dati[chiave] if isinstance(f, dict)]
        # un singolo finding descritto come oggetto
        if _campo(dati, "descriz", "descri") is not None or _campo(dati, "correz", "prop") is not None:
            return [dati]
    return None


def _normalizza_finding(grezzo: dict[str, Any], reviewer: str) -> dict[str, Any]:
    file_ = _campo(grezzo, "file", "ile", esatti=("file", "ile", "percorso", "path"))
    riga = _campo(grezzo, "riga", "iga", "line", esatti=("riga", "iga", "line", "linea"))
    gravita = _campo(grezzo, "grav", "severit", esatti=("gravita", "gravità", "severity"))
    descrizione = _campo(grezzo, "descriz", "descri", esatti=("descrizione", "description"))
    correzione = _campo(
        grezzo, "correz", "prop", esatti=("correzione_proposta", "correzione", "proposed_fix")
    )
    try:
        riga = int(riga) if riga is not None else None
    except (TypeError, ValueError):
        riga = None
    gravita = str(gravita or "").strip().upper()
    gravita = SINONIMI_GRAVITA.get(gravita, gravita)
    if gravita not in RANGO:
        # Gravita' assente o non riconosciuta: NON la declasso a MEDIUM (un CRITICAL
        # scritto male non deve passare il cancello). La marco UNKNOWN, che vale di piu'.
        gravita = "UNKNOWN"
    return {
        "file": str(file_).strip() if file_ is not None else "",
        "riga": riga,
        "gravita": gravita,
        "descrizione": str(descrizione or "").strip(),
        "correzione_proposta": str(correzione or "").strip(),
        "reviewer": reviewer,
    }


def leggi_findings(testo: str, reviewer: str) -> tuple[list[dict[str, Any]], bool]:
    """Restituisce (findings, interpretabile)."""
    dati = _estrai_json(testo)
    if dati is None:
        return [], False
    lista = _lista_findings(dati)
    if lista is None:
        return [], False
    return [_normalizza_finding(f, reviewer) for f in lista], True


# --- Esecuzione di un reviewer --------------------------------------------------

def _tokens(e: dict[str, Any]) -> int:
    t = (e.get("part") or {}).get("tokens") or {}
    if isinstance(t, dict) and t.get("total") is not None:
        return int(t["total"])
    if isinstance(t, dict):
        return int(t.get("input", 0)) + int(t.get("output", 0)) + int(t.get("reasoning", 0))
    return 0


def controlla_sola_lettura(cartella: Path, agente: str) -> str | None:
    """Preflight di sicurezza: il reviewer deve dichiarare `edit: deny`.

    Un file mancante o senza `edit: deny` NON viene lanciato: la 1.18 con un file
    mancante o un frontmatter non chiuso ripiega su `build`, che puo' scrivere.
    Restituisce il motivo del rifiuto, oppure None se il reviewer e' lanciabile.
    """
    percorso = cartella / ".opencode" / "agents" / f"{agente}.md"
    if not percorso.is_file():
        return "file del reviewer mancante: non lanciato"
    frontmatter = percorso.read_text(encoding="utf-8", errors="replace").split("---")
    corpo = frontmatter[1] if len(frontmatter) > 2 else ""
    if not re.search(r"^\s*edit:\s*[\"']?deny[\"']?\s*(#.*)?$", corpo, re.MULTILINE):
        return ("il reviewer non dichiara `edit: deny`: non lo lancio "
                "per non rischiare scritture sul codice recensito")
    return None


async def esegui(reviewer: str, target: str, budget: Budget, tetto_secondi: float) -> Esito:
    """Lancia un reviewer sul target e restituisce findings + consuntivo (non solleva per errori)."""
    esito = Esito(reviewer=reviewer, stato="OK")
    esito.partenza = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    esito.t_rel = time.perf_counter()
    t0 = time.perf_counter()
    prompt = (
        f"Rivedi esclusivamente il seguente target del repository LipariBank: {target}\n"
        "Applica soltanto la tua lente. Non modificare nessun file.\n"
        "Rispondi con il solo array JSON dei findings nel formato della skill review-format "
        "(array vuoto [] se non trovi nulla). Nessun testo prima o dopo l'array."
    )
    tentativi = 3
    for tentativo in range(1, tentativi + 1):
        if budget.superato():
            raise BudgetSuperato()
        pezzi: list[str] = []
        tetto = min(tetto_secondi, max(1.0, budget.secondi_rimasti()))
        generatore = query_opencode(
            prompt, agente=reviewer, cartella=REPO_ROOT, tetto_secondi=tetto
        )
        try:
            async for evento in generatore:
                if budget.superato():
                    raise BudgetSuperato()
                tipo = evento.get("type")
                if tipo == "text":
                    pezzi.append((evento.get("part") or {}).get("text", ""))
                elif tipo == "step_finish":
                    tok = _tokens(evento)
                    costo = float((evento.get("part") or {}).get("cost") or 0)
                    budget.aggiungi(tok, costo)
                    esito.token += tok
                    esito.costo += costo
                    if budget.superato():
                        raise BudgetSuperato()
            esito.testo = "".join(pezzi)
            esito.stato = "OK"
            break
        except BudgetSuperato:
            raise
        except ErroreOpenCode as exc:
            if exc.riprovabile and tentativo < tentativi and not budget.superato():
                attesa = 2 ** tentativo
                print(f"[{reviewer}] errore riprovabile ({exc}); riprovo fra {attesa}s",
                      file=sys.stderr, flush=True)
                await asyncio.sleep(attesa)
                continue
            esito.stato = "FALLITO"
            esito.motivo = str(exc)
            break
        except Exception as exc:  # il reviewer puo' fallire, il report esce lo stesso
            esito.stato = "FALLITO"
            esito.motivo = f"{type(exc).__name__}: {exc}"
            break
        finally:
            # Chiude SEMPRE il generatore: cosi' il suo `finally` ferma il processo figlio
            # anche quando usciamo per eccezione (budget/errore), senza lasciare orfani.
            await generatore.aclose()
    esito.durata = time.perf_counter() - t0
    if esito.stato == "OK":
        findings, interpretabile = leggi_findings(esito.testo, reviewer)
        esito.findings = findings
        if not interpretabile:
            esito.stato = "ILLEGGIBILE"
            esito.motivo = "La risposta non contiene un JSON di findings leggibile"
    return esito


async def esegui_tutti(
    reviewers: list[str], target: str, budget: Budget, tetto_secondi: float
) -> tuple[list[Esito], bool]:
    """Lancia i reviewer insieme. Restituisce (esiti, interrotta_per_budget)."""
    if not reviewers:
        return [], False
    for r in reviewers:
        print(f"[{r}] parto alle {datetime.now().strftime('%H:%M:%S.%f')[:-3]}", flush=True)
    tasks = [asyncio.create_task(esegui(r, target, budget, tetto_secondi)) for r in reviewers]

    # Tetto di tempo complessivo: asyncio.wait con timeout, cosi' anche un reviewer
    # bloccato senza eventi non fa superare il wall-clock cap.
    done, pending = await asyncio.wait(
        tasks, timeout=max(0.0, budget.secondi_rimasti()), return_when=asyncio.FIRST_EXCEPTION
    )
    interrotta = bool(pending) or budget.superato()
    for t in pending:
        t.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)

    esiti = [t.result() for t in tasks if t.done() and not t.cancelled() and t.exception() is None]
    esiti.sort(key=lambda e: e.t_rel)
    return esiti, interrotta


# --- Riconciliazione: dedup + gravita' massima + divergenza conservata -----------

def _descr_norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def _simile(a: str, b: str, soglia: float = 0.34) -> bool:
    """Due descrizioni parlano dello stesso problema? Similarita' di Jaccard sui termini.

    Le lenti diverse descrivono lo stesso difetto con parole diverse (una dice 'N+1',
    l'altra 'query nel ciclo'): la similarita' sui termini li avvicina senza pretendere
    l'uguaglianza, cosi' la deduplica accorpa il difetto e ne fa emergere il dissenso
    sulla gravita', invece di lasciarlo scritto due volte con due giudizi diversi.
    """
    ta = set(_descr_norm(a).split())
    tb = set(_descr_norm(b).split())
    if not ta or not tb:
        return False
    return len(ta & tb) / len(ta | tb) >= soglia


def riconcilia(esiti: list[Esito]) -> list[dict[str, Any]]:
    """Unisce i findings delle quattro lenti.

    Regola: la gravita' del gate e' la MASSIMA fra quelle proposte; ma ogni gravita'
    per lente resta scritta e, se le lenti dissentono, il rilievo viene marcato
    `conflitto: true` con tutte le voci. Cosi' il cancello non scende mai sotto la
    valutazione piu' severa, e la persona vede chi ha dissentito.
    """
    gruppi: list[dict[str, Any]] = []
    for e in esiti:
        for f in e.findings:
            g = next(
                (c for c in gruppi
                 if c["file"] == f["file"] and c["riga"] == f["riga"]
                 and _simile(c["_descr"], f["descrizione"])),
                None,
            )
            if g is None:
                g = {"file": f["file"], "riga": f["riga"], "_descr": f["descrizione"],
                     "descrizioni": [], "correzioni": [], "per_lente": {}, "reviewer": []}
                gruppi.append(g)
            if f["descrizione"] and f["descrizione"] not in g["descrizioni"]:
                g["descrizioni"].append(f["descrizione"])
            if f["correzione_proposta"] and f["correzione_proposta"] not in g["correzioni"]:
                g["correzioni"].append(f["correzione_proposta"])
            if e.reviewer not in g["reviewer"]:
                g["reviewer"].append(e.reviewer)
            # se la stessa lente propone due gravita' diverse, tiene la piu' alta
            prec = g["per_lente"].get(e.reviewer)
            if prec is None or RANGO[f["gravita"]] > RANGO[prec]:
                g["per_lente"][e.reviewer] = f["gravita"]

    riconciliati: list[dict[str, Any]] = []
    for g in gruppi:
        gravita_per_lente = g["per_lente"]
        distinte = set(gravita_per_lente.values())
        gravita_gate = max(distinte, key=lambda s: RANGO[s])
        riconciliati.append({
            "file": g["file"],
            "riga": g["riga"],
            "gravita": gravita_gate,
            "conflitto": len(distinte) > 1,
            "gravita_per_lente": gravita_per_lente,
            "reviewer": g["reviewer"],
            "descrizione": " | ".join(g["descrizioni"]),
            "correzione_proposta": " | ".join(g["correzioni"]),
        })
    riconciliati.sort(key=lambda f: (-RANGO[f["gravita"]], f["file"], f["riga"] or 0))
    return riconciliati


# --- Report ---------------------------------------------------------------------

def _conta(riconciliati: list[dict[str, Any]]) -> dict[str, int]:
    conteggi = {g: 0 for g in ORDINE_GRAVITA}
    for f in riconciliati:
        conteggi[f["gravita"]] += 1
    return conteggi


def _verdetto(riconciliati: list[dict[str, Any]], soglia: str, attesi: list[str],
              esiti: list[Esito], interrotta: bool, mutazione: bool) -> str:
    falliti = [e for e in esiti if e.stato != "OK"]
    severe = any(RANGO[f["gravita"]] >= RANGO[soglia] for f in riconciliati)
    if interrotta:
        return "INTERROTTA (tetto di spesa/tempo superato)"
    if mutazione:
        return "BLOCCATO (il codice recensito e' stato modificato)"
    if severe:
        return f"BLOCCATO (almeno un rilievo >= {soglia})"
    if falliti or len(esiti) != len(attesi):
        return "BLOCCATO (copertura incompleta)"
    return "PASSATO"


def rendi_report_md(
    target: str,
    esiti: list[Esito],
    riconciliati: list[dict[str, Any]],
    budget: Budget,
    soglia: str,
    interrotta: bool,
    durata_tot: float,
    attesi: list[str],
    mutazione: bool = False,
) -> str:
    conteggi = _conta(riconciliati)
    conflitti = [f for f in riconciliati if f["conflitto"]]
    falliti = [e for e in esiti if e.stato != "OK"]
    verdetto = _verdetto(riconciliati, soglia, attesi, esiti, interrotta, mutazione)

    r = [f"# Review di `{target}`", "",
         f"- correlationId: `{CORRELATION_ID}`",
         f"- avvio: {esiti[0].partenza if esiti else '-'}",
         f"- durata totale: {durata_tot:.1f}s",
         f"- spesa: {budget.token}/{budget.cap_token} token, costo {budget.costo:.4f}",
         f"- soglia del gate: {soglia}",
         f"- codice recensito: {'MODIFICATO durante la review' if mutazione else 'non modificato'}",
         f"- esito del gate: **{verdetto}**", ""]

    r += ["## Copertura", "",
          "| Lente | Stato | Partenza | Durata | Token | Findings |",
          "|---|---|---|---|---|---|"]
    for e in esiti:
        r.append(f"| {e.reviewer} | {e.stato} | {e.partenza} | {e.durata:.1f}s | "
                 f"{e.token} | {len(e.findings)} |")
    r.append("")

    r += ["## Riepilogo per gravita' (per il cancello)", ""]
    for g in ORDINE_GRAVITA:
        if conteggi[g] or g != "UNKNOWN":
            r.append(f"- {g}: {conteggi[g]}")
    r.append("")

    r += ["## Findings riconciliati", ""]
    if not riconciliati:
        r.append("_Nessun rilievo._")
    for i, f in enumerate(riconciliati, 1):
        riga = f":{f['riga']}" if f["riga"] else ""
        tag = "  **[CONFLITTO]**" if f["conflitto"] else ""
        r.append(f"### {i}. [{f['gravita']}] {f['file']}{riga}{tag}")
        r.append("")
        r.append(f"- lenti: {', '.join(f['reviewer'])}")
        if f["conflitto"]:
            divergenze = ", ".join(f"{k}={v}" for k, v in f["gravita_per_lente"].items())
            r.append(f"- gravita' per lente: {divergenze} (gate = {f['gravita']})")
        r.append(f"- descrizione: {f['descrizione']}")
        r.append(f"- correzione proposta: {f['correzione_proposta']}")
        r.append("")

    if conflitti:
        r += ["## Divergenze di gravita' conservate", ""]
        for f in conflitti:
            divergenze = ", ".join(f"{k}={v}" for k, v in f["gravita_per_lente"].items())
            r.append(f"- {f['file']}:{f['riga']} -> {divergenze} (gate = {f['gravita']})")
        r.append("")

    if falliti:
        r += ["## Sezioni fallite / illeggibili", ""]
        for e in falliti:
            r.append(f"### {e.reviewer} — {e.stato}")
            r.append("")
            r.append(f"{e.motivo}")
            r.append("")

    return "\n".join(r)


def rendi_report_json(
    target: str,
    esiti: list[Esito],
    riconciliati: list[dict[str, Any]],
    budget: Budget,
    soglia: str,
    interrotta: bool,
    durata_tot: float,
    attesi: list[str],
    mutazione: bool = False,
) -> dict[str, Any]:
    conteggi = _conta(riconciliati)
    verdetto = _verdetto(riconciliati, soglia, attesi, esiti, interrotta, mutazione)
    return {
        "correlationId": CORRELATION_ID,
        "target": target,
        "soglia_gate": soglia,
        "verdetto_gate": verdetto,
        "copertura_completa": not any(e.stato != "OK" for e in esiti) and len(esiti) == len(attesi),
        "interrotta_per_budget": interrotta,
        "codice_modificato": mutazione,
        "durata_totale_s": round(durata_tot, 1),
        "budget": {"token": budget.token, "cap_token": budget.cap_token, "costo": budget.costo},
        "riepilogo_gravita": conteggi,
        "reviewer": [
            {
                "nome": e.reviewer, "stato": e.stato, "partenza": e.partenza,
                "durata_s": round(e.durata, 1), "token": e.token, "costo": e.costo,
                "motivo": e.motivo, "findings": e.findings,
            }
            for e in esiti
        ],
        "findings": riconciliati,
    }


# --- Prologo / main -------------------------------------------------------------

def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Review suite a quattro lenti del LipariBank.")
    p.add_argument("target", nargs="?", default="",
                   help="file o cartella da rivedere (relativo alla root del repo)")
    p.add_argument("--gate", default="HIGH", choices=["CRITICAL", "HIGH", "MEDIUM", "LOW"],
                   help="soglia del cancello: blocca se un rilievo la raggiunge (default HIGH)")
    p.add_argument("--budget-token", type=int, default=500_000,
                   help="tetto di token condiviso: superato, la run si interrompe (default 500000)")
    p.add_argument("--budget-costo", type=float, default=0.0,
                   help="tetto di costo (unita' del provider); 0 = disattivato (default 0)")
    p.add_argument("--budget-secondi", type=float, default=1200,
                   help="tetto di tempo complessivo in secondi (default 1200)")
    p.add_argument("--tetto-secondi", type=float, default=420,
                   help="tetto di tempo per singolo reviewer in secondi (default 420)")
    p.add_argument("--solo", default="", help="lista di reviewer separati da virgola (default: tutti)")
    p.add_argument("--out-dir", default=".", help="dove scrivere i report (default: cartella corrente)")
    p.add_argument("--da-json", default="", metavar="REPORT.json",
                   help="ri-riconcilia un review-report.json esistente SENZA richiamare i reviewer")
    return p.parse_args(argv)


def _impronta(target_path: Path) -> str | None:
    """Impronta dello stato git dei file del target, per accorgersi di modifiche durante la review."""
    try:
        rel = target_path.relative_to(REPO_ROOT)
    except ValueError:
        rel = target_path
    try:
        esito = subprocess.run(
            ["git", "status", "--porcelain", "--", str(rel)],
            cwd=REPO_ROOT, capture_output=True, text=True, check=False,
        )
    except OSError:
        return None
    return esito.stdout if esito.returncode == 0 else None


async def amain(argv: list[str]) -> int:
    args = _parse_args(argv)

    if args.da_json:
        try:
            dati = json.loads(Path(args.da_json).read_text(encoding="utf-8"))
            target = dati["target"]
            esiti = [
                Esito(reviewer=r["nome"], stato=r["stato"],
                      findings=[_normalizza_finding(f, r["nome"]) for f in r.get("findings", [])],
                      motivo=r.get("motivo"), token=r.get("token", 0), costo=r.get("costo", 0.0),
                      partenza=r.get("partenza", ""), durata=r.get("durata_s", 0.0))
                for r in dati["reviewer"]
            ]
        except (OSError, ValueError, KeyError, TypeError) as exc:
            print(f"Report da rileggere non valido: {exc}", file=sys.stderr)
            return 2
        budget = Budget(cap_token=dati["budget"]["cap_token"], secondi=0)
        budget.token = dati["budget"].get("token", 0)
        budget.costo = dati["budget"].get("costo", 0.0)
        interrotta = bool(dati.get("interrotta_per_budget"))
        durata_tot = float(dati.get("durata_totale_s", 0.0))
        mutazione = bool(dati.get("codice_modificato"))
        attesi = [e.reviewer for e in esiti]
    else:
        target = args.target
        if not target:
            print("Serve il target da rivedere (oppure --da-json REPORT.json).", file=sys.stderr)
            return 2
        target_path = (REPO_ROOT / target).resolve() if not Path(target).is_absolute() \
            else Path(target).resolve()
        if not target_path.exists():
            print(f"Target inesistente: {target}", file=sys.stderr)
            return 2

        attesi = [r.strip() for r in args.solo.split(",") if r.strip()] if args.solo else REVIEWERS
        if not attesi or not set(attesi) <= set(REVIEWERS):
            print(f"Reviewer non validi in --solo: usa un sottoinsieme di {REVIEWERS}",
                  file=sys.stderr)
            return 2

        # Preflight: non lancio un reviewer che potrebbe scrivere. Chi non passa il
        # controllo diventa una sezione FALLITO; gli altri consegnano lo stesso.
        da_lanciare: list[str] = []
        esiti = []
        for r in attesi:
            motivo = controlla_sola_lettura(REPO_ROOT, r)
            if motivo:
                print(f"[{r}] {motivo}", file=sys.stderr, flush=True)
                esiti.append(Esito(reviewer=r, stato="FALLITO", motivo=motivo))
            else:
                da_lanciare.append(r)

        budget = Budget(cap_token=args.budget_token, secondi=args.budget_secondi,
                        cap_costo=args.budget_costo)
        impronta_prima = _impronta(target_path)
        t0 = time.perf_counter()
        esiti_run, interrotta = await esegui_tutti(
            da_lanciare, target, budget, args.tetto_secondi
        )
        durata_tot = time.perf_counter() - t0
        if budget.superato():
            interrotta = True
        esiti.extend(esiti_run)
        esiti.sort(key=lambda e: e.t_rel)
        mutazione = impronta_prima is not None and _impronta(target_path) not in (None, impronta_prima)

    riconciliati = riconcilia(esiti)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    testo_md = rendi_report_md(target, esiti, riconciliati, budget, args.gate,
                               interrotta, durata_tot, attesi, mutazione)
    dati_json = rendi_report_json(target, esiti, riconciliati, budget, args.gate,
                                  interrotta, durata_tot, attesi, mutazione)
    (out / "review-report.md").write_text(testo_md, encoding="utf-8")
    (out / "review-report.json").write_text(
        json.dumps(dati_json, ensure_ascii=False, indent=2), encoding="utf-8")
    print(testo_md)

    if interrotta:
        return 3
    if mutazione:
        return 2
    falliti = [e for e in esiti if e.stato != "OK"]
    trova_severe = any(RANGO[f["gravita"]] >= RANGO[args.gate] for f in riconciliati)
    if trova_severe or falliti or len(esiti) != len(attesi):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(amain(sys.argv[1:])))
