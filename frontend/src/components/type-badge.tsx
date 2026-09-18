import type { PokemonType } from "@/lib/types";
import { TYPE_COLORS, textColorFor } from "@/lib/type-colors";
import styles from "./type-badge.module.css";

export default function TypeBadge({ type }: { type: PokemonType }) {
  const bg = TYPE_COLORS[type];
  return (
    <span
      className={styles.badge}
      style={{ backgroundColor: bg, color: textColorFor(bg) }}
    >
      {type}
    </span>
  );
}
