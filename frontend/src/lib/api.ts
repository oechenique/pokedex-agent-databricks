import type { ChatApiResponse, RawHistoryMessage } from "./types";

// reglas/04-frontend.md: el front nunca pega a Databricks directo -- solo
// habla con este backend, que a su vez le pega a Claude y al MCP server.
// Path relativo (mismo origin) a propósito: Next.js y el backend FastAPI
// corren en la misma Databricks App, Next.js proxea /api/* server-side
// (ver rewrites() en next.config.ts) -- no hay una URL de backend externa
// que exponer.
export async function sendChatMessage(
  message: string,
  history: RawHistoryMessage[],
  multiAgent: boolean
): Promise<ChatApiResponse> {
  const response = await fetch(`/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, history, multi_agent: multiAgent }),
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? `El backend respondió ${response.status}`);
  }

  return response.json();
}
