"use client";

import { useSyncExternalStore } from "react";
import { useTheme } from "next-themes";
import styles from "./theme-toggle.module.css";

const subscribeNever = () => () => {};

export default function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  // next-themes no conoce el tema real hasta montar en el cliente -- antes
  // de eso renderizamos un placeholder para no arriesgar un mismatch de
  // hidratación entre server y client. useSyncExternalStore (en vez de
  // useState+useEffect) evita el lint react-hooks/set-state-in-effect.
  const mounted = useSyncExternalStore(
    subscribeNever,
    () => true,
    () => false
  );

  if (!mounted) {
    return <button className={styles.toggle} aria-label="Cambiar tema" />;
  }

  const isDark = resolvedTheme === "dark";

  return (
    <button
      type="button"
      className={styles.toggle}
      onClick={() => setTheme(isDark ? "light" : "dark")}
      aria-label={isDark ? "Cambiar a modo Día" : "Cambiar a modo Noche"}
      title={isDark ? "Modo Día (Hada/Luz)" : "Modo Noche (Fantasma/Siniestro)"}
    >
      {isDark ? (
        <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
          <path
            fill="currentColor"
            d="M12 3a1 1 0 011 1v1a1 1 0 11-2 0V4a1 1 0 011-1zm0 15a5 5 0 100-10 5 5 0 000 10zm9-6a1 1 0 010 2h-1a1 1 0 110-2h1zM4 12a1 1 0 010 2H3a1 1 0 110-2h1zm14.36-6.36a1 1 0 011.42 1.42l-.71.7a1 1 0 11-1.42-1.41l.71-.71zM6.35 17.66a1 1 0 011.41 1.41l-.7.71a1 1 0 11-1.42-1.42l.71-.7zm11.31 1.41a1 1 0 01-1.42 0l-.7-.7a1 1 0 111.41-1.42l.71.71a1 1 0 010 1.41zM7.05 6.34a1 1 0 01-1.41 0l-.71-.7A1 1 0 116.35 4.2l.7.71a1 1 0 010 1.42zM12 6a1 1 0 011-1V4a1 1 0 10-2 0v1a1 1 0 011 1z"
          />
        </svg>
      ) : (
        <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
          <path
            fill="currentColor"
            d="M20.742 13.045a8.088 8.088 0 01-2.077.271c-4.554 0-8.25-3.694-8.25-8.25 0-1.163.243-2.27.677-3.271A9.75 9.75 0 1021.75 14.522a8.5 8.5 0 01-1.008-1.477z"
          />
        </svg>
      )}
    </button>
  );
}
