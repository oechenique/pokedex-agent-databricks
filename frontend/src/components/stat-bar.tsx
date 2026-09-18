import styles from "./stat-bar.module.css";

export default function StatBar({ value, max }: { value: number; max: number }) {
  const pct = Math.min(100, Math.round((value / max) * 100));
  return (
    <span className={styles.track} role="img" aria-label={`${value} de ${max}`}>
      <span className={styles.fill} style={{ width: `${pct}%` }} />
    </span>
  );
}
