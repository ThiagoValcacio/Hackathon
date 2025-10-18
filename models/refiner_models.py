from __future__ import annotations
from typing import Annotated, Optional, Literal
from pydantic import BaseModel, Field, StringConstraints

NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

class RefinerRequest(BaseModel):
    transcript_text: NonEmptyStr = Field(
        ..., description="Transcrição original (bruta) em texto."
    )
    language: Literal["pt", "auto"] = Field(
        "pt", description="Idioma do texto final. 'pt' força português; 'auto' tenta preservar o original."
    )

class RefinerOutput(BaseModel):
    ebook_text: NonEmptyStr = Field(
        ..., description="Texto contínuo e coeso (ebook) já refinado."
    )
    tokens_used: Optional[int] = None
    had_redactions: Optional[bool] = None
