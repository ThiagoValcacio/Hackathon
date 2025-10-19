# launcher.py
from __future__ import annotations
import os
import sys
import subprocess
import time
import webbrowser
from pathlib import Path
from traceback import format_exc

def _base_dir() -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).parent))

def main() -> None:
    try:
        print("=== EbookQA Launcher ===\n")
        print("Como saber a porta que escolho?")
        print("  • Use 8501 (padrão) para acesso local. Se já estiver em uso, escolha 8502, 3000, 8051 etc.")
        print("  • O aplicativo abrirá em 127.0.0.1:PORTA. Para compartilhar na rede, será preciso ajustar firewall.\n")

        default_port = "8501"
        raw = input(f"Informe a porta do servidor [padrão {default_port}]: ").strip()
        port = raw if raw else default_port
        if not port.isdigit() or not (1 <= int(port) <= 65535):
            print("Porta inválida. Usando 8501.")
            port = "8501"

        base = _base_dir()
        app_path = base / "app.py"
        if not app_path.exists():
            print(f"ERRO: app.py não encontrado em: {app_path}")
            input("Pressione Enter para sair...")
            return

        # Limpa sinais de DEV do Streamlit que ativam o Node dev server (porta 3000)
        for k in list(os.environ):
            if k.upper().startswith("STREAMLIT_"):
                del os.environ[k]
        # Define apenas o necessário, coerente com a porta/host escolhidos:
        env = os.environ.copy()
        env["STREAMLIT_SERVER_HEADLESS"] = "true"
        env["STREAMLIT_SERVER_FILE_WATCHER_TYPE"] = "none"
        env["STREAMLIT_BROWSER_GATHERUSAGESTATS"] = "false"
        env["STREAMLIT_SERVER_ADDRESS"] = "127.0.0.1"
        env["STREAMLIT_SERVER_PORT"] = port

        # Comando: python -m streamlit run app.py --flags...
        cmd = [
            sys.executable, "-m", "streamlit", "run", str(app_path),
            "--server.address", "127.0.0.1",
            "--server.port", str(port),
            "--server.headless", "true",
            "--server.fileWatcherType", "none",
            "--browser.gatherUsageStats", "false",
        ]

        url = f"http://127.0.0.1:{port}"
        print(f"Iniciando Streamlit em {url} ...")

        # Abre o navegador após um pequeno atraso (opcional)
        def _open_browser(u: str):
            time.sleep(2.0)
            try:
                webbrowser.open_new(u)
            except Exception:
                pass

        import threading
        threading.Thread(target=_open_browser, args=(url,), daemon=True).start()

        # Roda o streamlit como subprocess “normal”
        proc = subprocess.Popen(cmd, env=env)
        proc.wait()

        print("\nServidor encerrado.")
        input("Pressione Enter para sair...")

    except Exception:
        print("Exceção no launcher:\n")
        print(format_exc())
        input("Pressione Enter para sair...")

if __name__ == "__main__":
    main()