"""Server MCP sul FinBank."""

import httpx
from fastmcp import FastMCP

mcp = FastMCP("finbank-mcp")

BACKEND = "http://localhost:8080"


@mcp.tool()
def query_account(account_id: int) -> dict:
    """Restituisce le informazioni e il saldo di un conto del LipariBank.

    Use this tool when:
    - devi conoscere il saldo reale di un conto prima di ragionare su un bonifico
    - l'utente chiede le informazioni di un account

    Do NOT use it to list movements or to move money.

    Args:
        account_id: ID dell'account (intero positivo)

    Returns:
        dict con account_id, balance, currency, last_updated
    """
    response = httpx.get(f"{BACKEND}/api/accounts/{account_id}")
    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    mcp.run()
