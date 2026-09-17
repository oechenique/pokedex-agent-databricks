"""Cliente HTTP mínimo para PokeAPI -- reintentos con backoff, sin
dependencias más allá de `requests` (preinstalado en Databricks Runtime).

Los notebooks Bronze usan esto tal cual: nunca transforman el payload,
solo lo envuelven para guardarlo en Delta (reglas/01-datos-medallion.md).
"""

import time

import requests

DEFAULT_TIMEOUT_SECONDS = 30


def fetch_json(url: str, max_retries: int = 3, backoff_seconds: float = 1.0) -> dict:
    last_error = None
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=DEFAULT_TIMEOUT_SECONDS)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            last_error = exc
            time.sleep(backoff_seconds * (attempt + 1))
    raise RuntimeError(f"No se pudo obtener {url} tras {max_retries} intentos: {last_error}")


def fetch_all_resource_urls(list_endpoint: str, limit: int = 0) -> list:
    """Pagina un endpoint de listado de PokeAPI (ej. /pokemon, /type) y
    devuelve las URLs de detalle de cada recurso.

    limit=0 trae todo el catálogo. Cualquier otro valor corta apenas se
    junten esa cantidad de URLs -- útil para una corrida de prueba rápida
    sin esperar el dataset completo.
    """
    urls = []
    page_url = f"{list_endpoint}?limit=100&offset=0"
    while page_url:
        page = fetch_json(page_url)
        for item in page["results"]:
            urls.append(item["url"])
            if limit and len(urls) >= limit:
                return urls
        page_url = page["next"]
    return urls
