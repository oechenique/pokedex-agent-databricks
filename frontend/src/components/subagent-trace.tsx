import type { SubagentTrace as SubagentTraceEntry } from "@/lib/types";
import OakText from "./oak-text";
import styles from "./subagent-trace.module.css";

// Panel de trazabilidad del modo multi-agente (Fase 6, agent/orchestrator.py
// + agent/subagents.py) -- mismo contenido que el expander "Cómo trabajó el
// equipo" de oak_app (Streamlit), portado a <details> nativo acá. Solo
// aparece cuando el turno corrió con el coordinador (trace no vacío);
// en modo single no se renderiza nada.
export default function SubagentTrace({ trace }: { trace?: SubagentTraceEntry[] }) {
  if (!trace || trace.length === 0) return null;

  return (
    <details className={styles.wrapper}>
      <summary className={styles.summary}>🧩 Cómo trabajó el equipo (coordinador + subagentes)</summary>
      <div className={styles.body}>
        {trace.map((r, i) => (
          <div key={`${r.role}-${i}`} className={styles.entry}>
            <p className={styles.role}>{r.role}</p>
            <p className={styles.meta}>Objetivo: {r.goal}</p>
            <p className={styles.meta}>Criterio de calidad: {r.quality_criteria}</p>
            {r.tool_calls.length > 0 && (
              <div className={styles.tools}>
                <span>Tools usadas:</span>
                {r.tool_calls.map((t, j) => (
                  <code key={`${t}-${j}`} className={styles.toolChip}>
                    {t}
                  </code>
                ))}
              </div>
            )}
            <div className={styles.summaryText}>
              <OakText text={r.summary} />
            </div>
          </div>
        ))}
      </div>
    </details>
  );
}
