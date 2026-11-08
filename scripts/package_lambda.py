"""Gera e valida ZIP determinístico Python 3.14/x86_64, sem upload ou AWS."""

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_FILES = (
    "lambda_function.py",
    "src/__init__.py",
    "src/config.py",
    "src/operations/__init__.py",
    "src/operations/serverless.py",
    "src/operations/budget.py",
    "src/analysis/__init__.py",
    "src/analysis/cost_analyzer.py",
    "src/analysis/finops_rules.py",
    "src/aws/__init__.py",
    "src/aws/cost_explorer.py",
    "src/reports/__init__.py",
    "src/reports/report_generator.py",
)
DEPENDENCY_ROOTS = {
    "boto3",
    "botocore",
    "s3transfer",
    "jmespath",
    "dateutil",
    "urllib3",
    "dotenv",
}
DISTRIBUTIONS = {
    "boto3",
    "botocore",
    "s3transfer",
    "jmespath",
    "python_dateutil",
    "urllib3",
    "python_dotenv",
    "six",
}


def _allowed(name):
    """Aceita somente fontes explícitas e arquivos das dependências selecionadas."""
    path = Path(name)
    if path.is_absolute() or ".." in path.parts or "__pycache__" in path.parts:
        return False
    if path.suffix in {".pyc", ".db", ".sqlite", ".so", ".log"} or path.name == ".env":
        return False
    root = path.parts[0]
    return (
        name in SOURCE_FILES
        or name == "six.py"
        or root in DEPENDENCY_ROOTS
        or (root.endswith(".dist-info") and root.split("-")[0] in DISTRIBUTIONS)
    )


def validate(destination):
    """Confere CRC, manifesto, caminhos e imports sem site-packages/credenciais."""
    if sys.version_info[:2] != (3, 14):
        raise ValueError("Use Python 3.14 para validar o runtime alvo.")
    with zipfile.ZipFile(destination) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or archive.testzip() is not None:
            raise ValueError("ZIP duplicado ou corrompido.")
        if "artifact-manifest.json" not in names:
            raise ValueError("Manifesto ausente.")
        manifest = json.loads(archive.read("artifact-manifest.json"))
        files = manifest["files"]
        if set(names) != set(files) | {"artifact-manifest.json"}:
            raise ValueError("Conteúdo divergente do manifesto.")
        if (
            not set(SOURCE_FILES) <= set(files)
            or manifest["runtime"] != "python3.14"
            or manifest["architecture"] != "x86_64"
        ):
            raise ValueError("Contrato de runtime inválido.")
        for name, digest in files.items():
            if (
                not _allowed(name)
                or hashlib.sha256(archive.read(name)).hexdigest() != digest
            ):
                raise ValueError("Caminho ou integridade inválidos.")
        with tempfile.TemporaryDirectory() as temporary:
            archive.extractall(temporary)
            # -I -S elimina PYTHONPATH, site-packages e diretório do repositório.
            # Ambiente mínimo e cwd temporário impedem leitura de .env/profiles locais.
            code = "import sys; sys.path.insert(0, sys.argv[1]); import boto3, botocore, dotenv, s3transfer, jmespath, dateutil, urllib3, six; import lambda_function; from src.operations import serverless; assert callable(serverless.lambda_handler)"
            subprocess.run(
                [sys.executable, "-I", "-S", "-c", code, temporary],
                cwd=temporary,
                env={"AWS_EC2_METADATA_DISABLED": "true"},
                check=True,
                timeout=30,
            )
    return manifest


def build(destination):
    """Instala wheels com hashes do uv.lock e normaliza metadados do ZIP."""
    if sys.version_info[:2] != (3, 14):
        raise ValueError("Use Python 3.14 para validar o runtime alvo.")
    with tempfile.TemporaryDirectory() as temporary:
        stage = Path(temporary) / "stage"
        requirements = Path(temporary) / "lambda-requirements.txt"
        subprocess.run(
            [
                "uv",
                "export",
                "--frozen",
                "--only-group",
                "lambda",
                "--no-emit-project",
                "--output-file",
                str(requirements),
            ],
            cwd=ROOT,
            check=True,
            stdout=subprocess.DEVNULL,
        )
        subprocess.run(
            [
                "uv",
                "pip",
                "install",
                "--link-mode",
                "copy",
                "--require-hashes",
                "--only-binary",
                ":all:",
                "--no-installer-metadata",
                "--python-version",
                "3.14",
                "--python-platform",
                "x86_64-manylinux2014",
                "--target",
                str(stage),
                "-r",
                str(requirements),
            ],
            cwd=ROOT,
            check=True,
        )
        contents = {}
        for path in sorted(stage.rglob("*")):
            if not path.is_file():
                continue
            name = path.relative_to(stage).as_posix()
            # Scripts de console não são usados pelo handler; RECORD pode conter
            # seus caminhos de instalação temporários. Não são artefatos de execução.
            if name.startswith("bin/") or name == ".lock" or path.name == "RECORD":
                continue
            if not _allowed(name) or path.is_symlink():
                raise ValueError(f"Dependência com arquivo não suportado: {name}")
            contents[name] = path.read_bytes()
        for name in SOURCE_FILES:
            contents[name] = (ROOT / name).read_bytes()
        manifest = {
            "runtime": "python3.14",
            "architecture": "x86_64",
            "lock_sha256": hashlib.sha256((ROOT / "uv.lock").read_bytes()).hexdigest(),
            "files": {
                name: hashlib.sha256(data).hexdigest()
                for name, data in sorted(contents.items())
            },
        }
        contents["artifact-manifest.json"] = json.dumps(
            manifest, sort_keys=True, separators=(",", ":")
        ).encode()
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(
            destination, "w", zipfile.ZIP_DEFLATED, compresslevel=9
        ) as archive:
            for name, data in sorted(contents.items()):
                info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
                info.create_system = 3
                info.external_attr = 0o100644 << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, data, compresslevel=9)
        validate(destination)
    return hashlib.sha256(destination.read_bytes()).hexdigest()


def main():
    """Produz apenas artefato local e checksum; --validate não instala pacotes."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "reports/collector.zip")
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()
    if args.validate:
        validate(args.output)
    else:
        build(args.output)
    print(f"SHA256 {hashlib.sha256(args.output.read_bytes()).hexdigest()}")
    print("ZIP validado localmente; nenhum upload, deploy ou acesso AWS.")


if __name__ == "__main__":
    main()
