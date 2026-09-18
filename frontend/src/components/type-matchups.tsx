import type { Effectiveness, TypeMatchupEntry, TypeMatchups } from "@/lib/types";
import TypeBadge from "./type-badge";
import styles from "./type-matchups.module.css";

const GROUPS: { effectiveness: Effectiveness; defLabel: string; offLabel: string }[] = [
  { effectiveness: "super_effective", defLabel: "Débil a", offLabel: "Fuerte contra" },
  { effectiveness: "not_very_effective", defLabel: "Resiste", offLabel: "Poco efectivo contra" },
  { effectiveness: "no_effect", defLabel: "Inmune a", offLabel: "Sin efecto contra" },
];

function effClass(effectiveness: Effectiveness): string {
  if (effectiveness === "super_effective") return styles.super;
  if (effectiveness === "not_very_effective") return styles.weak;
  if (effectiveness === "no_effect") return styles.none;
  return "";
}

function Section({
  title,
  entries,
  effectiveness,
  side,
}: {
  title: string;
  entries: TypeMatchupEntry[];
  effectiveness: Effectiveness;
  side: "offensive" | "defensive";
}) {
  if (entries.length === 0) return null;
  return (
    <div className={`${styles.section} ${effClass(effectiveness)}`}>
      <span className={styles.sectionTitle}>{title}</span>
      <div className={styles.chips}>
        {entries.map((entry) => {
          const t = side === "offensive" ? entry.defending_type : entry.attacking_type;
          if (!t) return null;
          return (
            <span key={t} className={styles.chip}>
              <TypeBadge type={t} />
              <span className={styles.multiplier}>×{entry.damage_multiplier}</span>
            </span>
          );
        })}
      </div>
    </div>
  );
}

export default function TypeMatchupBadges({ matchups }: { matchups: TypeMatchups }) {
  return (
    <div className={styles.wrapper}>
      <h3 className={styles.heading}>
        Matchups de <TypeBadge type={matchups.type} />
      </h3>

      <div className={styles.column}>
        <p className={styles.columnLabel}>Defendiendo</p>
        {GROUPS.map((g) => (
          <Section
            key={`def-${g.effectiveness}`}
            title={g.defLabel}
            effectiveness={g.effectiveness}
            side="defensive"
            entries={matchups.defensive.filter((e) => e.effectiveness === g.effectiveness)}
          />
        ))}
      </div>

      <div className={styles.column}>
        <p className={styles.columnLabel}>Atacando</p>
        {GROUPS.map((g) => (
          <Section
            key={`off-${g.effectiveness}`}
            title={g.offLabel}
            effectiveness={g.effectiveness}
            side="offensive"
            entries={matchups.offensive.filter((e) => e.effectiveness === g.effectiveness)}
          />
        ))}
      </div>
    </div>
  );
}
