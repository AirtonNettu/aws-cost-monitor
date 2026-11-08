"""API autenticada de leitura; nenhuma rota coleta dados da AWS."""
from contextlib import asynccontextmanager
from dataclasses import dataclass
import csv
import io
import json
import logging
import os
from pathlib import Path
import secrets
import sqlite3
import time
from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import ValidationError

from src.application.snapshots import Snapshot, History
from src.database.repository import init_db
from src.database.snapshots import get_snapshot, list_snapshots, connection

logger = logging.getLogger('cost_monitor.api')


@dataclass(frozen=True)
class Settings:
    """Configuração privada do servidor; nunca incorporada no frontend."""
    database_path: Path
    username: str
    password: str

    @classmethod
    def from_environment(cls):
        """Lê nomes exclusivos de configuração da API sem imprimir seus valores."""
        return cls(Path(os.getenv('DATABASE_PATH', 'data/costs.db')),
                   os.getenv('API_USERNAME', 'operator'), os.getenv('API_PASSWORD', ''))


def create_app(settings=None):
    """Cria a API com autenticação obrigatória e migração aditiva no startup."""
    settings = settings or Settings.from_environment()
    if not settings.username or ':' in settings.username or not settings.username.isascii() or not settings.password.isascii() or not 16 <= len(settings.password) <= 256:
        raise ValueError('Configure API_USERNAME e API_PASSWORD com pelo menos 16 caracteres na senha.')

    @asynccontextmanager
    async def lifespan(app):
        init_db(settings.database_path)
        yield

    app = FastAPI(title='AWS Cost Monitor', version='0.2.0', docs_url=None,
                  redoc_url=None, openapi_url=None, lifespan=lifespan)
    security = HTTPBasic(auto_error=False)
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(message)s'))
        logger.addHandler(handler)
        logger.propagate = False

    def authenticate(credentials: Annotated[HTTPBasicCredentials | None, Depends(security)]):
        """Autoriza um único operador com acesso de leitura a todo o workspace."""
        username = credentials.username if credentials else ''
        password = credentials.password if credentials else ''
        user_ok = secrets.compare_digest(username.encode(), settings.username.encode())
        password_ok = secrets.compare_digest(password.encode(), settings.password.encode())
        if not (user_ok and password_ok):
            raise HTTPException(401, 'Autenticação necessária.')
        return settings.username

    def error_response(request, status, code, message):
        """Cria erro público sem detalhes do banco, credenciais ou traceback."""
        return JSONResponse(status_code=status, content={'error': {'code': code,
            'message': message, 'request_id': request.state.request_id}})

    @app.middleware('http')
    async def correlation(request, call_next):
        """Correlaciona e mede requisições sem registrar entrada sensível."""
        try:
            request_id = str(UUID(request.headers.get('X-Request-ID', '')))
        except ValueError:
            request_id = str(uuid4())
        request.state.request_id = request_id
        started = time.monotonic()
        try:
            response = await call_next(request)
        except Exception:
            response = error_response(request, 500, 'INTERNAL_ERROR', 'Falha interna ao processar a requisição.')
        response.headers['X-Request-ID'] = request_id
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        route = request.scope.get('route')
        logger.info(json.dumps({'event': 'http_request', 'request_id': request_id,
            'route': getattr(route, 'path', 'unmatched'), 'status': response.status_code,
            'duration_ms': round((time.monotonic() - started) * 1000, 2)}))
        return response

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request, error):
        codes = {401: 'UNAUTHORIZED', 403: 'FORBIDDEN', 404: 'NOT_FOUND', 405: 'METHOD_NOT_ALLOWED', 422: 'INVALID_REQUEST'}
        return error_response(request, error.status_code, codes.get(error.status_code, 'REQUEST_ERROR'),
                              'Autenticação necessária.' if error.status_code == 401 else 'Recurso indisponível para esta requisição.')

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, error):
        return error_response(request, 422, 'INVALID_REQUEST', 'Parâmetros inválidos.')

    @app.exception_handler(LookupError)
    async def missing_snapshot(request, error):
        return error_response(request, 404, 'SNAPSHOT_NOT_FOUND', 'Snapshot não encontrado para os filtros informados.')

    @app.exception_handler(sqlite3.Error)
    async def unavailable_database(request, error):
        return error_response(request, 503, 'STORAGE_UNAVAILABLE', 'Armazenamento temporariamente indisponível.')

    @app.exception_handler(ValidationError)
    async def invalid_snapshot(request, error):
        return error_response(request, 503, 'INVALID_SNAPSHOT', 'Snapshot armazenado inválido. Solicite revisão ao operador.')

    @app.get('/health/live')
    def live():
        return {'status': 'alive'}

    @app.get('/health/ready', dependencies=[Depends(authenticate)])
    def ready():
        with connection(settings.database_path) as conn:
            conn.execute('SELECT run_id FROM snapshots LIMIT 1').fetchone()
        return {'status': 'ready'}

    router = APIRouter(prefix='/api/v1', dependencies=[Depends(authenticate)])

    @router.get('/snapshots/latest', response_model=Snapshot)
    def latest(days: int = 30, tag: Annotated[str | None, Query(max_length=128)] = None):
        if days not in (7, 30, 90):
            raise HTTPException(422, 'Período inválido.')
        return get_snapshot(settings.database_path, days=days, tag=tag or None)

    @router.get('/runs', response_model=History)
    def runs(limit: Annotated[int, Query(ge=1, le=50)] = 50):
        return list_snapshots(settings.database_path, limit)

    @router.get('/runs/{run_id}', response_model=Snapshot)
    def run(run_id: int):
        return get_snapshot(settings.database_path, run_id=run_id)

    @router.get('/runs/{run_id}/reports/{report_format}')
    def report(run_id: int, report_format: Literal['json', 'csv']):
        """Gera download a partir do snapshot autorizado, sem paths do cliente."""
        snapshot = get_snapshot(settings.database_path, run_id=run_id)
        if report_format == 'json':
            body, media_type = snapshot.model_dump_json(indent=2), 'application/json'
        else:
            output = io.StringIO(newline='')
            writer = csv.writer(output)
            writer.writerow(['Serviço', 'Custo USD', 'Participação %'])
            for service in snapshot.services:
                name = service.name
                if name.lstrip().startswith(('=', '+', '-', '@', '\t', '\r')):
                    name = "'" + name
                writer.writerow([name, service.amount, service.percentage])
            body, media_type = output.getvalue(), 'text/csv'
        return Response(body, media_type=media_type,
            headers={'Content-Disposition': f'attachment; filename="aws-cost-report.{report_format}"'})

    @router.get('/openapi.json')
    def openapi():
        return app.openapi()

    app.include_router(router)
    return app
