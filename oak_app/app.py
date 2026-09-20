"""Frontend real de Profesor Oak como Databricks App en Streamlit
(reglas/07-estado-actual.md -- pivot desde Vercel/Next.js, bloqueado por
un 401 de propagación M2M). Reusa agent/agent.py, hooks.py,
tool_choice.py, system_prompt.py y mcp_client.py TAL CUAL -- no se
reescribe nada de Fase 4 acá, mismo patrón que backend/app.py (Vercel).

Auth contra pokedex-mcp-server: mcp_client.py ya resuelve solo. Corriendo
como Databricks App (no en Vercel), DATABRICKS_HOST/DATABRICKS_PROFILE
no están seteados y no hace falta client_id/secret propios -- el SDK usa
WorkspaceClient()/Config() con el service principal de ESTA app,
inyectado automáticamente por la plataforma (auth app-to-app, validado
en vivo con el esqueleto de un botón antes de portar el resto de la UI).

Formato de salida por tipo de dato (reglas/04-frontend.md): ficha de
pokemon -> tarjeta con imagen+stats, comparación -> tabla lado a lado,
matchups de tipo -> badges agrupados por efectividad, resto -> texto.
render.py clasifica el turno real (nunca inventa un formato sin datos
detrás), serialize.py lo deja en JSON plano -- ambos copiados de
backend/, ver esos archivos.
"""

import asyncio
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

AGENT_DIR = Path(__file__).resolve().parent / "agent"
sys.path.insert(0, str(AGENT_DIR))

from agent import Agent  # noqa: E402
from mcp_client import PokedexMCPClient  # noqa: E402

from render import build_render  # noqa: E402
from serialize import serialize_messages  # noqa: E402

st.set_page_config(page_title="Profesor Oak -- Pokedex", page_icon="🔴", layout="centered")

STAT_ROWS = [
    ("hp", "PS"),
    ("attack", "Ataque"),
    ("defense", "Defensa"),
    ("special_attack", "At. Especial"),
    ("special_defense", "Def. Especial"),
    ("speed", "Velocidad"),
]

EFFECTIVENESS_GROUPS = [
    ("super_effective", "⚠️ Débil a", "🔥 Fuerte contra"),
    ("not_very_effective", "🛡️ Resiste", "💧 Poco efectivo contra"),
    ("no_effect", "🚫 Inmune a", "➖ Sin efecto contra"),
]


def _run_turn(user_message: str, history: list[dict]) -> tuple[str, list[dict], dict]:
    async def _call() -> tuple[str, list[dict], dict]:
        history_len = len(history)
        async with PokedexMCPClient() as mcp:
            agent = Agent(mcp)
            await agent.load_tools()
            # list(history), no history a secas -- si no, agent.messages
            # queda apuntando al MISMO objeto que session_state.history, y
            # cada .append() de agent.send() lo muta en el momento, dejando
            # len(history) igual a len(full_history) después de la llamada
            # (build_render siempre recibía [] y caía en kind="text").
            agent.messages = list(history)
            reply = await agent.send(user_message)
        full_history = serialize_messages(agent.messages)
        render = build_render(full_history[history_len:])
        return reply, full_history, render

    return asyncio.run(_call())


def _render_pokemon_card(pokemon: dict | None) -> None:
    if pokemon is None:
        st.warning("No encontré ese pokemon en Gold -- no invento datos.")
        return
    col_img, col_info = st.columns([1, 2])
    with col_img:
        if pokemon.get("image_url"):
            st.image(pokemon["image_url"], width=180)
    with col_info:
        st.subheader(pokemon["name"].capitalize())
        st.write(" ".join(f"`{t}`" for t in pokemon.get("types", [])))
        st.caption(f"Generación {pokemon.get('generation')} · #{pokemon.get('pokemon_id')}")
    stats = pokemon.get("stats", {})
    row1 = st.columns(3)
    row2 = st.columns(3)
    for col, (key, label) in zip(row1 + row2, STAT_ROWS):
        col.metric(label, stats.get(key))
    st.caption(
        f"Total: **{pokemon.get('total_stats')}** · "
        f"Ratio ataque/defensa: **{pokemon.get('attack_defense_ratio')}**"
    )
    if pokemon.get("lore"):
        st.markdown(f"> {pokemon['lore']}")


