"use client";

import { useState, type FormEvent } from "react";
import ThemeToggle from "./theme-toggle";
import ChatTurn from "@/components/chat-turn";
import { sendChatMessage } from "@/lib/api";
import type { ConversationTurn, OakMessage, RawHistoryMessage } from "@/lib/types";
import styles from "./page.module.css";

let turnCounter = 0;
const nextTurnId = () => `turn-${turnCounter++}`;

export default function Home() {
  const [turns, setTurns] = useState<ConversationTurn[]>([]);
  const [history, setHistory] = useState<RawHistoryMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const message = input.trim();
    if (!message || loading) return;

    setTurns((prev) => [...prev, { id: nextTurnId(), role: "user", content: message }]);
    setInput("");
    setLoading(true);
    setError(null);

    try {
      const res = await sendChatMessage(message, history);
      const content: OakMessage =
        res.render.kind === "text" ? { kind: "text", text: res.reply } : { ...res.render, text: res.reply };

      setTurns((prev) => [...prev, { id: nextTurnId(), role: "oak", content }]);
      setHistory(res.history);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Algo salió mal consultando al laboratorio.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Pokédex — Edición Día/Noche</h1>
          <p className={styles.subtitle}>Laboratorio del Profesor Oak</p>
        </div>
        <ThemeToggle />
      </header>

      <main className={styles.chat}>
        {turns.length === 0 && !loading && (
          <p className={styles.empty}>
            Preguntale al Profesor por un pokemon, pedile que compare dos, o consultale matchups de tipo.
          </p>
        )}
        {turns.map((turn) => (
          <ChatTurn key={turn.id} turn={turn} />
        ))}
        {loading && <p className={styles.loading}>El Profesor está consultando sus registros…</p>}
        {error && <p className={styles.error}>{error}</p>}
      </main>

      <form className={styles.composer} onSubmit={handleSubmit}>
        <input
          className={styles.input}
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder="Preguntale algo al Profesor Oak..."
          disabled={loading}
        />
        <button className={styles.send} type="submit" disabled={loading || !input.trim()}>
          Enviar
        </button>
      </form>
    </div>
  );
}
