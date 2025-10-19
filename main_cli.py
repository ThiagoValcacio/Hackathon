#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations
import os
import sys
import time
import random
from pathlib import Path
from typing import Optional, List

# ====== Imports do seu projeto ======
from api.openai_client import OpenAIClientFactory
from agents.refiner_agent import refine_transcript_to_ebook
from agents.qa_agent import answer_with_ebook
from models.refiner_models import RefinerRequest
from models.qa_models import QARequest

# Utils opcionais
try:
    from utils.io_utils import save_txt  # não será usado diretamente; manter por compatibilidade
except Exception:
    save_txt = None

try:
    from utils.flow_utils import normalize_none_answer
except Exception:
    def normalize_none_answer(s: Optional[str]) -> str:
        return (s or "").strip()

# ---------- Higienização de proxies ----------
for var in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY"):
    os.environ.pop(var, None)

# ---------- Pasta de Downloads e salvamento ----------
def get_downloads_dir() -> Path:
    """
    Retorna a pasta de Downloads do usuário.
    Fallback padrão: ~/Downloads (Windows/macOS/Linux).
    Cria a pasta se não existir.
    """
    downloads = Path.home() / "Downloads"
    try:
        downloads.mkdir(parents=True, exist_ok=True)
    except Exception:
        # Se falhar por algum motivo, usa diretório atual
        downloads = Path.cwd()
    return downloads

def save_text_to_downloads(content: str, filename: str) -> Path:
    """
    Salva 'content' como UTF-8 em ~/Downloads/filename (ou cwd, se não houver Downloads).
    """
    target_dir = get_downloads_dir()
    p = (target_dir / filename).resolve()
    p.write_text(content or "", encoding="utf-8")
    return p

# ---------- Leitura de TXT/PDF ----------
def read_text_or_pdf(path: Path) -> str:
    """
    Lê .txt ou .pdf e retorna texto em UTF-8.
    Para PDF usa pypdf (texto extraível).
    """
    suffix = path.suffix.lower()
    if suffix == ".txt":
        return path.read_text(encoding="utf-8", errors="ignore")

    if suffix == ".pdf":
        try:
            from pypdf import PdfReader  # pip install pypdf
        except Exception:
            print("[ERRO] Falta a dependência 'pypdf'. Instale com: pip install pypdf", file=sys.stderr)
            raise
        reader = PdfReader(str(path))
        parts = []
        for pg in reader.pages:
            try:
                parts.append(pg.extract_text() or "")
            except Exception:
                parts.append("")
        text = "\n".join(parts).strip()
        if not text:
            print(f"[AVISO] Extração vazia em: {path.name}. PDF pode ser imagem/OCR.", file=sys.stderr)
        return text

    raise ValueError(f"Formato não suportado: {suffix}. Use .txt ou .pdf")

def clear_screen() -> None:
    try:
        os.system("cls" if os.name == "nt" else "clear")
    except Exception:
        pass

def header(titulo: str) -> None:
    print("=" * 80)
    print(titulo)
    print("=" * 80)

# ---------- Seleção de arquivos (diálogo nativo) ----------
def select_files_with_dialog() -> List[str]:
    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception as e:
        print(f"[ERRO] Tkinter indisponível: {e}.", file=sys.stderr)
        return []
    root = tk.Tk()
    root.withdraw()
    root.update()
    filetypes = [
        ("Text files", "*.txt"),
        ("PDF files", "*.pdf"),
        ("All supported", "*.txt;*.pdf"),
        ("All files", "*.*"),
    ]
    paths = filedialog.askopenfilenames(
        title="Selecione 1 ou mais arquivos (.txt/.pdf)",
        filetypes=filetypes,
    )
    root.destroy()
    return list(paths) if paths else []

