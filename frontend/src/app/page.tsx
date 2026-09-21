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
  // Fase 6 (agent/orchestrator.py): fuerza coordinador + 3 subagentes en vez
  // del agente single. El backend además lo activa solo si el mensaje pide
  // un análisis completo (should_use_multi_agent) -- este toggle es un OR,
  // no la única forma de entrar al modo multi-agente.
  const [forceMultiAgent, setForceMultiAgent] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const message = input.trim();
    if (!message || loading) return;

    setTurns((prev) => [...prev, { id: nextTurnId(), role: "user", content: message }]);
    setInput("");
    setLoading(true);
    setError(null);

    try {
      const res = await sendChatMessage(message, history, forceMultiAgent);
      const content: OakMessage =
        res.render.kind === "text"
          ? { kind: "text", text: res.reply, trace: res.trace }
          : { ...res.render, text: res.reply, trace: res.trace };

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
        <div className={styles.headerControls}>
          <button
            type="button"
            className={`${styles.multiAgentToggle} ${forceMultiAgent ? styles.multiAgentActive : ""}`}
            onClick={() => setForceMultiAgent((v) => !v)}
            aria-pressed={forceMultiAgent}
            title="Coordinador + 3 subagentes (Pokemon Researcher, Battle Analyst, Data Librarian) en vez del agente single. También se activa solo si pedís un análisis completo."
          >
            🧩 Multi-agente
          </button>
          <ThemeToggle />
        </div>
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
        {loading && (
          <p className={styles.loading}>
            {forceMultiAgent
              ? "El equipo de Profesor Oak está trabajando (coordinador + subagentes)…"
              : "El Profesor está consultando sus registros…"}
          </p>
        )}
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
