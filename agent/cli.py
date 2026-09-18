"""CLI interactiva para probar al Profesor Oak a mano (reglas/03-agente-mcp.md
pide 3 conversaciones manuales antes de commitear). Requiere ANTHROPIC_API_KEY
y MCP_SERVER_URL en el entorno -- ver `.env.example`.

Uso: python agent/cli.py
Comando de debug `:raw <tool> <json>` -- llama a la tool real saltando a
Claude, para poder disparar a propósito un isError=true legítimo (ej. un
enum inválido) sin mockear nada. Solo para las pruebas manuales de esta fase.
"""

import asyncio
import json
import sys

from agent import Agent
from mcp_client import PokedexMCPClient


async def main() -> None:
    async with PokedexMCPClient() as mcp:
        agent = Agent(mcp)
        await agent.load_tools()
        print(f"Profesor Oak listo -- tools: {[t['name'] for t in agent.tools]}")
        print("Escribí tu mensaje (o ':raw <tool> <json>' para debug, 'salir' para cortar).\n")

        while True:
            try:
                user_message = await asyncio.to_thread(input, "vos> ")
            except EOFError:
                break
            if not user_message.strip():
                continue
            if user_message.strip().lower() in {"salir", "exit", "quit"}:
                break

            if user_message.startswith(":raw "):
                await _raw_call(mcp, user_message[len(":raw "):])
                continue

            reply = await agent.send(user_message)
            print(f"oak> {reply}\n")


async def _raw_call(mcp: PokedexMCPClient, rest: str) -> None:
    try:
        tool_name, raw_args = rest.strip().split(" ", 1)
        args = json.loads(raw_args)
    except ValueError:
        print("uso: :raw <tool> <json de argumentos>\n")
        return

    result = await mcp.call_tool(tool_name, args)
    print(f"[raw] is_error={result.is_error} content={result.content}\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
