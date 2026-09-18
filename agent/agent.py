"""Loop del agente Profesor Oak (reglas/03-agente-mcp.md).

Loop manual con la Messages API (no Claude Agent SDK, no tool runner beta):
tool_choice se decide por turno y los hooks necesitan un punto de
intercepción exacto antes/después de cada llamada a tool, así que se
escribe a mano en vez de delegarlo a un helper que no expone ese punto.
"""

import json

import anthropic

import config
import hooks
import system_prompt
import tool_choice
from mcp_client import PokedexMCPClient

MAX_TOKENS = 4096


class Agent:
    def __init__(self, mcp: PokedexMCPClient) -> None:
        self.mcp = mcp
        self.client = anthropic.Anthropic()
        self.messages: list[dict] = []
        self.tools: list[dict] = []

    async def load_tools(self) -> None:
        mcp_tools = await self.mcp.list_tools()
        self.tools = [
            {
                "name": t.name,
                "description": t.description or "",
                "input_schema": t.input_schema,
            }
            for t in mcp_tools
        ]

    async def send(self, user_message: str) -> str:
        self.messages.append({"role": "user", "content": user_message})
        forced_choice = tool_choice.choose_tool_choice(user_message)

        response = self._create(forced_choice=forced_choice)

        # Una vez que ya corrió una ronda de tool_use soltamos el forzado:
        # si Claude necesita otra tool para terminar, que la elija ella --
        # forzar la misma tool en cada vuelta del loop puede colgarlo.
        while response.stop_reason == "tool_use":
            self.messages.append({"role": "assistant", "content": response.content})
            tool_results = [
                await self._run_tool(block) for block in response.content if block.type == "tool_use"
            ]
            self.messages.append({"role": "user", "content": tool_results})
            response = self._create(forced_choice=None)

        self.messages.append({"role": "assistant", "content": response.content})
        return "\n".join(block.text for block in response.content if block.type == "text")

    def _create(self, forced_choice: dict | None):
        kwargs = dict(
            model=config.ANTHROPIC_MODEL,
            max_tokens=MAX_TOKENS,
            system=system_prompt.build_system_blocks(),
            tools=self.tools,
            messages=self.messages,
        )
        if forced_choice is not None:
            kwargs["tool_choice"] = forced_choice
        return self.client.messages.create(**kwargs)

    async def _run_tool(self, block) -> dict:
        ctx = hooks.HookContext(call_tool=self.mcp.call_tool)
        try:
            await hooks.pre_tool_use(block.name, block.input, ctx)
        except hooks.ToolBlocked as exc:
            return {
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": f"[PreToolUse bloqueó la llamada] {exc}",
                "is_error": True,
            }

        result = await self.mcp.call_tool(block.name, block.input)
        outcome = hooks.post_tool_use(block.name, result)

        if not outcome["ok"]:
            return {
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": f"[PostToolUse: isError=true, no es un dato válido] {outcome['error']}",
                "is_error": True,
            }

        return {
            "type": "tool_result",
            "tool_use_id": block.id,
            "content": json.dumps(outcome["data"], ensure_ascii=False),
        }
