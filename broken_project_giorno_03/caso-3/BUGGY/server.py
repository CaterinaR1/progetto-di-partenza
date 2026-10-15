"""Server MCP sul FinBank.

Questo server e' usato per la review del codice: espone SOLO strumenti di sola
lettura. Nessun tool deve poter modificare lo stato. Il bonifico reale
(POST /api/movements/transfer) non e' esposto a chi fa review.
"""

import httpx
from fastmcp import FastMCP

mcp = FastMCP("finbank-mcp")

BACKEND = "http://localhost:8080"


@mcp.tool()
def simulate_transfer_what_if(source: int, target: int, amount: float) -> dict:
    """Simula un bonifico e dice se e' fattibile, senza eseguirlo.

    Use this tool when:
    - durante una review vuoi verificare l'effetto di un bonifico senza spostare denaro

    Do NOT use it to move real money: legge soltanto, non scrive mai.

    Args:
        source: ID del conto di addebito
        target: ID del conto di accredito
        amount: importo in EUR

    Returns:
        dict con fattibile, saldo_source_dopo, saldo_target_dopo
    """
    src = httpx.get(f"{BACKEND}/api/accounts/{source}")
    src.raise_for_status()
    dst = httpx.get(f"{BACKEND}/api/accounts/{target}")
    dst.raise_for_status()
    saldo_src = src.json().get("balance", 0)
    saldo_dst = dst.json().get("balance", 0)
    return {
        "fattibile": amount > 0 and saldo_src >= amount,
        "saldo_source_dopo": saldo_src - amount,
        "saldo_target_dopo": saldo_dst + amount,
    }


if __name__ == "__main__":
    mcp.run()
