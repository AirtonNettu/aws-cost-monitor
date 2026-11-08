"""Construção determinística e validação dos snapshots persistidos."""
from datetime import date, datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, AwareDatetime, model_validator

from src.analysis.cost_analyzer import analyze_costs
from src.analysis.finops_rules import generate_alerts


class Model(BaseModel):
    """Modelo que rejeita campos inesperados e números não finitos."""
    model_config = ConfigDict(extra='forbid')


class Period(Model):
    start: date
    end: date

    @model_validator(mode='after')
    def ordered(self):
        """Valida o intervalo com término exclusivo."""
        if self.start >= self.end:
            raise ValueError('Intervalo inválido.')
        return self


class Summary(Model):
    total_cost: FiniteFloat
    largest_service: str | None
    largest_service_percentage: FiniteFloat | None
    alert_count: int = Field(ge=0)


class Service(Model):
    name: str
    amount: FiniteFloat
    percentage: FiniteFloat


class Point(Model):
    date: date
    amount: FiniteFloat


class Alert(Model):
    id: str
    type: Literal['growth', 'concentration', 'top_services', 'untagged']
    severity: Literal['info', 'warning', 'critical']
    message: str


class AI(Model):
    status: Literal['ready', 'processing', 'unavailable']
    text: str | None = None
    model: str | None = None
    observations: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    potential_waste: list[str] = Field(default_factory=list)
    reason: str | None = None


class Comparison(Model):
    previous_total: FiniteFloat
    current_total: FiniteFloat
    variation: FiniteFloat | None
    equivalent_periods: bool
    previous_period: Period


class Filters(Model):
    days: list[Literal[7, 30, 90]]
    tags: list[str]


class Snapshot(Model):
    id: str
    source: Literal['aws', 'mock']
    collected_at: AwareDatetime
    currency: Literal['USD'] = 'USD'
    period: Period
    estimated: bool
    tag: str | None
    summary: Summary
    comparison: Comparison | None
    services: list[Service]
    timeline: list[Point]
    alerts: list[Alert]
    ai: AI
    available_filters: Filters
    report_formats: list[Literal['json', 'csv']]


class RunSummary(Model):
    id: str
    collected_at: AwareDatetime
    period: Period
    estimated: bool
    total_cost: FiniteFloat
    largest_service: str | None


class History(Model):
    runs: list[RunSummary]


def build_snapshot(run_id, costs, analysis, ai_text=None, *, source='aws', tag=None,
                   collected_at=None, previous=None):
    """Reutiliza o motor Python, preservando créditos e a proveniência recebida."""
    periods = sorted(costs, key=lambda p: p['start'])
    period = Period(start=periods[0]['start'], end=periods[-1]['end'])
    comparison = None
    if previous and previous.source == source and previous.tag == tag:
        if previous.period.end == period.start and previous.period.end - previous.period.start == period.end - period.start:
            before = previous.summary.total_cost
            current = analysis['total_cost']
            comparison = Comparison(previous_total=before, current_total=current,
                variation=((current - before) / before * 100) if before else None,
                equivalent_periods=True, previous_period=previous.period)
    alerts = generate_alerts(analysis, comparison.model_dump() if comparison else None)
    mapped = [Alert(id=f'{run_id}-{i}', **{**a, 'type': 'untagged' if a['type'] == 'untagged_resources' else a['type']}) for i, a in enumerate(alerts)]
    daily = all((date.fromisoformat(p['end']) - date.fromisoformat(p['start'])).days == 1 for p in periods)
    return Snapshot(
        id=str(run_id), source=source, collected_at=collected_at or datetime.now(timezone.utc),
        period=period, estimated=any(p.get('estimated', True) for p in periods), tag=tag,
        summary=Summary(total_cost=analysis['total_cost'], largest_service=analysis['largest_service'],
            largest_service_percentage=analysis['percentages'].get(analysis['largest_service']), alert_count=len(mapped)),
        comparison=comparison,
        services=[Service(name=name, amount=amount, percentage=analysis['percentages'].get(name, 0)) for name, amount in analysis['services'].items()],
        timeline=[Point(date=p['start'], amount=analyze_costs([p])['total_cost']) for p in periods] if daily else [],
        alerts=mapped, ai=AI(status='ready' if ai_text else 'unavailable', text=ai_text,
            reason=None if ai_text else 'Interpretação não disponível para esta coleta.'),
        available_filters=Filters(days=[], tags=[]), report_formats=['json', 'csv'],
    )
