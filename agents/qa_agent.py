from __future__ import annotations
from openai import OpenAI
from models.qa_models import QARequest, QAOutput

DEFAULT_QA_MODEL = "gpt-4.1-mini"

_QA_SYSTEM = (
    "Você é um assistente acadêmico. Responda exclusivamente com base no ebook. "
    "Se não houver base suficiente, responda exatamente: "
    "\"Não há informações suficientes no material fornecido.\""
)

def answer_with_ebook(
    client: OpenAI,
    req: QARequest,
    model: str = DEFAULT_QA_MODEL,
) -> QAOutput:
    """
    Responde usando SOMENTE o ebook. Retorna QAOutput.
    """
    user_prompt = f"""
Conteúdo-base (ebook):
----- INÍCIO -----
{req.ebook_text}
----- FIM -----

Pergunta do usuário:
{req.question}

Instruções:
- Apoie-se apenas no conteúdo-base.
- Se não houver base suficiente, responda exatamente:
  "Não há informações suficientes no material fornecido."
""".strip()

    resp = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": _QA_SYSTEM},
            {"role": "user", "content": user_prompt},
        ],
    )
    answer_text = resp.output_text.strip()

    has_content = "não há informações suficientes no material fornecido" not in answer_text.lower()
    if req.fallback_on_insufficient == "none" and not has_content:
        return QAOutput(answer="", has_content=False)

    return QAOutput(answer=answer_text, has_content=has_content)
