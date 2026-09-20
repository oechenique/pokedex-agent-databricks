"""Convierte agent.Agent().messages (mezcla de dicts propios y content
blocks tipados del SDK de anthropic) a JSON plano. Copia literal de
backend/serialize.py -- no toca agent/agent.py, self.messages es una
lista Python común y corriente, esto solo la serializa en el borde.
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
