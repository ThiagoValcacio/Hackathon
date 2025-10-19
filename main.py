from __future__ import annotations
import os
import io
from pathlib import Path
from typing import Optional
import flet as ft

# ===== Seus módulos (iguais aos do projeto) =====
from api.openai_client import OpenAIClientFactory
from agents.refiner_agent import refine_transcript_to_ebook
from agents.qa_agent import answer_with_ebook
from models.refiner_models import RefinerRequest
from models.qa_models import QARequest
from utils.io_utils import read_uploaded_text_or_pdf
from utils.flow_utils import normalize_none_answer

# Remove proxies, como no Streamlit
for var in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY"):
    os.environ.pop(var, None)

# ===== Estado global =====
class AppState:
    def __init__(self):
        self.step: int = 1
        self.api_key: Optional[str] = None
        self.ebook_text: Optional[str] = None
        self.last_answer: Optional[str] = None
        self.qa_status: Optional[str] = None   # "ok" | "insufficient" | "error"
        self.uploaded_file_name: Optional[str] = None
        self.selected_file: Optional[ft.FilePickerFile] = None  # guarda seleção da etapa 2

STATE = AppState()

# ===== Util =====
def toast(page: ft.Page, msg: str):
    page.snack_bar = ft.SnackBar(ft.Text(msg))
    page.snack_bar.open = True
    page.update()

def save_txt_only(content: str, file_name_no_ext: str) -> Path:
    p = Path(file_name_no_ext).with_suffix(".txt")
    p.write_text(content, encoding="utf-8")
    return p

# ===== Etapa 1 =====
def view_step1(page: ft.Page):
    page.title = "Ebook Q&A (OpenAI + Flet)"

    title = ft.Text("📚 Ebook Q&A", size=26, weight=ft.FontWeight.BOLD)
    subtitle = ft.Text("Etapa 1 – Informe sua OpenAI API Key", size=18)

    api_key_field = ft.TextField(
        label="Cole sua OpenAI API Key",
        password=True,
        can_reveal_password=True,
        value=STATE.api_key or "",
        width=520,
    )

    def on_continue(e):
        key = (api_key_field.value or "").strip()
        if not key:
            toast(page, "Informe a API Key.")
            return
        STATE.api_key = key
        STATE.step = 2
        route_to_step(page)

    page.add(
        ft.Column(
            [title, subtitle, api_key_field, ft.ElevatedButton("Continuar", on_click=on_continue)],
            horizontal_alignment=ft.CrossAxisAlignment.START,
            spacing=18,
        )
    )

# ===== Etapa 2 =====
def view_step2(page: ft.Page):
    """
    Fluxo:
    - Selecionar arquivo (FilePicker)
    - Escolher tipo (radio)
    - Clicar "COnfirmar"
        * Se "pronto": ler texto e ir à Etapa 3
        * Se "refinar": chamar agente, salvar texto tratado e ir à Etapa 3
    """
    subtitle = ft.Text("Etapa 2 – Envie o arquivo (.txt ou .pdf) com a transcrição", size=18)

    selected_lbl = ft.Text("Nenhum arquivo selecionado.")
    status_lbl = ft.Text("")  # mensagens de progresso/erro

    def on_file_picked(e: ft.FilePickerResultEvent):
        if e.files:
            STATE.selected_file = e.files[0]
            STATE.uploaded_file_name = STATE.selected_file.name
            selected_lbl.value = f"Selecionado: {STATE.selected_file.name}"
            status_lbl.value = ""
        else:
            STATE.selected_file = None
            STATE.uploaded_file_name = None
            selected_lbl.value = "Nenhum arquivo selecionado."
            status_lbl.value = ""
        page.update()

    # Evita adicionar múltiplos pickers ao overlay se o usuário navegar entre etapas
    page.overlay.clear()
    file_picker = ft.FilePicker(on_result=on_file_picked)
    page.overlay.append(file_picker)

    pick_btn = ft.ElevatedButton(
        "Selecionar TXT/PDF",
        on_click=lambda e: file_picker.pick_files(
            allow_multiple=False,
            allowed_extensions=["txt", "pdf"],
        ),
    )

    material_radio = ft.RadioGroup(
        value="refinar",
        content=ft.Column(
            controls=[
                ft.Radio(
                    value="refinar",
                    label="Nota de aula/transcrição (precisa ser refinado em Material Tratado)",
                ),
                ft.Radio(
                    value="pronto",
                    label="Material já Tratado (Sem necessidade de Refinamento)",
                ),
            ],
            spacing=4,
        ),
    )

    def on_cancel(e):
        STATE.selected_file = None
        STATE.uploaded_file_name = None
        STATE.ebook_text = None
        selected_lbl.value = "Nenhum arquivo selecionado."
        status_lbl.value = ""
        page.update()

    def on_confirm(e):
        try:
            if STATE.selected_file is None:
                toast(page, "Selecione um arquivo antes.")
                return

            sel = STATE.selected_file
            if not sel.path:
                toast(page, "Arquivo sem caminho local disponível. Execute em modo desktop.")
                return

            # Leitura -> BytesIO para compatibilidade com seu util
            with open(sel.path, "rb") as f:
                data = f.read()
            name = sel.name or Path(sel.path).name
            raw_text = read_uploaded_text_or_pdf(io.BytesIO(data), name)

            STATE.uploaded_file_name = name
            selected_lbl.value = f"Arquivo carregado: {name}"
            page.update()

            choice = material_radio.value
            if choice == "pronto":
                STATE.ebook_text = raw_text
                STATE.step = 3
                route_to_step(page)
                return

            # Refinamento
            status_lbl.value = "Gerando ebook a partir da transcrição..."
            page.update()

            client = OpenAIClientFactory.build(STATE.api_key)
            req = RefinerRequest(transcript_text=raw_text)
            out = refine_transcript_to_ebook(client, req)

            safe_base = (name or "ebook").rsplit(".", 1)[0]
            out_path = save_txt_only(out.ebook_text, f"{safe_base}_refinado")
            STATE.ebook_text = out.ebook_text
            status_lbl.value = f"Ebook gerado e salvo em: {out_path}"
            page.update()

            STATE.step = 3
            route_to_step(page)
            return

        except Exception as ex:
            status_lbl.value = f"Falha: {ex}"
            page.update()

    page.add(
        ft.Column(
            [
                subtitle,
                pick_btn,
                selected_lbl,
                ft.Text("Como deseja prosseguir?"),
                material_radio,
                ft.Row(
                    [
                        ft.FilledButton("COnfirmar", on_click=on_confirm),
                        ft.OutlinedButton("Cancelar", on_click=on_cancel),
                    ],
                    spacing=10,
                ),
                ft.Divider(),
                status_lbl,
            ],
            horizontal_alignment=ft.CrossAxisAlignment.START,
            spacing=14,
        )
    )

