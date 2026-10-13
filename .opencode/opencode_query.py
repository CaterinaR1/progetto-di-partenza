"""opencode_query.py — il posto di query() dell'SDK, per chi lavora con OpenCode.

Il Claude Agent SDK dà `query()`, un generatore asincrono che restituisce i messaggi di una
sessione. Per OpenCode un SDK così non c'è: questo file fa la stessa parte lanciando un
processo `opencode run --agent <nome> --format json` e restituendo, uno per volta, gli
eventi che OpenCode scrive (una riga JSON per evento). Nient'altro: leggere il testo,
contare token e costo, estrarre i findings resta a chi lo usa, come con l'SDK.

    async for evento in query_opencode(prompt, agente="security-reviewer"):
        ...   # evento è un dict: evento["type"] è "text", "tool_use", "step_finish", ...

Gli eventi che contano:
- "text"        → evento["part"]["text"], un pezzo della risposta del reviewer;
- "step_finish" → evento["part"]["tokens"] (input, output, reasoning, cache.read) e
                  evento["part"]["cost"]: un passo dell'agente, il consuntivo si somma;
- "error"       → non arriva a te: diventa un'eccezione ErroreOpenCode, come un errore
                  dell'SDK, con lo stato HTTP e se ha senso riprovare.

Tre cose che fa per te, perché senza si perde un pomeriggio:
1. il prompt passa su stdin, che poi si chiude: `opencode run` legge stdin quando non è un
   terminale, e se resta aperto aspetta per sempre. Su Windows evita anche di far passare
   un testo lungo come argomento attraverso cmd.exe;
2. prima di lanciare legge il file del reviewer e si ferma sugli errori che il modello
   gratuito non perdona: il file che non c'è e `mode: subagent` (in entrambi i casi la 1.18
   fa girare al suo posto l'agente `build`, che può scrivere sul progetto), e la shell tolta
   (il gratuito risponde 403). E se OpenCode ripiega comunque su un altro agente, lo ferma
   subito;
3. un tetto di tempo per processo, scaduto il quale il processo viene fermato davvero.

Provato con OpenCode 1.18.34 e 2.0.24 sul modello gratuito (06/10/2026).
"""

import asyncio
import json
import os
import re
import shutil
import subprocess
import sys
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any


class ErroreOpenCode(RuntimeError):
    """Un fallimento di OpenCode, con quello che serve per decidere se riprovare."""

    def __init__(self, messaggio: str, stato: int | None = None, riprovabile: bool = False):
        super().__init__(messaggio)
        self.stato = stato
        self.riprovabile = riprovabile


def comando_opencode() -> str:
    """Il comando OpenCode: OPENCODE_BIN se impostata, se no quello nel PATH."""
    trovato = os.environ.get("OPENCODE_BIN") or shutil.which("opencode")
    if not trovato:
        raise ErroreOpenCode("OpenCode non è nel PATH: vedi la pagina «Pre-bootcamp setup — Path B»")
    return trovato


def controlla_reviewer(cartella: Path, agente: str) -> None:
    """I difetti del file del reviewer che si vedono prima di lanciarlo, senza spendere richieste."""
    percorso = cartella / ".opencode" / "agents" / f"{agente}.md"
    if not percorso.is_file():
        raise ErroreOpenCode(
            f"Non trovo {percorso}: con un nome sbagliato la 1.18 non dà errore e fa girare "
            "l'agente build, che può scrivere sul progetto. Controlla il nome del reviewer"
        )
    parti = percorso.read_text(encoding="utf-8").split("---")
    frontmatter = parti[1] if len(parti) > 2 else ""
    if re.search(r"^mode:\s*[\"']?subagent[\"']?\s*(#.*)?$", frontmatter, re.MULTILINE):
        raise ErroreOpenCode(
            f"{percorso.name} è `mode: subagent`: la 1.18 ignora `--agent` e fa girare un altro "
            "agente al suo posto. Scrivi `mode: all`, che vale per entrambe le versioni"
        )
    if re.search(r"^\s*bash:\s*[\"']?(false|deny)[\"']?\s*(#.*)?$", frontmatter, re.MULTILINE):
        raise ErroreOpenCode(
            f"{percorso.name} toglie la shell (`bash: false` o `bash: deny`): il gratuito "
            "risponderebbe 403. Nega i comandi con le regole e lasciane almeno uno in `allow`"
        )
    blocco = re.search(r"^(\s*)bash:\s*\n((?:\1\s+.*\n?)+)", frontmatter, re.MULTILINE)
    if blocco and not re.search(
        r":\s*[\"']?(allow|ask)[\"']?\s*(#.*)?$", blocco.group(2), re.MULTILINE
    ):
        raise ErroreOpenCode(
            f"{percorso.name} nega tutti i comandi della shell: per OpenCode è come toglierla, e "
            'il gratuito risponderebbe 403. Lasciane almeno uno in `allow` (es. "git status*")'
        )


