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
from pathlib import Path

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
        tmp_paths_to_cleanup = []  # se o util criar arquivos temporários, adicione-os aqui para limpeza

        try:
            # 1) Ler conteúdo em memória, sem persistir o arquivo de entrada
            raw_text = read_uploaded_text_or_pdf(uploaded, uploaded.name)
            st.success(f"Arquivo carregado: {uploaded.name}")
        except Exception as e:
            st.error(f"Falha ao ler arquivo: {e}")
            raw_text = None

        if raw_text:
            # Pergunta obrigatória: o material precisa ser refinado?
            st.markdown("#### Como deseja prosseguir?")
            material_type = st.radio(
                "O arquivo enviado é:",
                [
                    "Nota de aula/transcrição (precisa ser refinado em Material Tratado)",
                    "Material já Tratado (Sem necessidade de Refinamento)"
                ],
                index=0,
                horizontal=False,
            )

            colA, colB = st.columns(2)
            with colA:
                prosseguir = st.button("Prosseguir")
            with colB:
                cancelar = st.button("Cancelar")

            if cancelar:
                # volta ao estado inicial desta etapa
                st.experimental_rerun()

            if prosseguir:
                if material_type.startswith("Material já Tratado"):
                    # Pular agente: usar texto como está
                    st.session_state.ebook_text = raw_text
                    st.success("Material carregado. Indo para a Etapa 3.")
                    st.session_state.step = 3
                    st.rerun()
                else:
                    # 2) Geração do ebook (mantendo apenas o resultado final)
                    try:
                        from api.openai_client import OpenAIClientFactory
                        from models.refiner_models import RefinerRequest
                        from agents.refiner_agent import refine_transcript_to_ebook

                        client = OpenAIClientFactory.build(st.session_state.api_key)

                        with st.spinner("Gerando ebook a partir da transcrição..."):
                            req = RefinerRequest(transcript_text=raw_text)
                            out = refine_transcript_to_ebook(client, req)

                        # 3) Salvar apenas o ebook gerado (arquivo final do usuário)
                        safe_base = (uploaded.name or "ebook").rsplit(".", 1)[0]
                        out_path = save_txt(out.ebook_text, f"{safe_base}_refinado.txt")

                        # 4) Atualizar estado e seguir
                        st.session_state.ebook_text = out.ebook_text
                        st.success(f"Ebook gerado e salvo em: {out_path}")
                        st.session_state.step = 3
                        st.rerun()

                    except Exception as e:
                        st.error(f"Falha: {e}")

                    finally:
                        # 5) Limpeza de quaisquer arquivos temporários criados durante o processo
                        # Se em algum ponto você persistiu o arquivo de entrada em disco, remova aqui.
                        # Exemplo:
                        # for p in tmp_paths_to_cleanup:
                        #     try:
                        #         Path(p).unlink(missing_ok=True)
                        #     except Exception:
                        #         pass
                        pass
    else:
        st.info("Envie um arquivo .txt ou .pdf para prosseguir.")

# Etapa 3 – Q&A
elif st.session_state.step == 3:
    st.subheader("Etapa 3 – Perguntas sobre o Ebook")

    if not st.session_state.get("ebook_text"):
        st.warning("Nenhum ebook carregado. Volte à Etapa 2.")
    else:
        # Campo de pergunta
        q = st.text_area("Digite sua pergunta", height=120)

        # Botão para disparar a resposta
        if st.button("Responder"):
            if not q or not q.strip():
                st.error("Escreva uma pergunta.")
            else:
                try:
                    from api.openai_client import OpenAIClientFactory
                    from models.qa_models import QARequest
                    from agents.qa_agent import answer_with_ebook
                    from utils.io_utils import save_txt

                    client = OpenAIClientFactory.build(st.session_state.api_key)

                    with st.spinner("Consultando o material..."):
                        req = QARequest(
                            ebook_text=st.session_state.ebook_text,
                            question=q.strip(),
                            # se existir este campo no seu modelo:
                            # fallback_on_insufficient="none"
                        )
                        out = answer_with_ebook(client, req)
                        # out é QAOutput(answer: str, has_content: bool)

                    # Comentário original: "QARequest sem has_content como atributo..."
                    # Correção: quem tem 'has_content' é o QAOutput (out.has_content).
                    if out.has_content:
                        # Normaliza a resposta (se você tiver essa função)
                        ans = normalize_none_answer(out.answer) if 'normalize_none_answer' in globals() else (out.answer or "")
                        st.session_state.last_answer = ans.strip() if ans else ""
                        st.session_state.qa_status = "ok"
                    else:
                        # Não há base suficiente no material
                        st.session_state.last_answer = None
                        st.session_state.qa_status = "insufficient"

                except Exception as e:
                    st.error(f"Erro na resposta: {e}")
                    st.session_state.last_answer = None
                    st.session_state.qa_status = "error"

        # Exibição condicional do resultado
        # Comentário original: "Aqui nesse IF use isso."
        if st.session_state.get("last_answer") is None:
            # Caso 'insufficient' ou erro, exibe a mensagem canônica
            if st.session_state.get("qa_status") == "insufficient":
                st.info("Não há informações suficientes no material fornecido.")
            elif st.session_state.get("qa_status") == "error":
                st.warning("Falha ao obter resposta. Tente novamente.")
            else:
                # Estado inicial sem resposta ainda
                st.stop()
        else:
            # Há uma resposta válida e persistente no estado
            st.markdown("### Resposta")
            st.write(st.session_state.last_answer)

            # Seleção da ação (não executa nada ainda)
            opt = st.radio(
                "Selecione uma opção",
                ["Enviar nova pergunta", "Salvar resposta em .txt", "Recomeçar com outro conteúdo (voltar à Etapa 2)", "Sair"],
                index=0,
                horizontal=False,
            )

            # Botão de confirmação para efetivar a ação escolhida
            if st.button("Confirmar"):
                if opt == "Enviar nova pergunta":
                    st.session_state.last_answer = None
                    st.session_state.qa_status = None
                    # mantém step=3; usuário formula nova pergunta
                elif opt == "Salvar resposta em .txt":
                    st.markdown("#### Salvar resposta")
                    fname_default = "resposta_ebook.txt"
                    st.download_button(
                        label="Baixar .txt",
                        data=st.session_state.last_answer,
                        file_name=fname_default,
                        mime="text/plain",
                        use_container_width=True,
                    )
                elif opt == "Recomeçar com outro Conteúdo Base (voltar à Etapa 2)":
                    # limpa estado e volta para upload
                    st.session_state.last_answer = None
                    st.session_state.qa_status = None
                    st.session_state.ebook_text = None
                    st.session_state.step = 2
                    st.rerun()
                elif opt == "Sair":
                    st.info("Sessão encerrada.")