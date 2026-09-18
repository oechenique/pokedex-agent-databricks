import type { ChatApiResponse, RawHistoryMessage } from "./types";

// reglas/04-frontend.md: el front nunca pega a Databricks directo -- solo
// habla con este backend, que a su vez le pega a Claude y al MCP server.
// NEXT_PUBLIC_ porque el fetch sale del browser (backend/app.py define su
// propio rate limit y CORS, así que exponer la URL no es un problema de
// seguridad -- no hay ninguna key detrás de esta constante).
const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";

export async function sendChatMessage(
  message: string,
  history: RawHistoryMessage[]
): Promise<ChatApiResponse> {
  const response = await fetch(`${BACKEND_URL}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, history }),
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? `El backend respondió ${response.status}`);
  }

  return response.json();
}
