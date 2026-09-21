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

Fase 6 -- modo multi-agente opcional (orchestrator.py, subagents.py):
coordinador + 3 subagentes aislados (Pokemon Researcher, Battle Analyst,
Data Librarian), contexto entre subagentes pasado explícito por el
coordinador, nunca subagente-a-subagente. Se activa con el toggle de la
sidebar o solo si la pregunta pide un análisis multi-faceta
(orchestrator.should_use_multi_agent) -- el agente single sigue siendo
el modo default.
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
from orchestrator import run_multi_agent, should_use_multi_agent  # noqa: E402

from render import build_render  # noqa: E402
from serialize import serialize_messages  # noqa: E402

st.set_page_config(page_title="Profesor Oak -- Pokedex", page_icon="🔴", layout="centered")

# Tema Día/Noche -- misma paleta conceptual que frontend/src/app/globals.css
# (Día: Hada/Luz, pastel cálido + dorado. Noche: Fantasma/Siniestro, violeta
# profundo + fosforescente), no pixel-perfect -- Streamlit tiene su propio
# árbol de componentes, esto apunta a sus data-testid reales.
THEMES = {
    "day": {
        "bg": "#fff7f0",
        "bg_elevated": "#ffffff",
        "bg_subtle": "#ffeee0",
        "text": "#3b2a2e",
        "text_muted": "#8a7370",
        "border": "#f0d9c8",
        "accent": "#a8790f",
        "accent_strong": "#7a5a0c",
        "user_bubble": "#ffe9d6",
        "oak_bubble": "#ffffff",
    },
    "night": {
        "bg": "#0f0a1a",
        "bg_elevated": "#1c1330",
        "bg_subtle": "#241a3d",
        "text": "#ede7f6",
        "text_muted": "#b0a3d0",
        "border": "#3a2b57",
        "accent": "#b583ff",
        "accent_strong": "#d9b8ff",
        "user_bubble": "#2a1f47",
        "oak_bubble": "#1c1330",
    },
}


