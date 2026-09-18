"""Rate limit placeholder (reglas/04-frontend.md: "Frontend público -> rate
limit propio antes de pegarle al agente"). En memoria, por proceso -- no
sobrevive a un cold start ni se comparte entre instancias serverless. Alcanza
para esta fase; si el front se vuelve público de verdad, esto pasa a un
store compartido (Vercel KV / Upstash), no a este dict.
"""

import time

_WINDOW_SECONDS = 60
_MAX_REQUESTS = 10

_hits: dict[str, list[float]] = {}


def check_rate_limit(key: str) -> bool:
    """True si `key` todavía tiene cupo en la ventana actual; False si se
    pasó y hay que rechazar la request con 429."""
    now = time.time()
    window_start = now - _WINDOW_SECONDS
    hits = [t for t in _hits.get(key, []) if t > window_start]
    if len(hits) >= _MAX_REQUESTS:
        _hits[key] = hits
        return False
    hits.append(now)
    _hits[key] = hits
    return True