def _errore_da_evento(evento: dict[str, Any]) -> ErroreOpenCode:
    dati = (evento.get("error") or {}).get("data") or evento.get("error") or {}
    messaggio = str(dati.get("message") or dati)
    stato = dati.get("statusCode")
    riprovabile = bool(dati.get("isRetryable")) or stato == 429 or (
        isinstance(stato, int) and stato >= 500
    )
    if "free tier can only be used" in messaggio:
        messaggio += (
            " (403). Il gratuito rifiuta un agente senza la shell: niente `bash: false` né "
            "`bash: deny`, e almeno un comando in `allow`"
        )
    elif "or newer is required" in messaggio:
        messaggio += f" ({stato}). Aggiorna OpenCode: npm install -g opencode-ai@1.18.34"
    elif stato:
        messaggio += f" ({stato})"
    return ErroreOpenCode(messaggio, stato, riprovabile)


async def _ferma(processo: asyncio.subprocess.Process) -> None:
    """Ferma il processo e i suoi figli: su Windows il comando è un .cmd che lancia altro."""
    if processo.returncode is not None:
        return
    if sys.platform == "win32":
        await asyncio.to_thread(
            subprocess.run,
            ["taskkill", "/T", "/F", "/PID", str(processo.pid)],
            capture_output=True,
            check=False,
        )
    else:
        processo.kill()
    await processo.wait()


async def query_opencode(
    prompt: str,
    agente: str,
    cartella: str | Path = ".",
    tetto_secondi: float = 300,
) -> AsyncIterator[dict[str, Any]]:
    """Lancia `agente` su `prompt` nella cartella del repository e ne restituisce gli eventi.

    Solleva ErroreOpenCode per un evento "error", per un'uscita diversa da 0, per un reviewer
    ignorato e per il tetto di tempo superato (quest'ultimo con riprovabile=True).
    """
    cartella = Path(cartella).resolve()
    controlla_reviewer(cartella, agente)
    processo = await asyncio.create_subprocess_exec(
        comando_opencode(), "run", "--agent", agente, "--format", "json",
        cwd=cartella,  # la 1.18 avrebbe --dir, la 2.0 no: la cartella di lavoro vale per entrambe
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        limit=16 * 1024 * 1024,  # un evento può essere grande: un file letto intero ci finisce dentro
    )
    assert processo.stdin and processo.stdout and processo.stderr
    processo.stdin.write(prompt.encode("utf-8"))
    await processo.stdin.drain()
    processo.stdin.close()
    righe_errore: list[str] = []

    async def sorveglia_stderr() -> None:
        # la 1.18 avvisa solo qui, con uscita 0, quando fa girare un altro agente: si ferma subito
        assert processo.stderr
        async for grezza in processo.stderr:
            riga = grezza.decode("utf-8", errors="replace")
            righe_errore.append(riga)
            if "Falling back to default agent" in riga:
                await _ferma(processo)
                return

    stderr = asyncio.ensure_future(sorveglia_stderr())

    scadenza = asyncio.get_running_loop().time() + tetto_secondi
    try:
        while True:
            resta = scadenza - asyncio.get_running_loop().time()
            if resta <= 0:
                raise asyncio.TimeoutError
            riga = await asyncio.wait_for(processo.stdout.readline(), resta)
            if not riga:
                break
            try:
                evento = json.loads(riga.decode("utf-8", errors="replace"))
            except json.JSONDecodeError:
                continue  # una riga che non è un evento: OpenCode a volte stampa avvisi
            if evento.get("type") == "error":
                raise _errore_da_evento(evento)
            yield evento
        await processo.wait()
    except asyncio.TimeoutError:
        raise ErroreOpenCode(
            f"{agente}: nessuna risposta in {tetto_secondi:.0f}s (alza tetto_secondi, o dai meno "
            "file per volta)",
            riprovabile=True,
        ) from None
    finally:
        await _ferma(processo)
        await stderr

    await stderr
    errori = "".join(righe_errore)
    if "Falling back to default agent" in errori:
        raise ErroreOpenCode(
            f"OpenCode non ha usato {agente} e ha ripiegato su un altro agente: fermato. "
            "Il reviewer deve esistere ed essere `mode: all`"
        )
    if processo.returncode:
        raise ErroreOpenCode(f"OpenCode è uscito con {processo.returncode}: {errori.strip()[-500:]}")
