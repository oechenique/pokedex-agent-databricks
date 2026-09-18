import type { PokemonType } from "./types";

// Colores por tipo -- fijos entre temas a propósito: son parte de la
// identidad de cada tipo (como en los juegos), no del tema Día/Noche.
export const TYPE_COLORS: Record<PokemonType, string> = {
  bug: "#A6B91A",
  dark: "#705746",
  dragon: "#6F35FC",
  electric: "#F7D02C",
  fairy: "#D685AD",
  fighting: "#C22E28",
  fire: "#EE8130",
  flying: "#A98FF3",
  ghost: "#735797",
  grass: "#7AC74C",
  ground: "#E2BF65",
  ice: "#96D9D6",
  normal: "#A8A77A",
  poison: "#A33EA1",
  psychic: "#F95587",
  rock: "#B6A136",
  shadow: "#4C4C6D",
  steel: "#B7B7CE",
  stellar: "#7FD8E8",
  unknown: "#68A090",
  water: "#6390F0",
};

// WCAG relative luminance -> elige texto negro o blanco según cuál da más
// contraste, en vez de hardcodear 21 valores a mano.
function relativeLuminance(hex: string): number {
  const rgb = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255);
  const [r, g, b] = rgb.map((c) =>
    c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4)
  );
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

export function textColorFor(hex: string): "#0b0b0b" | "#ffffff" {
  return relativeLuminance(hex) > 0.5 ? "#0b0b0b" : "#ffffff";
}
