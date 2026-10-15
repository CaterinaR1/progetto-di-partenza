"""Esegue un reviewer sul target."""

from claude_agent_sdk import query, ClaudeAgentOptions


async def run_subagent(name, target):
    async for msg in query(
        prompt=f"Usa il subagent {name} per la review di {target}",
        options=ClaudeAgentOptions(
            cwd=".",
            setting_sources=["project"],
            allowed_tools=["Read", "Grep", "Glob"],
            max_turns=15,
        )
    ):
        # ... process ...
        pass
