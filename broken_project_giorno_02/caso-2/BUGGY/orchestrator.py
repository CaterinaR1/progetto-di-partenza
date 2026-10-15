"""Lancia i quattro reviewer su un target e raccoglie gli esiti."""

import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions

SUBAGENTS = [
    ("code-reviewer-banking-domain", "..."),
    ("security-reviewer", "..."),
    ("performance-reviewer", "..."),
    ("rest-contract-reviewer", "..."),
]


async def run_subagent(name, desc, target, cid):
    # ... chiamata Claude Agent SDK ...
    pass


async def main(target):
    cid = "abc-123"

    return await asyncio.gather(
        *(run_subagent(name, desc, target, cid) for name, desc in SUBAGENTS),
        return_exceptions=True,
    )