def _inject_theme_css(mode: str) -> None:
    c = THEMES[mode]
    st.markdown(
        f"""
        <style>
        .stApp {{
            background: {c["bg"]} !important;
            color: {c["text"]} !important;
        }}
        [data-testid="stBottom"], [data-testid="stBottom"] > div,
        [data-testid="stBottomBlockContainer"] {{
            background: {c["bg"]} !important;
        }}
        [data-testid="stSidebar"] {{
            background: {c["bg_subtle"]} !important;
            border-right: 1px solid {c["border"]};
        }}
        [data-testid="stChatMessage"] {{
            background: {c["oak_bubble"]} !important;
            border: 1px solid {c["border"]} !important;
            border-radius: 14px;
            padding: 0.5rem 0.75rem;
        }}
        [data-testid="stChatMessage"] p, [data-testid="stChatMessage"] span,
        [data-testid="stChatMessage"] li, .stApp p, .stApp span, .stApp li,
        .stApp label {{
            color: {c["text"]} !important;
        }}
        .stApp h1, .stApp h2, .stApp h3, .stApp h4 {{
            color: {c["accent_strong"]} !important;
        }}
        [data-testid="stMetricValue"] {{
            color: {c["accent"]} !important;
        }}
        [data-testid="stMetricLabel"] {{
            color: {c["text_muted"]} !important;
        }}
        [data-testid="stCaptionContainer"], .stApp small {{
            color: {c["text_muted"]} !important;
        }}
        [data-testid="stChatInput"] textarea {{
            background: {c["bg_elevated"]} !important;
            color: {c["text"]} !important;
            border-color: {c["border"]} !important;
        }}
        [data-testid="stChatInput"] {{
            background: {c["bg_elevated"]} !important;
            border-color: {c["border"]} !important;
        }}
        code {{
            background: {c["bg_subtle"]} !important;
            color: {c["accent_strong"]} !important;
        }}
        a {{
            color: {c["accent"]} !important;
        }}
        blockquote {{
            border-left: 3px solid {c["accent"]};
            color: {c["text_muted"]} !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


if "theme" not in st.session_state:
    st.session_state.theme = "day"

if "force_multi_agent" not in st.session_state:
    st.session_state.force_multi_agent = False

with st.sidebar:
    st.session_state.theme = "night" if st.toggle(
        "🌙 Modo noche", value=(st.session_state.theme == "night")
    ) else "day"
    st.session_state.force_multi_agent = st.toggle(
        "🧩 Multi-agente (Fase 6)",
        value=st.session_state.force_multi_agent,
        help=(
            "Coordinador + 3 subagentes (Pokemon Researcher, Battle Analyst, "
            "Data Librarian) en vez del agente single. También se activa "
            "solo si la pregunta pide un análisis completo."
        ),
    )

_inject_theme_css(st.session_state.theme)

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


def _run_turn(user_message: str, history: list[dict], multi_agent: bool) -> tuple[str, list[dict], dict, list]:
    async def _call() -> tuple[str, list[dict], dict, list]:
        history_len = len(history)
        async with PokedexMCPClient() as mcp:
            agent = Agent(mcp)
            await agent.load_tools()

            if multi_agent:
                # Coordinador + subagentes (Fase 6, orchestrator.py) -- el
                # detalle de quién hizo qué vive en result.trace, para la UI.
                # session_state.history sigue en el mismo formato que el modo
                # single (para que un turno normal después pueda seguir la
                # charla), pero sin el detalle interno de cada subagente --
                # eso nunca fue parte de la conversación con el usuario.
                result = await run_multi_agent(user_message, mcp, agent.tools)
                full_history = list(history) + [
                    {"role": "user", "content": user_message},
                    {"role": "assistant", "content": [{"type": "text", "text": result.reply}]},
                ]
                return result.reply, full_history, result.render, result.trace

            # list(history), no history a secas -- si no, agent.messages
            # queda apuntando al MISMO objeto que session_state.history, y
            # cada .append() de agent.send() lo muta en el momento, dejando
            # len(history) igual a len(full_history) después de la llamada
            # (build_render siempre recibía [] y caía en kind="text").
            agent.messages = list(history)
            reply = await agent.send(user_message)
        full_history = serialize_messages(agent.messages)
        render = build_render(full_history[history_len:])
        return reply, full_history, render, []

    return asyncio.run(_call())


def _render_subagent_trace(trace: list) -> None:
    if not trace:
        return
    with st.expander("🧩 Cómo trabajó el equipo (coordinador + subagentes)"):
        for r in trace:
            st.markdown(f"**{r.role}**")
            st.caption(f"Objetivo: {r.goal}")
            st.caption(f"Criterio de calidad: {r.quality_criteria}")
            if r.tool_calls:
                st.caption("Tools usadas: " + ", ".join(f"`{t}`" for t in r.tool_calls))
            st.markdown(r.summary)
            if r.structured_data:
                st.json(r.structured_data, expanded=False)
            st.divider()


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
st.caption("Agente Pokédex sobre datos reales de Gold -- Databricks App, sin Vercel de por medio.")

if "history" not in st.session_state:
    st.session_state.history = []  # agent.messages serializado, fuente de verdad para el próximo turno
if "turns" not in st.session_state:
    st.session_state.turns = []  # [(role, texto_o_None, render_dict_o_None, trace)] para pintar la conversación

for role, text, render, trace in st.session_state.turns:
    with st.chat_message(role):
        # Tarjeta ANCLA primero, comentario de Oak DESPUÉS (reglas/04-
        # frontend.md) -- invertido daba una prosa repitiendo en bullets
        # lo mismo que la tarjeta ya muestra, antes de que la tarjeta
        # apareciera.
        if render is not None:
            try:
                _render_turn(render)
            except Exception as e:
                st.exception(e)
        if text:
            st.markdown(text)
        _render_subagent_trace(trace)

user_message = st.chat_input("Preguntale algo a Profesor Oak (ficha, comparación, matchups de tipo)...")

if user_message:
    st.session_state.turns.append(("user", user_message, None, []))
    with st.chat_message("user"):
        st.markdown(user_message)

    multi_agent = st.session_state.force_multi_agent or should_use_multi_agent(user_message)

    with st.chat_message("assistant"):
        spinner_text = (
            "El equipo de Profesor Oak está trabajando (coordinador + subagentes)..."
            if multi_agent
            else "Profesor Oak está revisando la Pokedex..."
        )
        with st.spinner(spinner_text):
            try:
                reply, full_history, render, trace = _run_turn(user_message, st.session_state.history, multi_agent)
            except Exception as e:
                st.error(f"Error hablando con pokedex-mcp-server: {e!r}")
            else:
                st.session_state.history = full_history
                # Tarjeta primero, comentario de Oak después -- ver nota
                # arriba en el loop de historial.
                try:
                    _render_turn(render)
                except Exception as e:
                    st.exception(e)
                st.markdown(reply)
                _render_subagent_trace(trace)
                st.session_state.turns.append(("assistant", reply, render, trace))