# ---------- Retry/backoff para chamadas do agente ----------
def call_with_retry(fn, *args, max_retries: int = 5, base_delay: float = 1.5, jitter: float = 0.4, **kwargs):
    """
    Executa 'fn(*args, **kwargs)' com backoff exponencial + jitter.
    Trata erros transitórios (520/502/503/504/timeout).
    """
    for attempt in range(1, max_retries + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            msg = str(e).lower()
            transient = any(code in msg for code in [" 520", " 502", " 503", " 504", "timeout", "connection reset", "temporarily unavailable"])
            if not transient or attempt == max_retries:
                raise
            delay = (base_delay * (2 ** (attempt - 1))) * (1 + random.uniform(-jitter, jitter))
            delay = max(0.6, delay)
            print(f"[AVISO] Falha transitória ({e}). Tentativa {attempt}/{max_retries}. Aguardando {delay:.1f}s ...")
            time.sleep(delay)

# ---------- Fluxo principal ----------
def main() -> None:
    clear_screen()
    header("Ebook Q&A (Terminal) — 1 ebook por material, sem chunk e sem consolidate")

    # 1) API Key
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        api_key = input("Informe sua OpenAI API Key: ").strip()
    if not api_key:
        print("[ERRO] API Key não informada. Encerrando.")
        sys.exit(1)

    # 2) Seleção de arquivos
    print("\nEtapa 1 – Selecione 1 ou mais arquivos base (.txt ou .pdf) no diálogo que será aberto.")
    files = select_files_with_dialog()
    if not files:
        print("[ERRO] Nenhum arquivo selecionado. Encerrando.")
        sys.exit(1)

    # 3) Pergunta única: tratar/refinar ou não
    clear_screen()
    header("Configuração do Material")
    print("Como deseja prosseguir para TODOS os arquivos selecionados?\n")
    print("  1) Tratar/Refinar (usar agente para limpar e organizar em ebook)")
    print("  2) Não tratar (usar conteúdo original como ebook)\n")
    choice = input("Escolha 1 ou 2: ").strip()
    if choice not in ("1", "2"):
        print("[ERRO] Opção inválida.")
        sys.exit(1)

    client = OpenAIClientFactory.build(api_key)

    # 4) Processar cada material (um por arquivo). Um bloco por material.
    generated_outputs: List[Path] = []
    all_ebooks_text: List[str] = []

    for idx, f in enumerate(files, 1):
        p = Path(f).expanduser().resolve()
        print("\n" + "-" * 80)
        print(f"[INFO] Processando material {idx}/{len(files)}: {p.name}")
        print("-" * 80)

        try:
            raw_text = read_text_or_pdf(p)
            if not raw_text.strip():
                print(f"[AVISO] Texto vazio em {p.name}; material ignorado.")
                continue
        except Exception as e:
            print(f"[AVISO] Falha na leitura de {p.name}: {e}")
            continue

        if choice == "2":
            # Não tratar: salva como está na pasta Downloads
            final_text = raw_text.strip()
            out_name = f"{p.stem}_original.txt"
            out_path = save_text_to_downloads(final_text, out_name)
            generated_outputs.append(out_path)
            all_ebooks_text.append(final_text)
            print(f"[OK] Ebook (sem tratamento) salvo: {out_path}")
        else:
            # Tratar: UM bloco por material
            def _do_refine():
                req = RefinerRequest(transcript_text=raw_text)
                return refine_transcript_to_ebook(client, req)

            try:
                out = call_with_retry(_do_refine, max_retries=5, base_delay=1.5)
                final_text = (out.ebook_text or "").strip()
                if not final_text:
                    print(f"[AVISO] Agente não retornou texto para {p.name}; usando original.")
                    final_text = raw_text.strip()
            except Exception as e:
                print(f"[AVISO] Falha no tratamento de {p.name} ({e}); usando original.")
                final_text = raw_text.strip()

            out_name = f"{p.stem}_refinado.txt"
            out_path = save_text_to_downloads(final_text, out_name)
            generated_outputs.append(out_path)
            all_ebooks_text.append(final_text)
            print(f"[OK] Ebook refinado salvo: {out_path}")

    if not all_ebooks_text:
        print("\n[ERRO] Nenhum ebook disponível para Q&A. Encerrando.")
        sys.exit(1)

    # 5) Q&A com TODOS os ebooks (concatenação simples)
    clear_screen()
    header("Perguntas e Respostas — usando TODOS os ebooks gerados")
    sep = "\n\n" + ("-" * 80) + "\n"
    combined_ebooks = sep.join(all_ebooks_text).strip()

    last_answer: Optional[str] = None

    while True:
        print("\nOpções:")
        print("  1) Fazer pergunta (usa todos os ebooks carregados)")
        print("  2) Salvar última resposta em .txt (Downloads)")
        print("  3) Sair")
        opt = input("Selecione uma opção [1-3]: ").strip()

        if opt == "1":
            q = input("\nDigite sua pergunta: ").strip()
            if not q:
                print("[AVISO] Pergunta vazia; tente novamente.")
                continue
            try:
                req = QARequest(ebook_text=combined_ebooks, question=q)
                out = answer_with_ebook(client, req)
                if getattr(out, "has_content", False):
                    ans = normalize_none_answer(getattr(out, "answer", ""))
                    last_answer = ans.strip()
                    print("\n" + "-" * 80)
                    print("RESPOSTA")
                    print("-" * 80)
                    print(last_answer or "[Sem conteúdo]")
                    print("-" * 80)
                else:
                    last_answer = None
                    print("\n[INFO] Não há informações suficientes nos ebooks fornecidos.")
            except Exception as e:
                last_answer = None
                print(f"\n[ERRO] Falha ao obter resposta: {e}")

        elif opt == "2":
            if not last_answer:
                print("[AVISO] Não há resposta para salvar.")
                continue
            default_name = "resposta_ebook.txt"
            try:
                outp = save_text_to_downloads(last_answer, default_name)
                print(f"[OK] Resposta salva em: {outp}")
            except Exception as e:
                print(f"[ERRO] Falha ao salvar: {e}")

        elif opt == "3":
            print("\nSessão encerrada.")
            break

        else:
            print("[AVISO] Opção inválida.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nEncerrado pelo usuário.")
