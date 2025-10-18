from __future__ import annotations
from pathlib import Path
from typing import BinaryIO, Optional

def read_txt(path: str) -> str:
    p = Path(path).expanduser().resolve()
    if not p.exists() or not p.is_file():
        raise FileNotFoundError(f"Arquivo não encontrado: {p}")
    if p.suffix.lower() != ".txt":
        raise ValueError("Forneça um caminho para um arquivo .txt")
    return p.read_text(encoding="utf-8", errors="ignore")

def save_txt(content: str, path: str) -> Path:
    p = Path(path).expanduser().resolve()
    p.write_text(content, encoding="utf-8")
    return p

# -------- PDF helpers (sem dependência pesada) --------
def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """
    Extrai texto de um PDF a partir dos bytes.
    Requer: pip install pypdf
    """
    from pypdf import PdfReader  # leve e suficiente para a maioria dos PDFs baseados em texto
    import io

    reader = PdfReader(io.BytesIO(pdf_bytes))
    parts = []
    for page in reader.pages:
        text = page.extract_text() or ""
        parts.append(text)
    return "\n".join(parts).strip()

def read_uploaded_text_or_pdf(uploaded_file: BinaryIO, filename: Optional[str]) -> str:
    """
    Lê conteúdo de um arquivo enviado no Streamlit (TXT ou PDF).
    - TXT: tenta utf-8 e fallback latin-1.
    - PDF: extrai com pypdf.
    """
    name = (filename or "").lower()
    data = uploaded_file.getvalue()  # bytes

    if name.endswith(".txt"):
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError:
            return data.decode("latin-1", errors="ignore")

    if name.endswith(".pdf"):
        text = extract_text_from_pdf_bytes(data)
        if not text:
            raise ValueError("Não foi possível extrair texto do PDF (pode ser um PDF somente-imagem).")
        return text

    raise ValueError("Formato não suportado. Envie .txt ou .pdf")
