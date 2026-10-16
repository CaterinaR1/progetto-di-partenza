"""finbank-mcp - server MCP sul LipariBank (Giorno 3 del bootcamp).

Tre primitive per tipo:

- TOOL (il modello le invoca, hanno parametri e un costo di calcolo):
  get_account_balance, list_recent_movements, simulate_transfer_what_if.
- RESOURCE (read-only, senza parametri, cambiano solo con un commit):
  regolamento://aml-policy, regolamento://transfer-policy.
- PROMPT: verifica_effetto_bonifico.

Nessun percorso che muove denaro: l'unica POST che questo server emette e'
/api/auth/login, che non modifica dati. Il tool che eseguiva bonifici nella
versione del collega non e' stato portato qui (vedi README, FASE 3).

Identita': l'utente di servizio svc_mcp (credenziali da variabile
d'ambiente), token JWT tenuto in memoria e rinnovato alla scadenza o su 401.
"""

from __future__ import annotations

import json
import os
import sys
import threading
import time
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any

import httpx
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

# --- Configurazione (solo da variabile d'ambiente, nessun segreto nel codice) ---

BASE_URL = os.environ.get("LIPARIBANK_BASE_URL", "http://localhost:8080")
USERNAME = os.environ.get("LIPARIBANK_USERNAME", "svc_mcp")
PASSWORD = os.environ.get("LIPARIBANK_PASSWORD")  # se assente: errore esplicito, mai un default
HTTP_TIMEOUT = float(os.environ.get("FINBANK_HTTP_TIMEOUT", "5"))

TETTO_MOVIMENTI = int(os.environ.get("FINBANK_TETTO_MOVIMENTI", "50"))  # massimo per chiamata
DEFAULT_MOVIMENTI = 10
MAX_TRANSFER = Decimal(os.environ.get("FINBANK_MAX_TRANSFER", "50000"))  # tetto del server MCP
MIN_TRANSFER = Decimal("0.01")  # @DecimalMin di TransferRequest.java
AML_SOGLIA = Decimal("10000")  # soglia AML, citata da regolamento://aml-policy

TOKEN_VITA_SEC = 55 * 60  # il backend scade a 60 min: rinnoviamo un po' prima

AUDIT_FILE = Path(__file__).resolve().parent / "audit" / "invocations.jsonl"
REGOLAMENTO_DIR = Path(__file__).resolve().parent / "regolamento"

CENTESIMI = Decimal("0.01")

mcp = FastMCP("finbank-mcp")


def _log_err(msg: str) -> None:
    """Log su stderr: stdout e' riservato al trasporto stdio di MCP."""
    print(msg, file=sys.stderr, flush=True)


class ErroreBackend(RuntimeError):
    """Il backend non ha risposto come previsto.

    Classe distinta da ToolError perche' la causa e' nel sistema remoto,
    non negli argomenti: in entrambi i casi il modello riceve un errore
    esplicito e mai un dato predefinito.
    """


class ContoInesistente(ErroreBackend):
    """Il backend ha risposto 404: il conto non esiste (e' una risposta, non un guasto)."""


def _audit(tool: str, argomenti: dict[str, Any], esito: str, dettaglio: str = "") -> None:
    """Traccia ogni invocazione: prova che un tool e' stato CHIAMATO, non dedotto."""
    riga = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "tool": tool,
        "argomenti": argomenti,
        "esito": esito,
        "dettaglio": dettaglio[:500],
    }
    try:
        AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)
        with AUDIT_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(riga, ensure_ascii=False) + "\n")
    except OSError as e:  # l'audit non deve mai far fallire la chiamata, ma va avvisato
        _log_err(f"[finbank-mcp] audit non scritto: {e}")


# --- Client del backend -------------------------------------------------------