# ===== Etapa 3 =====
def view_step3(page: ft.Page):
    subtitle = ft.Text("Etapa 3 – Perguntas sobre o Ebook", size=18)

    if not STATE.ebook_text:
        page.add(
            ft.Column(
                [
                    subtitle,
                    ft.Text("Nenhum ebook carregado. Volte à Etapa 2."),
                    ft.ElevatedButton(
                        "Voltar à Etapa 2",
                        on_click=lambda e: (setattr(STATE, "step", 2), route_to_step(page)),
                    ),
                ],
                spacing=12,
            )
        )
        return

    question_field = ft.TextField(
        label="Digite sua pergunta",
        multiline=True,
        min_lines=5,
        max_lines=12,
        width=760,
    )

    result_title = ft.Text("")
    result_markdown = ft.Markdown(
        value="",
        selectable=True,
        extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
        visible=False,
        width=820,
    )
    msg_lbl = ft.Text("")  # removido uso de ft.colors

    action_radio = ft.RadioGroup(
        value="new",
        content=ft.Column(
            controls=[
                ft.Radio(value="new", label="Enviar nova pergunta"),
                ft.Radio(value="save", label="Salvar resposta em .txt"),
                ft.Radio(value="restart", label="Recomeçar com outro conteúdo (voltar à Etapa 2)"),
                ft.Radio(value="exit", label="Sair"),
            ]
        ),
    )

    def do_answer(e):
        q = (question_field.value or "").strip()
        if not q:
            toast(page, "Escreva uma pergunta.")
            return
        try:
            msg_lbl.value = "Consultando o material..."
            page.update()

            client = OpenAIClientFactory.build(STATE.api_key)
            req = QARequest(ebook_text=STATE.ebook_text, question=q)
            out = answer_with_ebook(client, req)

            if getattr(out, "has_content", False):
                ans = normalize_none_answer(out.answer) if out.answer else ""
                STATE.last_answer = (ans or "").strip()
                STATE.qa_status = "ok"
            else:
                STATE.last_answer = None
                STATE.qa_status = "insufficient"
        except Exception as ex:
            STATE.last_answer = None
            STATE.qa_status = "error"
            msg_lbl.value = f"Falha ao obter resposta: {ex}"
            page.update()
            return

        if STATE.last_answer is None:
            if STATE.qa_status == "insufficient":
                msg_lbl.value = "Não há informações suficientes no material fornecido."
            elif STATE.qa_status == "error":
                msg_lbl.value = "Falha ao obter resposta. Tente novamente."
            else:
                msg_lbl.value = ""
            result_title.value = ""
            result_markdown.visible = False
        else:
            msg_lbl.value = ""
            result_title.value = "Resposta"
            result_markdown.value = STATE.last_answer
            result_markdown.visible = True
        page.update()

    def on_confirm_action(e):
        opt = action_radio.value
        if opt == "new":
            STATE.last_answer = None
            STATE.qa_status = None
            question_field.value = ""
            result_title.value = ""
            result_markdown.visible = False
            msg_lbl.value = ""
            page.update()
        elif opt == "save":
            if not STATE.last_answer:
                toast(page, "Nenhuma resposta para salvar.")
                return
            p = save_txt_only(STATE.last_answer, "resposta_ebook")
            toast(page, f"Arquivo salvo em: {p}")
        elif opt == "restart":
            STATE.last_answer = None
            STATE.qa_status = None
            STATE.ebook_text = None
            STATE.step = 2
            route_to_step(page)
        elif opt == "exit":
            STATE.__init__()  # reset total
            STATE.step = 1
            route_to_step(page)

    page.add(
        ft.Column(
            [
                subtitle,
                question_field,
                ft.FilledButton("Responder", on_click=do_answer),
                ft.Divider(),
                msg_lbl,
                ft.Text("", size=4),
                result_title,
                result_markdown,
                ft.Divider(),
                ft.Text("Ações"),
                action_radio,
                ft.ElevatedButton("Confirmar", on_click=on_confirm_action),
            ],
            spacing=12,
        )
    )

# ===== Navegação =====
def route_to_step(page: ft.Page):
    page.clean()
    if STATE.step == 1:
        view_step1(page)
    elif STATE.step == 2:
        view_step2(page)
    elif STATE.step == 3:
        view_step3(page)
    else:
        STATE.step = 1
        view_step1(page)
    page.update()

# ===== Entry point Flet =====
def main(page: ft.Page):
    page.window.width = 980
    page.window.height = 820
    page.padding = 20
    page.scroll = ft.ScrollMode.AUTO
    route_to_step(page)

if __name__ == "__main__":
    ft.app(target=main)
