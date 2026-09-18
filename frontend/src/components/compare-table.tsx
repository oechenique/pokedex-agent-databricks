import Image from "next/image";
import type { ComparePokemon, Pokemon } from "@/lib/types";
import TypeBadge from "./type-badge";
import styles from "./compare-table.module.css";

const ROWS: { key: keyof Pokemon["stats"]; label: string }[] = [
  { key: "hp", label: "PS" },
  { key: "attack", label: "Ataque" },
  { key: "defense", label: "Defensa" },
  { key: "special_attack", label: "At. Especial" },
  { key: "special_defense", label: "Def. Especial" },
  { key: "speed", label: "Velocidad" },
];

function Missing({ label }: { label: string }) {
  return <p className={styles.missing}>No encontré datos para &ldquo;{label}&rdquo;.</p>;
}

export default function CompareTable({ compare }: { compare: ComparePokemon }) {
  const { pokemon_a, pokemon_b } = compare;

  if (!pokemon_a || !pokemon_b) {
    return (
      <div className={styles.wrapper}>
        {!pokemon_a && <Missing label="pokemon_a" />}
        {!pokemon_b && <Missing label="pokemon_b" />}
      </div>
    );
  }

  return (
    <div className={styles.wrapper}>
      <table className={styles.table}>
        <thead>
          <tr>
            <th></th>
            <th>
              <Image src={pokemon_a.image_url} alt={pokemon_a.name} width={64} height={64} />
              <div className={styles.name}>{pokemon_a.name}</div>
              <div className={styles.types}>
                {pokemon_a.types.map((t) => (
                  <TypeBadge key={t} type={t} />
                ))}
              </div>
            </th>
            <th>
              <Image src={pokemon_b.image_url} alt={pokemon_b.name} width={64} height={64} />
              <div className={styles.name}>{pokemon_b.name}</div>
              <div className={styles.types}>
                {pokemon_b.types.map((t) => (
                  <TypeBadge key={t} type={t} />
                ))}
              </div>
            </th>
          </tr>
        </thead>
        <tbody>
          {ROWS.map(({ key, label }) => {
            const a = pokemon_a.stats[key];
            const b = pokemon_b.stats[key];
            return (
              <tr key={key}>
                <th scope="row">{label}</th>
                <td className={a > b ? styles.winner : undefined}>{a}</td>
                <td className={b > a ? styles.winner : undefined}>{b}</td>
              </tr>
            );
          })}
          <tr className={styles.totalRow}>
            <th scope="row">Total</th>
            <td className={pokemon_a.total_stats > pokemon_b.total_stats ? styles.winner : undefined}>
              {pokemon_a.total_stats}
            </td>
            <td className={pokemon_b.total_stats > pokemon_a.total_stats ? styles.winner : undefined}>
              {pokemon_b.total_stats}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}
