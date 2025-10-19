from __future__ import annotations
from typing import Optional
from openai import OpenAI
from models.qa_models import QARequest, QAOutput

DEFAULT_QA_MODEL = "gpt-4.1-mini"

_QA_SYSTEM = (
    "Você é um assistente acadêmico. Responda exclusivamente com base no ebook ou no material da base de dados recebida. "
    "Se não houver base suficiente, responda exatamente: "
    "\"Não há informações suficientes no material fornecido.\""
)

_INSUFF_PHRASE = "Não há informações suficientes no material fornecido."

def _extract_text_from_responses(resp) -> Optional[str]:
    """
    Extrai o primeiro 'output_text' do objeto retornado pela API Responses (openai>=1.40).
    """
    for item in getattr(resp, "output", []) or []:
        for c in getattr(item, "content", []) or []:
            if getattr(c, "type", None) == "output_text" and getattr(c, "text", None):
                return c.text
    # Fallbacks defensivos (se a estrutura variar)
    return getattr(resp, "output_text", None) or getattr(resp, "text", None)

def _normalize_answer(txt: str) -> str:
    """
    Garante que, se não houver base suficiente, retornamos exatamente a frase exigida.
    """
    if not txt:
        return _INSUFF_PHRASE
    # Caso o modelo diga algo equivalente, normalizamos para a frase padrão.
    low = txt.strip().lower()
    if "não há informações suficientes" in low or "insuficiente" in low:
        return _INSUFF_PHRASE
    return txt.strip()

def answer_with_ebook(
    client: OpenAI,
    req: QARequest,
    model: str = DEFAULT_QA_MODEL,
) -> QAOutput:
    """
    Responde usando SOMENTE o ebook ou o material da base de dados recebida. Retorna QAOutput com controle estrito da mensagem de insuficiência.
    """
    user_prompt = (
        "Use exclusivamente o conteúdo-base abaixo para responder à pergunta. "
        "Se a resposta não puder ser fundamentada apenas no conteúdo-base, "
        f"responda exatamente: \"{_INSUFF_PHRASE}\"\n\n"
        "Conteúdo-base (ebook):\n----- INÍCIO -----\n"
        f"{req.ebook_text}\n"
        "----- FIM -----\n\n"
        "Pergunta do usuário:\n"
        f"{req.question}\n\n"
        "Instruções finais:\n"
        f"- Responda somente com base no conteúdo-base, procure exaustivamente a informação.\n"
        f"- Se não houver base suficiente, responda exatamente: \"{_INSUFF_PHRASE}\""
    )

    # Caminho preferencial: API Responses (se disponível)
    if hasattr(client, "responses"):
        resp = client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": _QA_SYSTEM},
                {"role": "user", "content": user_prompt},
            ],
        )
        answer_text = _extract_text_from_responses(resp) or ""
        answer_text = _normalize_answer(answer_text)
    else:
        # Fallback: Chat Completions (compatível com qualquer 1.x)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",  # ajuste aqui se desejar manter o mesmo modelo na rota antiga
            messages=[
                {"role": "system", "content": _QA_SYSTEM},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0,
        )
        answer_text = _normalize_answer(resp.choices[0].message.content if resp.choices else "")

    has_content = (answer_text != _INSUFF_PHRASE)

    if req.fallback_on_insufficient == "none" and not has_content:
        return QAOutput(answer="", has_content=False)

    return QAOutput(answer=answer_text, has_content=has_content)
