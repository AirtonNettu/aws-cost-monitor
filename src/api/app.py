"""FastAPI read-only API. No GET handler contacts AWS or Ollama."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from src import config
from src.database.repository import get_latest_run, get_history, get_run_services


class Period(BaseModel):
    start: str
    end: str


class Summary(BaseModel):
    total_cost: float
    largest_service: str | None
    largest_service_percentage: float | None
    alert_count: int = Field(ge=0)


class ServiceCost(BaseModel):
    name: str
    amount: float
    percentage: float


class Alert(BaseModel):
    id: str
    type: Literal["growth", "concentration", "top_services", "untagged"]
    severity: Literal["info", "warning", "critical"]
    message: str


class AIState(BaseModel):
    status: Literal["ready", "processing", "unavailable"]
    text: str | None
    model: str | None
    observations: list[str]
    recommendations: list[str]
    potential_waste: list[str]
    reason: str | None


class Snapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    source: Literal["aws", "mock"]
    collected_at: datetime
    currency: Literal["USD"] = "USD"
    period: Period
    estimated: bool
    tag: str | None
    summary: Summary
    comparison: dict | None
    services: list[ServiceCost]
    timeline: list[dict]
    alerts: list[Alert]
    ai: AIState
    available_filters: dict
    report_formats: list[str]


def _snapshot(row: dict) -> Snapshot:
    # Legacy runs do not persist exact days, tags, estimated flag, or timeline.
    # Do not fabricate these fields or claim the row matches a requested filter.
    services = row.get("services") or get_run_services(row["id"])
    alerts = []
    for index, raw in enumerate(row.get("alerts", []), start=1):
        kind = "untagged" if raw.get("type") == "untagged_resources" else raw.get("type")
        alerts.append(Alert(id=f"{row['id']}-{index}", type=kind,
                            severity=raw["severity"], message=raw["message"]))
    largest = row.get("largest_service")
    pct = next((s["percentage"] for s in services if s["service_name"] == largest), None)
    ai_text = row.get("ai_interpretation")
    collected = datetime.fromisoformat(row["created_at"])
    if collected.tzinfo is None:
        # Legacy datetime.now() stored naive local time: timezone is unknown.
        # Refuse to mislabel it as UTC; require a migration before API exposure.
        raise HTTPException(status_code=409, detail="Snapshot legado sem fuso horario; migracao necessaria.")
    return Snapshot(
        id=str(row["id"]), source="aws", collected_at=collected,
        period=Period(start=row["period_start"], end=row["period_end"]),
        estimated=False, tag=None,
        summary=Summary(total_cost=row["total_cost"], largest_service=largest,
                        largest_service_percentage=pct, alert_count=len(alerts)),
        comparison=None,
        services=[ServiceCost(name=s["service_name"], amount=s["amount"],
                              percentage=s["percentage"]) for s in services],
        timeline=[], alerts=alerts,
        ai=AIState(status="ready" if ai_text else "unavailable", text=ai_text,
                   model=None, observations=[], recommendations=[], potential_waste=[],
                   reason=None if ai_text else "Analise nao disponivel."),
        available_filters={"days": [], "tags": []}, report_formats=[],
    )


app = FastAPI(title="AWS Cost Monitor API", version="0.1.0")


@app.get("/api/v1/health")
def health():
    return {"status": "ok"}


@app.get("/api/v1/snapshots/latest", response_model=Snapshot)
def latest_snapshot(days: Literal[7, 30, 90] = 30, tag: str | None = None):
    # Legacy SQLite cannot prove that a row matches these filters.
    # Explicitly report unavailable rather than show unrelated costs.
    raise HTTPException(status_code=501, detail="Filtro de snapshots requer migracao de metadados.")


@app.get("/api/v1/runs")
def list_runs(limit: int = Query(default=50, ge=1, le=100)):
    runs = get_history(limit=limit)
    result = []
    for row in reversed(runs):
        if not row["period_start"] or not row["period_end"]:
            continue
        collected = datetime.fromisoformat(row["created_at"])
        if collected.tzinfo is None:
            continue  # Legacy timezone unknown; not safe for frontend contract.
        result.append({"id": str(row["id"]), "collected_at": collected.isoformat(),
                       "period": {"start": row["period_start"], "end": row["period_end"]},
                       "estimated": False, "total_cost": row["total_cost"],
                       "largest_service": row["largest_service"]})
    return {"runs": result}


@app.get("/api/v1/runs/{run_id}", response_model=Snapshot)
def get_run(run_id: int):
    rows = get_history(limit=100)
    row = next((r for r in rows if r["id"] == run_id), None)
    if row is None:
        raise HTTPException(status_code=404, detail="Snapshot nao encontrado.")
    return _snapshot(row)
