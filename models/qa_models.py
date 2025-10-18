from __future__ import annotations
from typing import Annotated, Optional, Literal
from pydantic import BaseModel, Field, StringConstraints

NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

class QARequest(BaseModel):
    ebook_text: NonEmptyStr = Field(..., description="Conteúdo-base refinado (ebook).")
    question: NonEmptyStr = Field(..., description="Pergunta do usuário.")
    fallback_on_insufficient: Literal["phrased", "none"] = Field(
        "phrased", description="Comportamento quando não houver base suficiente."
    )

class QAOutput(BaseModel):
    answer: str = Field(..., description="Resposta textual.")
    has_content: bool = Field(..., description="True se a resposta foi baseada no ebook.")
    tokens_used: Optional[int] = None