class BackendClient:
    """Client autenticato verso il LipariBank. Un solo token, in memoria, mai su disco."""

    def __init__(self) -> None:
        self._token: str | None = None
        self._login_at: float = 0.0
        self._lock = threading.Lock()

    def _login(self) -> str:
        if not PASSWORD:
            raise ErroreBackend(
                "LIPARIBANK_PASSWORD non impostata: nessuna credenziale di default viene "
                "usata. Imposta le credenziali di servizio (vedi README FASE 3)."
            )
        try:
            r = httpx.post(
                f"{BASE_URL}/api/auth/login",
                json={"username": USERNAME, "password": PASSWORD},
                timeout=HTTP_TIMEOUT,
            )
        except httpx.HTTPError as e:
            raise ErroreBackend(
                f"login impossibile: backend irraggiungibile su {BASE_URL} "
                f"({type(e).__name__}: {e})"
            ) from e
        if r.status_code != 200:
            raise ErroreBackend(
                f"login rifiutato (HTTP {r.status_code}) per l'utente di servizio "
                f"'{USERNAME}': credenziali non valide. Corpo: {r.text[:200]}"
            )
        try:
            token = r.json()["token"]
        except (ValueError, KeyError, TypeError) as e:
            raise ErroreBackend(
                f"risposta di login senza il campo 'token' (corpo: {r.text[:200]})"
            ) from e
        if not isinstance(token, str) or not token:
            raise ErroreBackend(f"'token' non stringa o vuoto nella risposta di login: {token!r}")
        self._token = token
        self._login_at = time.time()
        return token

    def _token_valido(self) -> bool:
        return self._token is not None and (time.time() - self._login_at) < TOKEN_VITA_SEC

    def get_json(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """GET autenticato. Solleva ErroreBackend/ContoInesistente, mai valori di ripiego."""
        with self._lock:
            token = self._token if self._token_valido() else self._login()

        try:
            r = httpx.get(
                f"{BASE_URL}{path}",
                params=params,
                headers={"Authorization": f"Bearer {token}"},
                timeout=HTTP_TIMEOUT,
            )
        except httpx.TimeoutException as e:
            raise ErroreBackend(
                f"timeout ({HTTP_TIMEOUT}s) su GET {path}: il backend non risponde entro il limite"
            ) from e
        except httpx.HTTPError as e:
            raise ErroreBackend(
                f"backend irraggiungibile su {BASE_URL}{path} ({type(e).__name__}: {e})"
            ) from e

        if r.status_code == 401:
            # Token scaduto o rifiutato: un solo rinnovo, poi errore esplicito.
            with self._lock:
                token = self._login()
            try:
                r = httpx.get(
                    f"{BASE_URL}{path}",
                    params=params,
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=HTTP_TIMEOUT,
                )
            except httpx.HTTPError as e:
                raise ErroreBackend(
                    f"backend irraggiungibile durante il rinnovo del token ({type(e).__name__}: {e})"
                ) from e
            if r.status_code == 401:
                raise ErroreBackend(
                    f"HTTP 401 su GET {path} anche dopo il rinnovo del token: "
                    f"il backend non accetta l'identita' di servizio '{USERNAME}'"
                )

        if r.status_code == 404:
            raise ContoInesistente(f"HTTP 404 su GET {path}: risorsa inesistente")
        if r.status_code >= 400:
            raise ErroreBackend(f"HTTP {r.status_code} su GET {path}: {r.text[:300]}")

        try:
            data = r.json()
        except ValueError as e:
            raise ErroreBackend(f"risposta non-JSON da GET {path}: {r.text[:200]}") from e
        if data is None:
            raise ErroreBackend(
                f"risposta JSON 'null' da GET {path}: nessun dato - errore dichiarato, "
                f"nessun valore predefinito"
            )
        return data


BACKEND = BackendClient()


# --- Helper -------------------------------------------------------------------


def _decimale(testo: Any, campo: str) -> Decimal:
    """Converte un importo in Decimal. Errore esplicito se non e' un numero valido."""
    if isinstance(testo, bool) or testo is None:
        raise ToolError(f"{campo}: atteso un numero decimale, ricevuto {testo!r}")
    if isinstance(testo, Decimal):
        valore = testo
    else:
        try:
            valore = Decimal(str(testo).strip().replace(",", "."))
        except (InvalidOperation, ValueError) as e:
            raise ToolError(
                f"{campo}: importo non valido {testo!r} - atteso un numero "
                f"(es. 150 o '150.00'), non una stringa arbitraria"
            ) from e
    if not valore.is_finite():
        raise ToolError(f"{campo}: importo non finito {testo!r}")
    return valore


def _soldi(v: Decimal) -> str:
    """Due decimali, come stringa: nei soldi non si usano i float."""
    return str(v.quantize(CENTESIMI, rounding=ROUND_HALF_UP))


def _conto_o_errore(account_id: Any, lato: str) -> dict[str, Any]:
    """Legge un conto dal backend. 404 -> ContoInesistente; resto -> ErroreBackend."""
    if isinstance(account_id, bool) or not isinstance(account_id, int):
        try:
            account_id = int(str(account_id))
        except (TypeError, ValueError) as e:
            raise ErroreBackend(f"{lato}: account_id intero atteso, ricevuto {account_id!r}") from e
    if account_id <= 0:
        raise ErroreBackend(f"{lato}: account_id deve essere > 0, ricevuto {account_id}")
    dati = BACKEND.get_json(f"/api/accounts/{account_id}")
    if not isinstance(dati, dict):
        raise ErroreBackend(
            f"{lato}: risposta del backend per l'account {account_id} non e' un oggetto "
            f"(tipo {type(dati).__name__}) - campi attesi mancanti"
        )
    for campo in ("id", "balance"):
        if campo not in dati:
            raise ErroreBackend(
                f"{lato}: risposta del backend priva del campo '{campo}' "
                f"(corpo: {json.dumps(dati)[:200]})"
            )
    try:
        saldo = _decimale(dati["balance"], f"{lato}.balance")
    except ToolError as e:
        raise ErroreBackend(f"{lato}: balance non decodificabile ({e})") from e
    return {
        "account_id": int(dati["id"]),
        "balance": _soldi(saldo),
        "currency": str(dati.get("currency") or "EUR"),
        "status": str(dati.get("status") or "UNKNOWN"),
    }


# --- TOOL 1: saldo reale ------------------------------------------------------


@mcp.tool()
def get_account_balance(account_id: int) -> dict:
    """Legge il saldo REALE di un conto dal backend LipariBank. Sola lettura.

    Quando usarla:
    - per sapere quanto c'e' davvero su un conto, invece di dedurlo dal codice;
    - per verificare un'ipotesi di saldo scritta in una review;
    - come punto di partenza prima di una simulazione di bonifico.

    Non usarla per:
    - spostare o simulare denaro (serve simulate_transfer_what_if);
    - vedere i movimenti di un conto (serve list_recent_movements);
    - cercare un conto per cliente o IBAN: non esiste una ricerca per IBAN.

    Parametri: account_id - intero > 0. Nel database di riferimento esistono
    1 e 2; un id inesistente produce un errore, non un saldo vuoto.

    Ritorna: oggetto con account_id (int), balance (stringa a 2 decimali,
    es. "1000.00"), currency (es. "EUR"), status (es. "ACTIVE"). Nessun altro
    campo del conto (customerId, iban, createdAt) viene esposto.

    Effetti sul sistema: nessuno - solo GET /api/accounts/{id}.

    Errori espliciti (mai un valore predefinito): conto inesistente (404),
    backend irraggiungibile, timeout, credenziali di servizio rifiutate,
    risposta malformata o priva dei campi attesi.
    """
    argomenti = {"account_id": account_id}
    try:
        conto = _conto_o_errore(account_id, "get_account_balance")
    except ToolError as e:
        _audit("get_account_balance", argomenti, "errore", str(e))
        raise
    except ErroreBackend as e:
        _audit("get_account_balance", argomenti, "errore", str(e))
        raise ToolError(str(e)) from e
    _audit("get_account_balance", argomenti, "ok", f"balance={conto['balance']}")
    return conto


# --- TOOL 2: movimenti con tetto lato server ----------------------------------


@mcp.tool()
def list_recent_movements(account_id: int, limit: int = DEFAULT_MOVIMENTI) -> dict:
    """I movimenti piu' recenti di un conto, con TETTO APPLICATO DAL SERVER.

    Quando usarla:
    - per vedere gli ultimi movimenti di un conto quando la review tocca la
      logica che li legge o li produce (buildStatement, transformazioni);
    - per controllare tipo/data/importo/controparte dei movimenti reali.

    Non usarla per:
    - avere l'estratto conto completo: il backend non ha paginazione e qui
    NON si restituisce mai la lista intera;
    - conoscere il saldo (serve get_account_balance);
    - simulare operazioni (serve simulate_transfer_what_if).

    Parametri: account_id (int > 0); limit (int, default 10) = quanti movimenti
    vuoi. Il server accetta da 1 a 50: richieste fuori da questo intervallo
    vengono CLAMPATE (es. limit=999 -> 50), non errore e non lista completa.
    La risposta dichiara limit_richiesto e limit_applicato.

    Ritorna: oggetto con account_id, limit_richiesto, limit_applicato,
    tetto_massimo, count, movements (lista di oggetti con executed_at, type,
    amount a 2 decimali, counterparty_account_id, description).

    Effetti sul sistema: nessuno - solo GET /api/movements?accountId=...

    Errori espliciti: conto inesistente, limit < 1, backend irraggiungibile,
    risposta malformata. Una lista count=0 significa che il backend ha
    risposto 200 con una lista vuota (conto senza movimenti): non e' un
    errore mascherato.
    """
    argomenti = {"account_id": account_id, "limit": limit}
    try:
        if isinstance(limit, bool) or not isinstance(limit, int):
            try:
                limit = int(limit)
            except (TypeError, ValueError) as e:
                raise ToolError(f"limit: intero atteso, ricevuto {limit!r}") from e
        if limit < 1:
            raise ToolError(
                f"limit: deve essere >= 1 (richiesto {limit}). Il server non restituisce "
                f"liste vuote per argomenti fuori intervallo: correggi il parametro."
            )
        limit_richiesto = limit
        limit_applicato = min(limit, TETTO_MOVIMENTI)

        conto = _conto_o_errore(account_id, "list_recent_movements")
        dati = BACKEND.get_json("/api/movements", params={"accountId": conto["account_id"]})
        if not isinstance(dati, list):
            raise ErroreBackend(
                f"list_recent_movements: attesa una lista di movimenti, ricevuto "
                f"{type(dati).__name__}"
            )

        movimenti = []
        for m in dati[:limit_applicato]:
            if not isinstance(m, dict) or "amount" not in m or "type" not in m:
                raise ErroreBackend(
                    f"list_recent_movements: movimento privo dei campi attesi: "
                    f"{json.dumps(m)[:200]}"
                )
            movimenti.append(
                {
                    "executed_at": m.get("executed_at"),
                    "type": m.get("type"),
                    "amount": _soldi(_decimale(m["amount"], "movements[].amount")),
                    "counterparty_account_id": m.get("counterparty_account_id"),
                    "description": m.get("description"),
                }
            )
    except ToolError as e:
        _audit("list_recent_movements", argomenti, "errore", str(e))
        raise
    except ErroreBackend as e:
        _audit("list_recent_movements", argomenti, "errore", str(e))
        raise ToolError(str(e)) from e

    esito = {
        "account_id": conto["account_id"],
        "limit_richiesto": limit_richiesto,
        "limit_applicato": limit_applicato,
        "tetto_massimo": TETTO_MOVIMENTI,
        "count": len(movimenti),
        "movimenti_totali_a_backend": len(dati),
        "movimenti": movimenti,
    }
    _audit(
        "list_recent_movements",
        argomenti,
        "ok",
        f"restituiti {len(movimenti)} di {len(dati)} (tetto {TETTO_MOVIMENTI})",
    )
    return esito


# --- TOOL 3: simulazione what-if ---------------------------------------------


@mcp.tool()
def simulate_transfer_what_if(
    source_account_id: int, target_account_id: int, amount: Any
) -> dict:
    """Simula un bonifico e ritorna i saldi PRIMA e DOPO. NON muove nessun denaro.

    Quando usarla:
    - per vedere cosa succederebbe davvero a spostare una somma fra due conti;
    - in una review che tocca la logica dei movimenti, per verificare che
      l'operazione che il codice descrive reggerebbe (o fallirebbe) sui dati reali.

    Non usarla per:
    - ESEGUIRE un bonifico: questo tool non ha nessun effetto sul sistema, non
      esiste nessun percorso in questo server che modifichi un saldo;
    - conti di cui non conosci l'id (nessuna ricerca per IBAN cliente).

    Parametri: source_account_id, target_account_id (int > 0, diversi fra loro);
    amount (numero o stringa decimale, es. 150 o '150.00').

    Ritorna: oggetto con amount, before/after (saldi delle due parti,
    stringhe a 2 decimali), would_succeed (bool), reasons (lista di motivi,
    con i numeri reali letti dal backend), aml (flag + soglia + uri della
    policy citata, quando amount >= 10000), system_changed: false e
    resources_cited (gli uri delle resource che il regolamento detta).

    Effetti sul sistema: NESSUNO. Legge due saldi con GET e calcola in
    memoria. Prima e dopo sono una previsione, non uno stato scritto.

    Errori espliciti: amount <= 0 o amount > MAX_TRANSFER (tetto del server,
    default 50000) -> errore sugli argomenti; conto irraggiungibile o
    risposta malformata -> errore del backend. Un'operazione che il backend
    NON accetterebbe (conto sorgente/destinazione inesistente, stesso conto,
    fondi insufficienti, amount < 0.01) ritorna would_succeed: false con il
    motivo, non un errore: quella e' proprio la risposta che serve.
    """
    argomenti = {
        "source_account_id": source_account_id,
        "target_account_id": target_account_id,
        "amount": str(amount),
    }
    try:
        importo = _decimale(amount, "amount")
        if importo <= 0:
            raise ToolError(
                f"amount: deve essere > 0, ricevuto {_soldi(importo)} - "
                f"un bonifico di zero o negativo non e' simulabile"
            )
        if importo > MAX_TRANSFER:
            raise ToolError(
                f"amount: {_soldi(importo)} supera il tetto del server MCP "
                f"({ _soldi(MAX_TRANSFER) }): simulazione rifiutata, nessun dato inventato"
            )

        motivi: list[str] = []
        system_changed = False

        src = tgt = None
        try:
            src = _conto_o_errore(source_account_id, "simulate.source")
        except ContoInesistente:
            motivi.append(
                f"il conto sorgente {source_account_id} non esiste nel backend (404): "
                f"il bonifico sarebbe rifiutato"
            )
        try:
            tgt = _conto_o_errore(target_account_id, "simulate.target")
        except ContoInesistente:
            motivi.append(
                f"il conto destinazione {target_account_id} non esiste nel backend (404): "
                f"il bonifico sarebbe rifiutato"
            )

        if source_account_id == target_account_id:
            motivi.append(
                "sorgente e destinazione coincidono: MovementService.transfer() rifiuta "
                "l'operazione (MovementService.java:27)"
            )

        if importo < MIN_TRANSFER:
            motivi.append(
                f"importo {_soldi(importo)} inferiore al minimo di "
                f"{_soldi(MIN_TRANSFER)} (TransferRequest @DecimalMin)"
            )

        if src is not None and tgt is not None and not motivi:
            saldo_src = _decimale(src["balance"], "saldo sorgente")
            saldo_tgt = _decimale(tgt["balance"], "saldo destinazione")
            if saldo_src < importo:
                motivi.append(
                    f"fondi insufficienti: saldo sorgente {_soldi(saldo_src)} < "
                    f"importo {_soldi(importo)} (MovementService.java:36-38)"
                )

        would_succeed = not motivi

        def _prima(c: dict[str, Any] | None) -> dict[str, Any] | None:
            if c is None:
                return None
            return {"account_id": c["account_id"], "balance": c["balance"], "currency": c["currency"]}

        before = {"source": _prima(src), "target": _prima(tgt)}
        if would_succeed:
            saldo_src = _decimale(src["balance"], "saldo sorgente") - importo
            saldo_tgt = _decimale(tgt["balance"], "saldo destinazione") + importo
            after = {
                "source": {**before["source"], "balance": _soldi(saldo_src)},
                "target": {**before["target"], "balance": _soldi(saldo_tgt)},
            }
        else:
            # Nessun successo -> nessuna proiezione: prima == dopo, nulla cambia.
            after = before

        aml: dict[str, Any] = {"flagged": False}
        if importo >= AML_SOGLIA:
            aml = {
                "flagged": True,
                "soglia": _soldi(AML_SOGLIA),
                "note": (
                    "importo oltre soglia AML: questa simulazione NON segnala nulla "
                    "nessun campo viene scritto - la segnalazione spetta al backend/"
                    "al processo di compliance"
                ),
                "policy": "regolamento://aml-policy",
            }

        risposta = {
            "source_account_id": source_account_id,
            "target_account_id": target_account_id,
            "amount": _soldi(importo),
            "before": before,
            "after": after,
            "would_succeed": would_succeed,
            "reasons": motivi,
            "aml": aml,
            "system_changed": system_changed,
            "resources_cited": ["regolamento://transfer-policy"]
            + (["regolamento://aml-policy"] if importo >= AML_SOGLIA else []),
        }
    except ToolError as e:
        _audit("simulate_transfer_what_if", argomenti, "errore", str(e))
        raise
    except ErroreBackend as e:
        _audit("simulate_transfer_what_if", argomenti, "errore", str(e))
        raise ToolError(str(e)) from e

    _audit(
        "simulate_transfer_what_if",
        argomenti,
        "ok",
        f"would_succeed={would_succeed} reasons={len(motivi)}",
    )
    return risposta


# --- RESOURCE: i regolamenti, letti da disco a ogni read ----------------------


def _leggi_regolamento(nome_file: str) -> str:
    """Legge il regolamento dal disco: la fonte e' il file, non la memoria del modello."""
    percorso = REGOLAMENTO_DIR / nome_file
    try:
        testo = percorso.read_text(encoding="utf-8")
    except OSError as e:
        raise RuntimeError(
            f"regolamento non leggibile ({percorso}): {e} - nessun testo di ripiego"
        ) from e
    if not testo.strip():
        raise RuntimeError(f"regolamento vuoto ({percorso}): rifiutato, non viene tornato vuoto")
    return testo


@mcp.resource("regolamento://aml-policy", mime_type="text/markdown")
def _resource_aml_policy() -> str:
    """Regolamento AML del LipariBank: soglie di segnalazione e audit.

    Lettura dal file finbank-mcp/regolamento/aml-policy.md a ogni richiesta.
    Fonte unica per citare le soglie: non ricordarle a memoria.
    """
    return _leggi_regolamento("aml-policy.md")


@mcp.resource("regolamento://transfer-policy", mime_type="text/markdown")
def _resource_transfer_policy() -> str:
    """Regole operative di un bonifico: minimo, tetto del server MCP, invarianze.

    Lettura dal file finbank-mcp/regolamento/transfer-policy.md a ogni richiesta.
    """
    return _leggi_regolamento("transfer-policy.md")


# --- PROMPT: la sequenza che la compliance chiede ------------------------------


@mcp.prompt(name="verifica_effetto_bonifico")
def verifica_effetto_bonifico(source_account_id: int, target_account_id: int, amount: str) -> str:
    """Verifica cosa succederebbe a un bonifico, con dati reali e citazione del regolamento.

    Compilato con due account e un importo, prepara il flusso completo:
    regolamento -> saldi reali -> simulazione -> esito senza modifiche.
    """
    return f"""Verifica l'effetto reale di un bonifico di {amount} dal conto {source_account_id}
al conto {target_account_id}, senza modificare nulla al sistema.

Segui ESATTAMENTE questa sequenza:

1. Leggi il regolamento PRIMA di calcolare: usa list_mcp_resources e
   read_mcp_resource sulle resource "regolamento://transfer-policy" e
   "regolamento://aml-policy". Le soglie e le regole vanno CITATE dalla
   resource letta, mai ricordate a memoria.

2. Leggi i saldi reali con get_account_balance sui due conti. Se un tool
   restituisce un errore, riporta l'errore testuale: non dedurre nessun
   numero al suo posto.

3. Simula con simulate_transfer_what_if (source={source_account_id},
   target={target_account_id}, amount={amount}).

4. Riporta: tabella saldi PRIMA / DOPO, would_succeed, e se e' false il
   motivo con i numeri reali. Chiudi con la frase esplicita:
   "Nessuna modifica e' stata applicata al sistema: la simulazione non
   muove denaro" (il campo system_changed: false lo conferma).

5. Se amount >= 10000 o l'esito e' negativo, cita la regola dalla resource
   letta (uri + frase chiave), non dalla tua memoria.

NON usare questo flusso per eseguire un bonifico: non esiste nessun tool
che muova denaro in questo server."""


if __name__ == "__main__":
    # stdio: nessun print su stdout, il server resta in ascolto in silenzio.
    mcp.run()

