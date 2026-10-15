"""Server MCP sul FinBank."""

import httpx
from fastmcp import FastMCP

mcp = FastMCP("finbank-mcp")

BACKEND = "http://localhost:8080"


@mcp.tool()
def get_balance(account_id: int) -> dict:
    """Restituisce il saldo corrente di un conto del LipariBank.

    Use this tool when:
    - durante una review devi verificare il saldo reale invece di stimarlo dal codice
    - l'utente chiede quanto denaro c'e' su un conto

    Do NOT use it to list movements or to move money.

    Args:
        account_id: ID dell'account (intero positivo)

    Returns:
        dict con account_id, balance, currency
    """
    response = httpx.get(f"{BACKEND}/api/accounts/{account_id}")
    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    mcp.run()