def _render_compare(compare: dict) -> None:
    pokemon_a, pokemon_b = compare.get("pokemon_a"), compare.get("pokemon_b")
    if not pokemon_a or not pokemon_b:
        if not pokemon_a:
            st.warning("No encontré datos para `pokemon_a`.")
        if not pokemon_b:
            st.warning("No encontré datos para `pokemon_b`.")
        return

    col_a, col_b = st.columns(2)
    for col, p in ((col_a, pokemon_a), (col_b, pokemon_b)):
        with col:
            if p.get("image_url"):
                st.image(p["image_url"], width=120)
            st.markdown(f"**{p['name'].capitalize()}**")
            st.write(" ".join(f"`{t}`" for t in p.get("types", [])))

    rows = []
    for key, label in STAT_ROWS:
        rows.append({"": label, pokemon_a["name"].capitalize(): pokemon_a["stats"][key], pokemon_b["name"].capitalize(): pokemon_b["stats"][key]})
    rows.append(
        {
            "": "Total",
            pokemon_a["name"].capitalize(): pokemon_a["total_stats"],
            pokemon_b["name"].capitalize(): pokemon_b["total_stats"],
        }
    )
    df = pd.DataFrame(rows).set_index("")

    def _highlight_winner(row: pd.Series) -> list[str]:
        a, b = row.iloc[0], row.iloc[1]
        styles = ["", ""]
        if a > b:
            styles[0] = "font-weight: bold; color: #2e7d32"
        elif b > a:
            styles[1] = "font-weight: bold; color: #2e7d32"
        return styles

    st.dataframe(df.style.apply(_highlight_winner, axis=1), use_container_width=True)


def _render_matchups(matchups: dict) -> None:
    st.subheader(f"Matchups de `{matchups.get('type')}`")
    col_def, col_off = st.columns(2)

    with col_def:
        st.markdown("**Defendiendo**")
        for effectiveness, def_label, _ in EFFECTIVENESS_GROUPS:
            entries = [e for e in matchups.get("defensive", []) if e.get("effectiveness") == effectiveness]
            if not entries:
                continue
            chips = ", ".join(f"`{e['attacking_type']}` (×{e['damage_multiplier']})" for e in entries)
            st.markdown(f"{def_label}: {chips}")

    with col_off:
        st.markdown("**Atacando**")
        for effectiveness, _, off_label in EFFECTIVENESS_GROUPS:
            entries = [e for e in matchups.get("offensive", []) if e.get("effectiveness") == effectiveness]
            if not entries:
                continue
            chips = ", ".join(f"`{e['defending_type']}` (×{e['damage_multiplier']})" for e in entries)
            st.markdown(f"{off_label}: {chips}")


def _render_turn(render: dict) -> None:
    kind = render.get("kind")
    if kind == "pokemon":
        _render_pokemon_card(render["pokemon"])
    elif kind == "compare":
        _render_compare(render["compare"])
    elif kind == "matchups":
        _render_matchups(render["matchups"])
    # kind == "text" -> nada que renderizar aparte de la prosa de Oak


st.title("🔴 Profesor Oak")
st.caption("Pokedex agente sobre gold.* -- Databricks App, sin Vercel de por medio (reglas/07-estado-actual.md).")

if "history" not in st.session_state:
    st.session_state.history = []  # agent.messages serializado, fuente de verdad para el próximo turno
if "turns" not in st.session_state:
    st.session_state.turns = []  # [(role, texto_o_None, render_dict_o_None)] para pintar la conversación

for role, text, render in st.session_state.turns:
    with st.chat_message(role):
        if text:
            st.markdown(text)
        if render is not None:
            try:
                _render_turn(render)
            except Exception as e:
                st.exception(e)

user_message = st.chat_input("Preguntale algo a Profesor Oak (ficha, comparación, matchups de tipo)...")

if user_message:
    st.session_state.turns.append(("user", user_message, None))
    with st.chat_message("user"):
        st.markdown(user_message)

    with st.chat_message("assistant"):
        with st.spinner("Profesor Oak está revisando la Pokedex..."):
            try:
                reply, full_history, render = _run_turn(user_message, st.session_state.history)
            except Exception as e:
                st.error(f"Error hablando con pokedex-mcp-server: {e!r}")
            else:
                st.session_state.history = full_history
                st.markdown(reply)
                try:
                    _render_turn(render)
                except Exception as e:
                    st.exception(e)
                st.session_state.turns.append(("assistant", reply, render))
