# 00 — Overview del proyecto

## Qué es esto
Plataforma de datos Pokémon en Databricks (Terraform + Medallion) con un agente Claude ("Profesor Oak") que consume la capa Gold vía MCP. El proyecto es, a la vez: pieza de portfolio de Data Engineering, y laboratorio práctico para el examen **CCA-F (Claude Certified Architect – Foundations)** — cada componente existe también porque ejercita algo puntual que entra en el examen.

## Principio rector
**El agente NO es el proyecto. El agente es la capa que consume una plataforma de datos ya curada.**
Si en algún momento el agente empieza a "inventar" lógica que debería vivir en Gold (cálculos, reglas de negocio), es señal de que algo está en la capa equivocada.

## Fuentes de datos (todas reales, sin scraping raro)
- **PokeAPI** (`pokeapi.co`) — stats base, tipos, habilidades, evoluciones, sprites y **official-artwork** (imagen). Gratis, sin key, sin restricción de uso comercial conocida.
- **pokemontcg.io** — cartas TCG, rareza, puntos, precios de mercado. Gratis con API key. Proyecto fan-made, no afiliado oficialmente a Nintendo/Game Freak — ver `04-guardrails-seguridad.md` si esto deja de ser solo portfolio.
- **Bulbapedia / wiki** — SOLO texto (lore, flavor text). **Nunca imágenes de ahí** — licencia CC BY-NC-SA (no comercial), choca con la idea de vender el proyecto.
- **Pokenots** — opcional, fase tardía (v2). No bloquea nada de lo de abajo.

## Las 4 capas del proyecto
```
Terraform (infra as code, desde el día 1)
        ↓
Databricks: Bronze → Silver → Gold  (con Data Quality gate)
        ↓
MCP Server en Databricks Apps (tools que consultan Gold)
        ↓
Agente (Claude Agent SDK) + Frontend (Vercel)
```

## Fases de trabajo (orden real, no el de un README)
1. ✅ Terraform + Bronze (prioridad: se acaban los días del workspace pago)
2. ✅ Silver + Gold + Data Quality gate
3. ✅ MCP server (tools + schemas) sobre Databricks Apps
4. ✅ Agente single-agent + hooks + structured output
5. ✅ Frontend (pivotado de Vercel a `oak_app/`, Databricks App en Streamlit -- reglas/07)
6. ✅ Multi-agente: orchestrator + subagents (`agent/orchestrator.py`, `agent/subagents.py`)
7. ⬜ `tests/` — casos reproducibles mapeados a los dominios del examen

Estado detallado, hallazgos y recursos vivos en Azure: `07-estado-actual.md`.

## Qué NO hacemos (y por qué, para que no se reintroduzca en otra sesión)
- ❌ Vector Search / embeddings para stats o matchups — son datos exactos y estructurados, no texto ambiguo. Es la trampa "vector store para un dato que debe estar siempre disponible", catalogada en la guía de estudio del CCA-F.
- ❌ Model Serving endpoint — es para hostear modelos ML propios, no aplica a orquestar un agente Claude.
- ❌ Contenedores/Dockerfile manuales — Databricks Apps corre desde `app.py` + `requirements.txt` + `app.yaml` opcional, sin que nosotros administremos containers.
- ❌ Multi-agente desde el arranque — primero single agent + tools + hooks + structured output funcionando, recién después orquestador.
