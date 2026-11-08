"""Validação do ZIP hermético, reprodutível e sem arquivos locais."""

import hashlib
import importlib.util
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "package_lambda", ROOT / "scripts/package_lambda.py"
)
package = importlib.util.module_from_spec(spec)
spec.loader.exec_module(package)


def test_empacotamento_reproduzivel_e_importavel(tmp_path):
    first, second = tmp_path / "first.zip", tmp_path / "second.zip"
    package.build(first)
    package.build(second)
    assert (
        hashlib.sha256(first.read_bytes()).digest()
        == hashlib.sha256(second.read_bytes()).digest()
    )
    package.validate(first)
    altered = tmp_path / "altered.zip"
    with zipfile.ZipFile(first) as source, zipfile.ZipFile(altered, "w") as target:
        for name in source.namelist():
            data = source.read(name)
            target.writestr(
                name, data + b"\n# alterado" if name == "lambda_function.py" else data
            )
    with pytest.raises(ValueError, match="integridade"):
        package.validate(altered)
    with zipfile.ZipFile(first) as archive:
        names = set(archive.namelist())
        assert {
            "boto3/__init__.py",
            "botocore/__init__.py",
            "dotenv/__init__.py",
            "lambda_function.py",
            "artifact-manifest.json",
        } <= names
        assert not any(
            name.endswith((".db", ".sqlite", ".pyc", ".env")) or "__pycache__" in name
            for name in names
        )
        assert not any(
            name.startswith(("streamlit/", "fastapi/", "requests/")) for name in names
        )


def test_arquivo_extra_recusado(tmp_path):
    bad = tmp_path / "bad.zip"
    with zipfile.ZipFile(bad, "w") as archive:
        archive.writestr(".env", "DADO_SINTETICO=nao_incluir")
    with pytest.raises(ValueError):
        package.validate(bad)


def test_template_compativel_com_pacote():
    """Alterar runtime, arquitetura ou handler exige revisar o empacotamento."""
    from cfnlint.decode import decode

    template, errors = decode(str(ROOT / "infra/serverless.yaml"))
    assert not errors
    properties = template["Resources"]["Collector"]["Properties"]
    assert properties["Runtime"] == "python3.14"
    assert properties["Architectures"] == ["x86_64"]
    assert properties["Handler"] == "src.operations.serverless.lambda_handler"
