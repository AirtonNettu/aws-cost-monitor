"""FastAPI read-only API. No GET handler contacts AWS or Ollama."""

from __future__ import annotations

import json
import logging
import math
import os
from datetime import datetime
from enum import IntEnum
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, HTTPException, Query, Response, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    functional_validators,
    model_validator,
)

from src.database.repository import (
    get_available_tags,
    get_history,
    get_latest_snapshot,
    get_run_by_id,
    get_run_services,
)
from src.reports.report_generator import build_report_for_format

logger = logging.getLogger("aws_cost_monitor.api")


def check_finite(v: float) -> float:
    """Valida estritamente se o número financeiro é finito.

    Rejeita NaN, Infinity e -Infinity. Preserva valores negativos legítimos (ex: créditos AWS).
    """
    if not isinstance(v, (int, float)) or not math.isfinite(v):
        raise ValueError(
            "Valor financeiro deve ser um número finito (valores NaN, Infinity e -Infinity são proibidos)."
        )
    return float(v)


FiniteFloat = Annotated[
    float,
    Field(allow_inf_nan=False),
    functional_validators.AfterValidator(check_finite),
]


class SnapshotDays(IntEnum):
    DAYS_7 = 7
    DAYS_30 = 30
    DAYS_90 = 90


class Period(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    start: str
    end: str

    @field_validator("start", "end")
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Data deve estar no formato ISO YYYY-MM-DD")
        return v

    @model_validator(mode="after")
    def validate_range(self) -> Period:
        if self.start >= self.end:
            raise ValueError("period.start deve ser estritamente anterior a period.end")
        return self


class Summary(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    total_cost: FiniteFloat
    largest_service: str | None
    largest_service_percentage: FiniteFloat | None
    alert_count: int = Field(ge=0)


class Comparison(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    previous_total: FiniteFloat
    current_total: FiniteFloat
    variation: FiniteFloat | None
    equivalent_periods: bool
    previous_period: Period


class ServiceCost(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    name: str
    amount: FiniteFloat
    percentage: FiniteFloat


class TimelinePoint(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    date: str
    amount: FiniteFloat

    @field_validator("date")
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Data deve estar no formato ISO YYYY-MM-DD")
        return v


class Alert(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    id: str
    type: Literal["growth", "concentration", "top_services", "untagged"]
    severity: Literal["info", "warning", "critical"]
    message: str


class AIState(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    status: Literal["ready", "processing", "unavailable"]
    text: str | None
    model: str | None
    observations: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    potential_waste: list[str] = Field(default_factory=list)
    reason: str | None = None


class AvailableFilters(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    days: list[SnapshotDays] = Field(
        default_factory=lambda: [SnapshotDays.DAYS_7, SnapshotDays.DAYS_30, SnapshotDays.DAYS_90]
    )
    tags: list[str] = Field(default_factory=list)


ReportFormatType = Literal["json", "csv", "html", "markdown", "txt"]


class Snapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    id: str
    source: Literal["aws", "mock"]
    collected_at: datetime
    currency: Literal["USD"] = "USD"
    period: Period
    estimated: bool
    tag: str | None
    summary: Summary
    comparison: Comparison | None
    services: list[ServiceCost]
    timeline: list[TimelinePoint]
    alerts: list[Alert]
    ai: AIState
    available_filters: AvailableFilters
    report_formats: list[ReportFormatType]


class RunSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    id: str
    collected_at: datetime
    period: Period
    estimated: bool
    total_cost: FiniteFloat
    largest_service: str | None


class HistoryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    runs: list[RunSummary]


def _snapshot(row: dict, db_path=None) -> Snapshot:
    services = row.get("services") or get_run_services(row["id"], db_path)

    alerts = []
    raw_alerts = row.get("alerts")
    if raw_alerts is None and row.get("alerts_json"):
        try:
            raw_alerts = json.loads(row["alerts_json"])
        except Exception:
            raw_alerts = []
    for index, raw in enumerate(raw_alerts or [], start=1):
        kind = "untagged" if raw.get("type") == "untagged_resources" else raw.get("type")
        alert_id = raw.get("id") or f"{row['id']}-{index}"
        alerts.append(
            Alert(
                id=str(alert_id),
                type=kind,
                severity=raw.get("severity", "info"),
                message=raw.get("message", ""),
            )
        )

    largest = row.get("largest_service")
    pct = next(
        (
            float(s["percentage"])
            for s in services
            if s.get("service_name") == largest or s.get("name") == largest
        ),
        None,
    )

    raw_created = row["created_at"]
    collected = datetime.fromisoformat(raw_created)
    if collected.tzinfo is None:
        raise HTTPException(
            status_code=409,
            detail="Snapshot legado sem fuso horario; migracao necessaria.",
        )

    period = Period(start=row["period_start"], end=row["period_end"])

    comparison = None
    if row.get("comparison_json"):
        try:
            comp_raw = json.loads(row["comparison_json"])
            if comp_raw and comp_raw.get("previous_period"):
                comparison = Comparison(
                    previous_total=float(comp_raw.get("previous_total", 0.0)),
                    current_total=float(comp_raw.get("current_total", row["total_cost"])),
                    variation=float(comp_raw["variation"])
                    if comp_raw.get("variation") is not None
                    else None,
                    equivalent_periods=bool(comp_raw.get("equivalent_periods", False)),
                    previous_period=Period(
                        start=comp_raw["previous_period"]["start"],
                        end=comp_raw["previous_period"]["end"],
                    ),
                )
        except Exception:
            comparison = None

    timeline = []
    if row.get("timeline_json"):
        try:
            for pt in json.loads(row["timeline_json"]):
                timeline.append(TimelinePoint(date=pt["date"], amount=float(pt["amount"])))
        except Exception:
            timeline = []

    if row.get("ai_json"):
        try:
            ai_raw = json.loads(row["ai_json"])
            ai_state = AIState(
                status=ai_raw.get("status", "unavailable"),
                text=ai_raw.get("text"),
                model=ai_raw.get("model"),
                observations=ai_raw.get("observations", []),
                recommendations=ai_raw.get("recommendations", []),
                potential_waste=ai_raw.get("potential_waste", []),
                reason=ai_raw.get("reason"),
            )
        except Exception:
            ai_text = row.get("ai_interpretation")
            ai_state = AIState(
                status="ready" if ai_text else "unavailable",
                text=ai_text,
                model=None,
                observations=[],
                recommendations=[],
                potential_waste=[],
                reason=None if ai_text else "Analise ainda nao executada.",
            )
    else:
        ai_text = row.get("ai_interpretation")
        ai_state = AIState(
            status="ready" if ai_text else "unavailable",
            text=ai_text,
            model=None,
            observations=[],
            recommendations=[],
            potential_waste=[],
            reason=None if ai_text else "Analise ainda nao executada.",
        )

    if row.get("available_filters_json"):
        try:
            filters_raw = json.loads(row["available_filters_json"])
            available_filters = AvailableFilters(
                days=filters_raw.get("days", [7, 30, 90]),
                tags=filters_raw.get("tags", []),
            )
        except Exception:
            available_filters = AvailableFilters(
                days=[SnapshotDays.DAYS_7, SnapshotDays.DAYS_30, SnapshotDays.DAYS_90],
                tags=get_available_tags(db_path),
            )
    else:
        available_filters = AvailableFilters(
            days=[SnapshotDays.DAYS_7, SnapshotDays.DAYS_30, SnapshotDays.DAYS_90],
            tags=get_available_tags(db_path),
        )

    if row.get("report_formats_json"):
        try:
            report_formats = json.loads(row["report_formats_json"])
        except Exception:
            report_formats = ["json", "markdown", "html", "txt"]
    else:
        report_formats = ["json", "markdown", "html", "txt"]

    service_costs = [
        ServiceCost(
            name=s.get("service_name") or s.get("name", ""),
            amount=float(s["amount"]),
            percentage=float(s["percentage"]),
        )
        for s in services
    ]

    return Snapshot(
        id=str(row["id"]),
        source=row.get("source") or "aws",
        collected_at=collected,
        currency="USD",
        period=period,
        estimated=bool(row.get("estimated", 0)),
        tag=row.get("tag"),
        summary=Summary(
            total_cost=float(row["total_cost"]),
            largest_service=largest,
            largest_service_percentage=pct,
            alert_count=len(alerts),
        ),
        comparison=comparison,
        services=service_costs,
        timeline=timeline,
        alerts=alerts,
        ai=ai_state,
        available_filters=available_filters,
        report_formats=report_formats,
    )


api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(api_key: str | None = Security(api_key_header)) -> str | None:
    """Valida a chave de API caso a variável de ambiente API_KEY esteja configurada."""
    expected_key = os.environ.get("API_KEY")
    if expected_key:
        if not api_key or api_key != expected_key:
            raise HTTPException(
                status_code=401,
                detail="Chave de API inválida ou ausente (header X-API-Key).",
            )
    return api_key


class SyncResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    status: str
    message: str
    snapshot: Snapshot | None = None


app = FastAPI(title="AWS Cost Monitor API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/api/v1/health")
def health():
    return {"status": "ok"}


@app.get(
    "/api/v1/snapshots/latest",
    response_model=Snapshot,
    dependencies=[Depends(verify_api_key)],
)
def latest_snapshot(
    days: SnapshotDays = SnapshotDays.DAYS_30,
    tag: str | None = None,
):
    clean_tag = tag.strip() if tag and tag.strip() else None
    row = get_latest_snapshot(days=int(days), tag=clean_tag)
    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"Nenhum snapshot encontrado para os filtros informados (days={days.value}, tag={clean_tag}).",
        )
    return _snapshot(row)


@app.post(
    "/api/v1/sync",
    response_model=SyncResponse,
    dependencies=[Depends(verify_api_key)],
)
def sync_aws_costs(
    days: SnapshotDays = SnapshotDays.DAYS_30,
    tag: str | None = None,
):
    """Sincroniza custos com a AWS (com proteção de cooldown e fallback seguro)."""
    clean_tag = tag.strip() if tag and tag.strip() else None
    latest = get_latest_snapshot(days=int(days), tag=clean_tag)

    # Cooldown FinOps: Se temos snapshot criado há menos de 10 minutos, aproveita o cache
    now = datetime.now()
    if latest and latest.get("created_at"):
        try:
            created_dt = datetime.fromisoformat(
                latest["created_at"].replace("Z", "+00:00")
            ).replace(tzinfo=None)
            diff_mins = (now - created_dt).total_seconds() / 60
            if diff_mins < 10:
                return SyncResponse(
                    status="cached",
                    message=f"Dados recentes já sincronizados ({int(diff_mins)} min atrás). Cooldown ativo para proteção de custos da API.",
                    snapshot=_snapshot(latest),
                )
        except Exception:
            pass

    # Tenta coleta real via Boto3 / Cost Explorer
    try:
        from src.analysis.cost_analyzer import analyze_costs, compare_periods
        from src.analysis.finops_rules import generate_alerts
        from src.aws.cost_explorer import get_costs
        from src.database.repository import save_run

        costs = get_costs(days=int(days), tag_key=clean_tag)
        analysis = analyze_costs(costs)
        comparison = compare_periods(costs)

        daily_costs = []
        for period in costs:
            day_total = sum(
                float(g["Metrics"]["UnblendedCost"]["Amount"])
                for g in period.get("groups", [])
            )
            daily_costs.append(day_total)

        alerts = generate_alerts(analysis, comparison, daily_costs=daily_costs)

        run_id = save_run(
            total_cost=analysis["total_cost"],
            services_data=analysis["positive_services"],
            source="aws",
            days=int(days),
            tag=clean_tag,
            estimated=True,
            comparison_json=json.dumps(comparison) if comparison else None,
            timeline_json=json.dumps(costs),
            alerts_json=json.dumps(alerts) if alerts else None,
        )

        updated_row = get_latest_snapshot(days=int(days), tag=clean_tag)
        return SyncResponse(
            status="success",
            message=f"Sincronização com AWS Cost Explorer concluída com sucesso (Execução #{run_id}).",
            snapshot=_snapshot(updated_row) if updated_row else None,
        )
    except Exception as e:
        logger.warning(f"Sincronização com AWS não concluída: {e}")
        if latest:
            return SyncResponse(
                status="offline_fallback",
                message="AWS indisponível ou credenciais ausentes. Exibindo dados locais seguros.",
                snapshot=_snapshot(latest),
            )
        raise HTTPException(
            status_code=503,
            detail=f"Não foi possível sincronizar com a AWS e nenhum dado local foi encontrado: {str(e)}",
        )


@app.get(
    "/api/v1/runs",
    response_model=HistoryResponse,
    dependencies=[Depends(verify_api_key)],
)
def list_runs(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    days: SnapshotDays | None = None,
    tag: str | None = None,
):
    clean_tag = tag.strip() if tag and tag.strip() else None
    days_val = int(days) if days is not None else None

    logger.info(
        "Listagem de execuções solicitada",
        extra={
            "limit": limit,
            "offset": offset,
            "days": days_val,
            "has_tag": clean_tag is not None,
        },
    )

    runs = get_history(
        limit=limit,
        offset=offset,
        days=days_val,
        tag=clean_tag,
        only_compatible=True,
        order_desc=True,
    )

    result = []
    for row in runs:
        try:
            raw_created = row["created_at"]
            collected = datetime.fromisoformat(raw_created)
            if collected.tzinfo is None:
                # Tratamento explícito com log estruturado de registros legados
                logger.warning(
                    "Registro legado com data ingênua ignorado no histórico da API",
                    extra={"run_id": row["id"]},
                )
                continue

            summary = RunSummary(
                id=str(row["id"]),
                collected_at=collected,
                period=Period(start=row["period_start"], end=row["period_end"]),
                estimated=bool(row.get("estimated", 0)),
                total_cost=float(row["total_cost"]),
                largest_service=row.get("largest_service"),
            )
            result.append(summary)
        except (ValueError, TypeError, ValidationError) as err:
            logger.error(
                "Falha na validação de integridade do registro histórico",
                extra={"run_id": row.get("id"), "erro": str(err)},
            )
            raise HTTPException(
                status_code=500,
                detail="Erro interno de integridade de dados ao listar execuções.",
            ) from err

    return HistoryResponse(runs=result)


@app.get(
    "/api/v1/runs/{run_id}",
    response_model=Snapshot,
    dependencies=[Depends(verify_api_key)],
)
def get_run(run_id: str):
    try:
        numeric_id = int(run_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Snapshot nao encontrado.")

    row = get_run_by_id(numeric_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Snapshot nao encontrado.")

    try:
        collected = datetime.fromisoformat(row["created_at"])
        if collected.tzinfo is None:
            logger.warning(
                "Consulta individual de snapshot legado sem fuso horário",
                extra={"run_id": numeric_id},
            )
            raise HTTPException(
                status_code=409,
                detail="Snapshot legado sem fuso horario; migracao necessaria.",
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Erro ao interpretar data de criação do snapshot",
            extra={"run_id": numeric_id, "erro": str(exc)},
        )
        raise HTTPException(
            status_code=500,
            detail="Erro ao processar dados do snapshot.",
        ) from exc

    return _snapshot(row)


_MEDIA_TYPES = {
    "json": "application/json",
    "markdown": "text/markdown; charset=utf-8",
    "html": "text/html; charset=utf-8",
    "txt": "text/plain; charset=utf-8",
}


@app.get(
    "/api/v1/runs/{run_id}/reports/{format}",
    dependencies=[Depends(verify_api_key)],
)
def download_report(run_id: str, format: str):
    norm_fmt = format.strip().lower()
    if norm_fmt not in _MEDIA_TYPES:
        raise HTTPException(
            status_code=404,
            detail=f"Formato '{format}' nao disponivel ou nao suportado.",
        )

    try:
        numeric_id = int(run_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Snapshot nao encontrado.")

    row = get_run_by_id(numeric_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Snapshot nao encontrado.")

    services = row.get("services") or get_run_services(row["id"])
    positive_services = {
        s["service_name"]: float(s["amount"])
        for s in services
        if float(s["amount"]) > 0
    }
    percentages = {
        s["service_name"]: float(s["percentage"])
        for s in services
    }
    analysis = {
        "services": {s["service_name"]: float(s["amount"]) for s in services},
        "total_cost": float(row["total_cost"]),
        "positive_services": positive_services,
        "percentages": percentages,
        "largest_service": row.get("largest_service"),
        "has_positive_cost": bool(row.get("has_positive_cost", 1 if row["total_cost"] > 0 else 0)),
    }

    comparison = None
    if row.get("previous_total") is not None:
        comparison = {
            "previous_total": float(row["previous_total"]),
            "current_total": float(row["total_cost"]),
            "variation": float(row["variation"]) if row.get("variation") is not None else None,
        }

    costs = []
    if row.get("period_start") and row.get("period_end"):
        costs = [{"start": row["period_start"], "end": row["period_end"], "groups": []}]

    report_text, ext = build_report_for_format(
        norm_fmt,
        costs=costs,
        analysis=analysis,
        comparison=comparison,
        ai_interpretation=row.get("ai_interpretation"),
        alerts=row.get("alerts", []),
    )

    media_type = _MEDIA_TYPES[norm_fmt]
    filename = f"report-run-{run_id}.{ext}"
    return Response(
        content=report_text,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
