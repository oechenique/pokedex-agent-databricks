"use client";

import { useState } from "react";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL ??
  "https://pokedex-backend-7405616363788532.12.azure.databricksapps.com";

export default function Home() {
  const [reply, setReply] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>("");

  async function ask() {
    setLoading(true);
    setError("");
    setReply("");
    try {
      const res = await fetch(`${BACKEND_URL}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ message: "contame de Pikachu", history: [] }),
      });
      if (!res.ok) {
        setError(`HTTP ${res.status}: ${await res.text()}`);
        return;
      }
      const data = await res.json();
      setReply(data.reply);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <main style={{ padding: 32, fontFamily: "monospace" }}>
      <h1>Esqueleto Next.js -- Databricks App</h1>
      <p>Backend: {BACKEND_URL}</p>
      <button onClick={ask} disabled={loading}>
        {loading ? "Preguntando..." : "Preguntarle a Oak sobre Pikachu"}
      </button>
      {error && <pre style={{ color: "red" }}>{error}</pre>}
      {reply && <p style={{ whiteSpace: "pre-wrap" }}>{reply}</p>}
    </main>
  );
}
