# claude_code/ — ejemplos reales, no tests de código

Dominio "Claude Code Config & Workflows" del examen CCA-F
(`reglas/06-ccaf-mapa-y-convenciones.md`): distinguir **AGENTS.md/CLAUDE.md**
(contexto siempre-vigente para el asistente que trabaja en el repo) de un
**hook** (enforcement real en tiempo de ejecución de la app) y de una
**rule con `paths:` scoped** (convención que aplica solo a una parte del
árbol). Los tres mecanismos existen en Claude Code; mezclar cuál va en
cuál es justo lo que este dominio evalúa. Tres ejemplos con archivos
reales de este mismo repo, no hipotéticos.

## 1. Esto va en `AGENTS.md` (raíz del repo)

Archivo real: [`AGENTS.md`](../../AGENTS.md).

```
Antes de cualquier tarea en este repo: leé reglas/00-overview.md y
reglas/07-estado-actual.md primero, en ese orden. reglas/ contiene las
decisiones de arquitectura ya tomadas (no las reinterpretes ni propongas
alternativas sin que se te pida explícitamente)...
```

**Por qué acá y no en un hook:** es contexto para el *asistente que
trabaja en el repo* (vos, en cualquier sesión futura), no una regla que
el sistema desplegado tenga que hacer cumplir en producción. No hay
ningún dato de usuario en juego, no hay nada que "nunca deba pasar" en
runtime -- es orientación de cómo abordar el trabajo. Vive en la raíz
porque aplica a **todo** el repo, sin excepción de carpeta.

## 2. Esto es un hook, no una instrucción de prompt

Archivo real: [`agent/hooks.py`](../../agent/hooks.py), función
`pre_tool_use`.

```python
async def pre_tool_use(tool_name: str, tool_input: dict, ctx: HookContext) -> None:
    generation = tool_input.get("generation")
    if generation is not None and not _is_valid_generation(generation):
        raise ToolBlocked(...)
    for field in POKEMON_NAME_FIELDS:
        name = tool_input.get(field)
        if not name:
            continue
        if not await _pokemon_exists(name, ctx):
            raise ToolBlocked(...)
```

**Por qué acá y no en `AGENTS.md`/system prompt:** `reglas/05-guardrails-
seguridad.md` lo dice explícito -- *"Nada que sea 'nunca debe pasar'
(ej. exponer una key, devolver un precio inventado como si fuera real)
se resuelve con una instrucción en el prompt por más enfática que
esté."* Un system prompt es una sugerencia fuerte que Claude puede, en
el peor caso, no seguir; un hook corre **antes** de que la tool real se
ejecute y puede bloquear la llamada por completo, pase lo que pase en el
razonamiento del modelo. `generation="banana"` o un nombre de pokemon
inexistente tienen que quedar bloqueados sí o sí -- eso es
`tests/hooks/test_hooks.py`, no una instrucción de personalidad.

## 3. Esto sería una rule con `paths:` scoped

`reglas/06-ccaf-mapa-y-convenciones.md` (tabla de convenciones) da el
ejemplo exacto para este repo:

> regla scoped a `mcp_server/tools/**` — "toda tool valida el nombre del
> pokemon contra Gold antes de pegarle a la API externa"

Este repo no tiene hoy un archivo `.claude/rules/` real (es un proyecto
chico, un solo colaborador) -- pero si el equipo creciera y alguien
tocara `mcp_server/` sin haber leído `reglas/03-agente-mcp.md` entero,
esa convención puntual (nunca `mcp_server/tools/**`, nunca todo el repo)
es exactamente lo que va en una `rule` con `paths: ["mcp_server/tools/**"]`
-- no en `AGENTS.md` (demasiado amplio, se aplicaría a `agent/`, `oak_app/`,
`terraform/` sin necesidad) ni en un hook (no es enforcement en runtime
de la app desplegada, es una convención de cómo escribir código nuevo
en esa carpeta).

## Resumen

| Mecanismo | Ejemplo real de este repo | Por qué ahí y no en otro lado |
|---|---|---|
| `AGENTS.md` | Leer `reglas/00`/`07` antes de cualquier tarea | Aplica a todo el repo, es para el asistente, no runtime |
| Hook (`PreToolUse`) | `hooks.pre_tool_use` bloqueando `generation`/pokemon inválido | "Nunca debe pasar" real, tiene que ejecutarse sí o sí, antes de la tool |
| Rule con `paths:` | Convención scoped a `mcp_server/tools/**` (reglas/06) | Aplica solo a una carpeta puntual, es convención de código, no enforcement de runtime |
