# 05 — Guardrails y seguridad

## Guardrail de dominio
Si preguntan algo fuera de Pokémon, el agente redirige hacia una recomendación pokemónica relacionada en vez de un rechazo seco — mismo patrón de diseño que el asesor de turismo.

## Enforcement real vs. prompt
Nada que sea "nunca debe pasar" (ej. exponer una key, devolver un precio inventado como si fuera real) se resuelve con una instrucción en el prompt por más enfática que esté. Va en la tool (validación server-side) o en un hook (`PreToolUse`/`PostToolUse`), no en texto.

## Secrets
- `.gitignore` desde el primer commit: `*.tfstate`, `*.tfstate.backup`, `*.tfplan`, `.env`, cualquier archivo con la Claude API key o la de pokemontcg.io.
- Keys en variables de entorno / Databricks Secrets, nunca hardcodeadas.
- Pre-commit hook (`gitleaks` / `detect-secrets`) como segunda red — no confiar solo en acordarse.

## IP / licencias (por si esto deja de ser solo portfolio)
- **PokeAPI**: datos y sprites/artwork sin restricción de uso comercial conocida — la fuente de imágenes por defecto.
- **Bulbapedia**: solo texto, nunca imágenes (CC BY-NC-SA, no comercial).
- **pokemontcg.io**: proyecto fan-made, no afiliado oficialmente a Nintendo/Game Freak/The Pokémon Company. Para portfolio y estudio, sin problema. **Si en algún momento se plantea monetizar** el producto usando marca/personajes Pokémon, eso es una decisión de negocio aparte que hay que resolver antes de cobrar un mango — no bloquea nada de lo que estamos construyendo ahora.

## Free tier / uso comercial de Databricks
La Databricks Free Edition (la perpetua, no el trial de Azure) prohíbe explícitamente uso comercial en sus términos. Mientras el proyecto sea portfolio/estudio, no aplica. Si se vuelve un producto real, va a necesitar un workspace pago sostenido, no Free Edition.
