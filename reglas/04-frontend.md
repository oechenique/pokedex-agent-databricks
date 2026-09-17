# 04 — Frontend

## Dónde vive
Vercel. Decisión tomada explícitamente para desacoplar el frontend del ciclo de vida de Azure/Databricks (que se apaga cuando se acaba el free tier). El front sigue vivo pase lo que pase con la infra de datos.

## Qué consume
El backend del front (API route en Vercel, o el propio agente vía Databricks App mientras esté vivo) — nunca pega directo a Databricks desde el browser, y nunca expone la key de Claude ni de pokemontcg.io al cliente.

## Formato de salida según el tipo de dato (Dominio 4 del examen, aplicado)
- **Un pokemon** → tarjeta: imagen (`image_url` de PokeAPI) + stats + tipos.
- **Comparación de dos pokemones** → tabla lado a lado, no prosa.
- **Matchups de tipo** → lista/badges, no párrafo largo.
- **Charla de Profesor Oak / lore** → texto normal.
No forzar todo a un único formato — la síntesis debe renderizar cada tipo apropiadamente.

## Imágenes — solo PokeAPI
Nunca imágenes de Bulbapedia (licencia CC BY-NC-SA, no comercial). Video de YouTube: diferido a v2, y si se agrega, siempre como **embed** (iframe), nunca descargado/rehosteado.

## Rate limiting
Frontend público → rate limit propio antes de pegarle al agente (que a su vez le pega a la API de Claude). Sin esto, un front abierto sin control de costo puede fundir el budget en un fin de semana.
