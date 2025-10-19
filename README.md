📚 Ebook Q&A — CLI e Interface Web (Streamlit)

Este projeto permite transformar transcrições ou materiais brutos em ebooks organizados e realizar perguntas e respostas (Q&A) sobre o conteúdo usando a API da OpenAI.
O programa pode ser executado de duas formas:

Como executável (.exe) — sem necessidade de configurar ambiente.

Localmente com Python e Streamlit — ideal para desenvolvimento.

🧩 1. Configuração do ambiente virtual

Crie e ative o ambiente virtual (recomendado para o modo Streamlit):

# Criar ambiente virtual
python -3.12 -m venv .venv

# Linux/macOS
source .venv/bin/activate

# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1

📦 2. Instalar dependências

Instale todos os pacotes necessários:

pip install -r requirements.txt

🚀 3. Executar o programa
Opção A — Usar o executável (recomendado para usuários finais)

Se já tiver o arquivo EbookQA-CLI.exe (gerado em /dist), basta executar:

.\dist\EbookQA-CLI.exe

O programa abrirá diretamente no terminal com interface interativa.
Ao final, os ebooks refinados e respostas serão salvos automaticamente na sua pasta Downloads.

Como gerar o executável (para desenvolvedores)

Se quiser gerar o .exe você mesmo, execute:

pyinstaller --onefile --clean --name EbookQA-CLI ^
  --hidden-import jiter ^
  --hidden-import jiter.jiter ^
  --hidden-import pydantic_core ^
  --hidden-import pydantic_core._pydantic_core ^
  --paths . ^
  --paths .\api --paths .\agents --paths .\models --paths .\utils ^
  main_cli.py

Após o build, o executável estará em:

.\dist\EbookQA-CLI.exe

Opção B — Usar o Streamlit localmente (modo interface gráfica)

Execute o app Streamlit normalmente:

streamlit run app.py

Isso abrirá uma interface web interativa no navegador.
Certifique-se de ter configurado corretamente sua OpenAI API Key antes de iniciar.