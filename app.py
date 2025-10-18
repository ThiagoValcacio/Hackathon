from __future__ import annotations
import streamlit as st
from openai import OpenAI
from api.openai_client import OpenAIClientFactory
from agents.refiner_agent import refine_transcript_to_ebook
from agents.qa_agent import answer_with_ebook
from models.refiner_models import RefinerRequest
from models.qa_models import QARequest
from utils.io_utils import read_txt, save_txt
from utils.flow_utils import normalize_none_answer

import os
for var in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY"):
    os.environ.pop(var, None)

st.set_page_config(page_title="Ebook Q&A (OpenAI + Streamlit)", page_icon="📚", layout="centered")

if "step" not in st.session_state:
    st.session_state.step = 1
if "api_key" not in st.session_state:
    st.session_state.api_key = None
if "ebook_text" not in st.session_state:
    st.session_state.ebook_text = None
if "last_answer" not in st.session_state:
    st.session_state.last_answer = None

st.title("📚 Ebook Q&A")
api_key_input = ""

# ----------------- Etapa 1: Token -----------------
if st.session_state.step == 1:
    st.subheader("Etapa 1 – Informe sua OpenAI API Key")
    with st.form("form_api_key"):
        api_key_input = st.text_input("Cole sua OpenAI API Key", type="password")
        submitted = st.form_submit_button("Continuar")
        if submitted:
            if not api_key_input.strip():
                st.error("Informe a API Key.")
            else:
                st.session_state.api_key = api_key_input.strip()
                st.session_state.step = 2
                st.rerun()

# ----------------- Etapa 2: Upload (TXT ou PDF) -----------------
elif st.session_state.step == 2:
    st.subheader("Etapa 2 – Envie o arquivo (.txt ou .pdf) com a transcrição")

    uploaded = st.file_uploader(
        "Selecione um arquivo .txt ou .pdf",
        type=["txt", "pdf"],
        accept_multiple_files=False
    )

    if uploaded is not None:
        from utils.io_utils import read_uploaded_text_or_pdf, save_txt
        try:
            raw_text = read_uploaded_text_or_pdf(uploaded, uploaded.name)
            st.success(f"Arquivo carregado: {uploaded.name}")
        except Exception as e:
            st.error(f"Falha ao ler arquivo: {e}")
            raw_text = None

        if raw_text and st.button("Gerar Ebook"):
            try:
                from api.openai_client import OpenAIClientFactory
                from models.refiner_models import RefinerRequest
                from agents.refiner_agent import refine_transcript_to_ebook

                # usa a chave guardada na Etapa 1; nada de st.secrets aqui
                client = OpenAIClientFactory.build(st.session_state.api_key)

                with st.spinner("Gerando ebook a partir da transcrição..."):
                    req = RefinerRequest(transcript_text=raw_text)
                    out = refine_transcript_to_ebook(client, req)

                safe_base = (uploaded.name or "ebook").rsplit(".", 1)[0]
                out_path = save_txt(out.ebook_text, f"{safe_base}_refinado.txt")

                st.session_state.ebook_text = out.ebook_text
                st.success(f"Ebook gerado e salvo em: {out_path}")
                st.session_state.step = 3
                st.rerun()
            except Exception as e:
                st.error(f"Falha: {e}")
    else:
        st.info("Envie um arquivo .txt ou .pdf para prosseguir.")

# Etapa 3 – Q&A
elif st.session_state.step == 3:
    st.subheader("Etapa 3 – Perguntas sobre o Ebook")
    if not st.session_state.ebook_text:
        st.warning("Nenhum ebook carregado. Volte à Etapa 2.")
    else:
        q = st.text_area("Digite sua pergunta", height=120)
        if st.button("Responder"):
            if not q.strip():
                st.error("Escreva uma pergunta.")
            else:
                try:
                    client = OpenAIClientFactory.build(st.session_state.api_key)
                    with st.spinner("Consultando o material..."):
                        req = QARequest(
                            ebook_text=st.session_state.ebook_text,
                            question=q.strip()
                        )
                        out = answer_with_ebook(client, req)
                    st.session_state.last_answer = normalize_none_answer(out.answer)
                except Exception as e:
                    st.error(f"Erro na resposta: {e}")

        if st.session_state.last_answer is None:
            st.info("Não há informações suficientes no material fornecido.")
        else:
            st.markdown("### Resposta")
            st.write(st.session_state.last_answer)

            opt = st.radio(
                "Selecione uma opção",
                ["Enviar nova pergunta", "Salvar resposta em .txt", "Sair"],
                index=0
            )
            if opt == "Enviar nova pergunta":
                st.session_state.last_answer = None
                st.rerun()
            elif opt == "Salvar resposta em .txt":
                try:
                    p = save_txt(st.session_state.last_answer, "resposta_ebook.txt")
                    st.success(f"Resposta salva em: {p}")
                except Exception as e:
                    st.error(f"Erro ao salvar resposta: {e}")
            elif opt == "Sair":
                st.info("Sessão encerrada.")
