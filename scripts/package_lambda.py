"""Empacota somente os módulos necessários ao coletor, sem executar deploy."""
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
files = [ROOT / 'lambda_function.py', ROOT / 'src/__init__.py', ROOT / 'src/config.py', ROOT / 'src/operations/__init__.py', ROOT / 'src/operations/serverless.py']
for directory in ('analysis', 'aws', 'reports'):
    files.extend((ROOT / 'src' / directory).glob('*.py'))
destination = ROOT / 'reports/collector.zip'
destination.parent.mkdir(exist_ok=True)
with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(files):
        archive.write(path, path.relative_to(ROOT))
print('Pacote local criado em reports/collector.zip; nenhum upload executado.')
