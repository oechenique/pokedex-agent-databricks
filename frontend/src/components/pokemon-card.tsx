import Image from "next/image";
import type { Pokemon } from "@/lib/types";
import TypeBadge from "./type-badge";
import StatBar from "./stat-bar";
import styles from "./pokemon-card.module.css";

const STAT_LABELS: Record<keyof Pokemon["stats"], string> = {
  hp: "PS",
  attack: "Ataque",
  defense: "Defensa",
  special_attack: "At. Esp.",
  special_defense: "Def. Esp.",
  speed: "Velocidad",
};

export default function PokemonCard({ pokemon }: { pokemon: Pokemon }) {
  return (
    <article className={styles.card}>
      <div className={styles.header}>
        <Image
          src={pokemon.image_url}
          alt={pokemon.name}
          width={120}
          height={120}
          className={styles.artwork}
        />
        <div className={styles.identity}>
          <h3 className={styles.name}>
            {pokemon.name} <span className={styles.dex}>#{pokemon.pokemon_id}</span>
          </h3>
          <p className={styles.meta}>
            Gen {pokemon.generation} · {pokemon.height / 10} m · {pokemon.weight / 10} kg
          </p>
          <div className={styles.types}>
            {pokemon.types.map((t) => (
              <TypeBadge key={t} type={t} />
            ))}
          </div>
        </div>
      </div>

      <dl className={styles.stats}>
        {(Object.keys(pokemon.stats) as (keyof Pokemon["stats"])[]).map((key) => (
          <div key={key} className={styles.statRow}>
            <dt>{STAT_LABELS[key]}</dt>
            <dd>
              <StatBar value={pokemon.stats[key]} max={180} />
              <span className={styles.statValue}>{pokemon.stats[key]}</span>
            </dd>
          </div>
        ))}
      </dl>

      <p className={styles.total}>Total: {pokemon.total_stats}</p>

      {pokemon.lore && <p className={styles.lore}>{pokemon.lore}</p>}
    </article>
  );
}
