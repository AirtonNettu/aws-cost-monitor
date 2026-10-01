"""Atalho de execução na raiz do projeto.

Delega ao ponto de entrada real em src/main.py.
Uso: `uv run python main.py`
"""

from src.main import main

if __name__ == "__main__":
    main()
