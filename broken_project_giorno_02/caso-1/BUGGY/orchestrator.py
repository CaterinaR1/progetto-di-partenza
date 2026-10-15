"""Lancia i reviewer e stampa il report."""

import asyncio
import time
from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query

MAX_TURNS = 15
MAX_BUDGET_USD = 1.50
BUDGET_SUITE_USD = 5.0
BUDGET_SUITE_SECONDS = 600


class BudgetSuperato(Exception):
    pass


async def run_subagent(name, target):
    costo = 0.0
    async for msg in query(
        prompt=f"Usa il subagent {name} per la review di {target}",
        options=ClaudeAgentOptions(
            cwd=".",
            setting_sources=["project"],
            allowed_tools=["Read", "Grep", "Glob"],
            max_turns=MAX_TURNS,
            max_budget_usd=MAX_BUDGET_USD,
        ),
    ):
        if isinstance(msg, ResultMessage):
            costo = msg.total_cost_usd or 0.0
    return {"name": name, "costo_usd": costo}


async def main(target):
    start = time.time()
    tasks = [run_subagent(name, target) for name in SUBAGENTS]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    costo = sum(r["costo_usd"] for r in results
                if not isinstance(r, Exception))
    trascorso = time.time() - start
    if costo > BUDGET_SUITE_USD:
        raise BudgetSuperato(f"costo ${costo:.2f} > ${BUDGET_SUITE_USD:.2f}")
    if trascorso > BUDGET_SUITE_SECONDS:
        raise BudgetSuperato(f"durata {trascorso:.0f}s > {BUDGET_SUITE_SECONDS}s")

    print(synthesize_report(results))
