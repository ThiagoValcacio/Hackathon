from __future__ import annotations

def normalize_none_answer(answer: str | None) -> str | None:
    if answer is None:
        return None
    s = answer.strip()
    if not s:
        return None
    if "não há informações suficientes" in s.lower():
        return None
    return s
