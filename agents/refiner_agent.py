from __future__ import annotations
from openai import OpenAI
from models.refiner_models import RefinerRequest, RefinerOutput

DEFAULT_REFINER_MODEL = "gpt-4.1-mini"

_REFINER_SYSTEM = (
    "Você é um editor que transforma transcrições de aulas em um ebook limpo, "
    "coeso e contínuo. Remova trechos irrelevantes, estruture parágrafos e não invente fatos."
)

def refine_transcript_to_ebook(client: OpenAI, req: RefinerRequest, model: str = DEFAULT_REFINER_MODEL) -> RefinerOutput:
    user_prompt = f"""
Você recebe um arquivo .txt que representa a gravação de uma aula...

Transcrição:
{req.transcript_text}
""".strip()

    resp = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": _REFINER_SYSTEM},
            {"role": "user", "content": user_prompt},
        ],
    )
    return RefinerOutput(ebook_text=resp.output_text.strip())
