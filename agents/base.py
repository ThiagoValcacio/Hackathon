from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable, Generic, Optional, Sequence, Type, TypeVar

T = TypeVar("T")

@dataclass
class ModelSettings:
    store: bool = False
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    max_output_tokens: Optional[int] = None

class Agent(Generic[T]):
    def __init__(
        self,
        name: str,
        instructions: str,
        model: str,
        output_type: Optional[Type[T]] = None,
        model_settings: Optional[ModelSettings] = None,
        tools: Optional[Sequence[Callable[..., Any]]] = None,
    ) -> None:
        self.name = name
        self.instructions = instructions.strip()
        self.model = model
        self.output_type = output_type
        self.model_settings = model_settings or ModelSettings()
        self.tools = list(tools or [])

    def __repr__(self) -> str:
        return f"Agent(name={self.name}, model={self.model})"
