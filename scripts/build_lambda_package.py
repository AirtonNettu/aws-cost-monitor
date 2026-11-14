"""Gera o pacote lambda_package.zip de forma limpa e determinística para deploy serverless."""

import os
import zipfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_ZIP = ROOT_DIR / "lambda_package.zip"


def build_package():
    print(f"Empacotando artefatos serverless em {OUTPUT_ZIP.name}...")
    with zipfile.ZipFile(OUTPUT_ZIP, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. Adiciona lambda_function.py na raiz do zip
        lambda_entry = ROOT_DIR / "lambda_function.py"
        if lambda_entry.exists():
            zf.write(lambda_entry, arcname="lambda_function.py")
            print("  + lambda_function.py")

        # 2. Adiciona o diretório src/ recursivamente, ignorando caches e testes
        src_dir = ROOT_DIR / "src"
        if src_dir.exists():
            for root, dirs, files in os.walk(src_dir):
                # Ignora __pycache__ e caches
                dirs[:] = [d for d in dirs if d != "__pycache__" and not d.endswith(".pyc")]
                for file in files:
                    if file.endswith(".pyc") or file.endswith(".pyo"):
                        continue
                    file_path = Path(root) / file
                    arcname = file_path.relative_to(ROOT_DIR).as_posix()
                    zf.write(file_path, arcname=arcname)
                    print(f"  + {arcname}")

    print(f"Pacote gerado com sucesso! Tamanho: {OUTPUT_ZIP.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    build_package()
