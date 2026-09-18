// Tipos calcados de lo que devuelven de verdad las tools de
// pokedex-mcp-server (ver agent/hooks.py::extract_json y las transcripciones
// de Fase 4) -- para que enchufar el backend real en la siguiente etapa no
// obligue a tocar los componentes.

export type PokemonType =
  | "bug"
  | "dark"
  | "dragon"
  | "electric"
  | "fairy"
  | "fighting"
  | "fire"
  | "flying"
  | "ghost"
  | "grass"
  | "ground"
  | "ice"
  | "normal"
  | "poison"
  | "psychic"
  | "rock"
  | "shadow"
  | "steel"
  | "stellar"
  | "unknown"
  | "water";

export interface PokemonStats {
  hp: number;
  attack: number;
  defense: number;
  special_attack: number;
  special_defense: number;
  speed: number;
}

export interface Pokemon {
  pokemon_id: number;
  name: string;
  generation: number;
  types: PokemonType[];
  height: number;
  weight: number;
  image_url: string;
  lore: string;
  stats: PokemonStats;
  total_stats: number;
  attack_defense_ratio: number;
}

export type Effectiveness =
  | "super_effective"
  | "not_very_effective"
  | "no_effect"
  | "neutral";

export interface TypeMatchupEntry {
  defending_type?: PokemonType;
  attacking_type?: PokemonType;
  damage_multiplier: number;
  effectiveness: Effectiveness;
}

export interface TypeMatchups {
  type: PokemonType;
  offensive: TypeMatchupEntry[];
  defensive: TypeMatchupEntry[];
}

export interface ComparePokemon {
  pokemon_a: Pokemon | null;
  pokemon_b: Pokemon | null;
}

// Formato por tipo de dato (reglas/04-frontend.md): la síntesis nunca
// fuerza todo a un único formato de render. `text` viaja en las 4 variantes
// porque Oak siempre acompaña el dato estructurado con su lectura en prosa
// (RULES #2 del system prompt: separar dato de tool vs. cálculo/opinión propia).
export type OakMessage =
  | { kind: "text"; text: string }
  | { kind: "pokemon"; pokemon: Pokemon; text: string }
  | { kind: "compare"; compare: ComparePokemon; text: string }
  | { kind: "matchups"; matchups: TypeMatchups; text: string };

export interface ConversationTurn {
  id: string;
  role: "user" | "oak";
  content: string | OakMessage;
}

// Forma cruda del historial que viaja al backend y vuelve -- son los
// mensajes de agent.Agent().messages ya serializados (backend/serialize.py),
// opacos para el front: solo se guardan y se reenvían tal cual.
export type RawHistoryMessage = Record<string, unknown>;

export type ChatRender =
  | { kind: "text" }
  | { kind: "pokemon"; pokemon: Pokemon }
  | { kind: "compare"; compare: ComparePokemon }
  | { kind: "matchups"; matchups: TypeMatchups };

export interface ChatApiResponse {
  reply: string;
  history: RawHistoryMessage[];
  render: ChatRender;
}
