from __future__ import annotations
from typing import Optional
from openai import OpenAI
from models.refiner_models import RefinerRequest, RefinerOutput

_REFINER_SYSTEM = (
    "Você é um editor que transforma transcrições de aulas em um ebook limpo, "
    "coeso e contínuo. Remova trechos irrelevantes, estruture parágrafos e não invente fatos."
)

def _extract_text_from_responses(resp) -> Optional[str]:
    """
    Extrai o primeiro 'output_text' do objeto retornado pela API Responses.
    Compatível com o schema do openai>=1.40.
    """
    for item in getattr(resp, "output", []) or []:
        for c in getattr(item, "content", []) or []:
            if getattr(c, "type", None) == "output_text" and getattr(c, "text", None):
                return c.text
    # fallback bruto, se necessário
    try:
        return getattr(resp, "output_text", None) or getattr(resp, "text", None)
    except Exception:
        return None

def refine_transcript_to_ebook(client: OpenAI, req: RefinerRequest) -> RefinerOutput:
    """
    Refina a transcrição em um texto coeso de ebook.
    Usa `client.responses.create` quando disponível; caso contrário, usa `client.chat.completions.create`.
    """
    user_prompt = (
        "Você receberá abaixo a transcrição bruta de uma aula, em formato de texto ou também pode receber um material informativo e já organizado.\n"
        "Tarefas:\n"
        "1) Limpar e organizar em prosa contínua (formato de ebook).\n"
        "2) Remover trechos irrelevantes e repetições.\n"
        "3) Melhorar coesão e clareza, mantendo o conteúdo factual original.\n"
        "4) Não inventar fatos.\n\n"
        f"Transcrição:\n{req.transcript_text}"
    )

    # Caminho preferencial: Responses API (se existir no cliente)
    if hasattr(client, "responses"):
        resp = client.responses.create(
            model="gpt-4o-mini",
            input=[
                {"role": "system", "content": _REFINER_SYSTEM},
                {"role": "user", "content": user_prompt},
            ],
        )
        text = _extract_text_from_responses(resp)
        if not text:
            text = str(resp)
        return RefinerOutput(ebook_text=text.strip())

    # Fallback universal: Chat Completions
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": _REFINER_SYSTEM},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
    )
    text = resp.choices[0].message.content if resp.choices else ""
    return RefinerOutput(ebook_text=(text or "").strip())
