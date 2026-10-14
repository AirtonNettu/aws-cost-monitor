"""Ponto de entrada para o dashboard interativo.

Pode ser executado diretamente com:
    uv run streamlit run dashboard.py
ou simplesmente:
    uv run python dashboard.py
"""

import os
import subprocess
import sys

# Se estiver executando dentro do runtime do Streamlit
if "STREAMLIT_SERVER_PORT" in os.environ or any("streamlit" in arg for arg in sys.argv):
    from src.dashboard.app import run_dashboard
    run_dashboard()
else:
    # Se chamado via python direto, inicializa o servidor Streamlit automaticamente
    app_path = os.path.join(os.path.dirname(__file__), "src", "dashboard", "app.py")
    cmd = [sys.executable, "-m", "streamlit", "run", app_path] + sys.argv[1:]
    sys.exit(subprocess.call(cmd))
