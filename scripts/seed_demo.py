"""Cria um banco separado de demonstração, sem qualquer chamada externa."""
import argparse
from datetime import date, timedelta, datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.analysis.cost_analyzer import analyze_costs
from src.database.repository import save_run


def seed(path):
    """Recusa sobrescrever bancos para preservar dados do operador."""
    path = Path(path)
    if path.exists():
        raise ValueError('O banco de destino já existe; escolha outro arquivo.')
    end = date(2026, 10, 20)
    for days in (7, 30, 90):
        for offset in (days, 0):
            stop = end - timedelta(days=offset)
            periods = []
            for i in range(days):
                day = stop - timedelta(days=days-i)
                groups = [{'Keys': [service], 'Metrics': {'UnblendedCost': {'Amount': str(amount), 'Unit': 'USD'}}}
                          for service, amount in [('Amazon EC2', 3), ('Amazon S3', 1), ('Crédito ilustrativo', -0.25)]]
                periods.append({'start': day.isoformat(), 'end': (day+timedelta(days=1)).isoformat(), 'estimated': True, 'groups': groups})
            save_run(periods, analyze_costs(periods), db_path=path, source='mock',
                     collected_at=datetime.combine(stop, datetime.min.time(), timezone.utc))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', default='data/demo.db')
    seed(parser.parse_args().database)
    print('Banco sintético criado; source=mock. Nenhuma coleta AWS executada.')
