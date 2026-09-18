"""Convierte agent.Agent().messages (mezcla de dicts propios y content
blocks tipados del SDK de anthropic) a JSON plano para mandar por HTTP, y
viceversa. No toca agent/agent.py -- self.messages es una lista Python
común y corriente, esto solo la serializa/deserializa en el borde HTTP.

La API de Claude acepta blocks como dict plano en `messages` (es el mismo
formato que viaja por el wire), así que el round-trip JSON -> dict -> vuelta
a la API funciona sin reconstruir tipos del SDK.
"""

from typing import Any


def to_jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [to_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {k: to_jsonable(v) for k, v in value.items()}
    return value


def serialize_messages(messages: list[dict]) -> list[dict]:
    return [to_jsonable(m) for m in messages]
