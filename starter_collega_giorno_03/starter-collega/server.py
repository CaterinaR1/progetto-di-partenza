"""Server MCP sul FinBank — prima versione (Gino)."""

from typing import Any

import httpx
from fastmcp import FastMCP

mcp = FastMCP("finbank-mcp")

BASE_URL = "http://localhost:8080"


@mcp.tool()
def get_balance(id: int) -> dict:
    """Get balance."""
    response = httpx.get(f"{BASE_URL}/api/accounts/{id}")
    return response.json()


@mcp.tool()
def execute_transfer(source: int, target: int, amount: float) -> Any:
    """Execute a transfer."""
    response = httpx.post(
        f"{BASE_URL}/api/movements/transfer",
        json={
            "sourceAccountId": source,
            "targetAccountId": target,
            "amount": amount,
        },
    )
    return response.json()


if __name__ == "__main__":
    mcp.run()
