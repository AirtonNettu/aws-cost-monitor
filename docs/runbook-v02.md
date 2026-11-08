# Operação e troubleshooting

## Inicialização local segura

```bash
uv sync --frozen --dev
uv run python scripts/seed_demo.py --database data/demo.db
export DATABASE_PATH=data/demo.db
export API_USERNAME=operator
read -r -s -p 'Senha local da API (16+ caracteres ASCII): ' API_PASSWORD
export API_PASSWORD
uv run uvicorn src.api.app:create_app --factory --no-access-log --host 127.0.0.1 --port 8000
```

A semente recusa sobrescrever arquivo existente; não remover banco de usuário para fazê-la passar. Todos os valores semeados são fictícios, source=mock. Em outro terminal:

```bash
cd frontend
npm ci
VITE_DATA_MODE=api npm run dev -- --host 127.0.0.1
```

Abra o endereço local impresso pelo Vite e entre com a credencial do servidor. Para demonstração sem API: `npm run dev` (modo mock padrão). `VITE_API_BASE_URL` padrão /api/v1; proxy do Vite aponta para 127.0.0.1:8000. CORS e hosting de produção não são configurados automaticamente.

## Banco e recuperação

1. Parar todos os escritores (CLI, Streamlit e coleta).
2. Fazer backup consistente: `uv run python -c "import sqlite3; a=sqlite3.connect('data/costs.db'); b=sqlite3.connect('data/costs-backup.db'); a.backup(b); b.close(); a.close()"`.
3. Iniciar API para executar migração aditiva. Testar ready e histórico autenticados.
4. Se necessário, parar processos e restaurar backup. Não apagar tabelas/arquivos em runtime para fazer testes passarem.
5. Backups contêm dados financeiros: manter fora do Git, com acesso restrito e retenção definida pelo operador. Schema legado não é promovido automaticamente: ver arquitetura.

## Coleta controlada

API nunca coleta. Uma chamada explicitamente autorizada de `src.operations.collection.collect_once(db_path, days=30, tag=None)` reserva o dia UTC em collection_jobs. Resoluções de configuração de tag são aplicadas antes da consulta e da gravação. Concluída retorna o run salvo somente para os mesmos parâmetros; outro escopo é recusado; novas chamadas no mesmo banco/dia não consultam AWS. Não há retry automático depois de falha ou estado running.

Para diagnosticar falha, consultar apenas status/error_code/horários de collection_jobs (não imprimir payload financeiro). Corrigir credenciais/rede e avaliar custo antes de qualquer nova tentativa. Uma execução interrompida pode deixar running: operador decide recuperação manual ou aguarda próxima data. Reserva e gravação do snapshot são transações separadas; uma interrupção entre elas pode deixar snapshot salvo e job running. Não apagar a reserva cegamente.

CLI e Streamlit legados continuam disponíveis. Streamlit inicia em histórico local e usa cache de 24 horas por configuração no modo AWS. Isso não é trava global: alterar filtros, reiniciar processo ou executar CLI manualmente pode realizar novas consultas. Para política diária estrita usar coleta reservada/agenda preparada. Paginação até 20 páginas e duas tentativas por página; uma execução diária NÃO significa uma única requisição faturável.

## Sintomas e ações

| Sintoma | Diagnóstico e recuperação |
| --- | --- |
| API não inicia | Configurar usuário/senha ASCII adequada sem imprimir valores; conferir diretório gravável |
| 401 | Credencial inválida/ausente; entrar novamente; nunca colocar senha no bundle |
| 404 no snapshot | Não há janela/tag salva; consultar histórico; não fazer coleta automática |
| 422 | days deve ser 7/30/90, limit 1..50, formato json/csv |
| 503 | Banco ausente, bloqueado/corrompido ou snapshot inválido; verificar backup e permissão local |
| 500 | Usar X-Request-ID e logs seguros; não divulgar traceback ao navegador |
| Sem série diária | Coleta mensal ou registro legado não permite série; não interpolar valores inventados |
| IA indisponível | FinOps continua; configurar Ollama apenas em Python privado se desejado |
| Tela vazia após npm ci | Parar Vite antes de reinstalar; iniciar um único servidor com --force |
| Lambda sem relatório | Agenda desabilitada? Ver logs e reserva locks/AAAA-MM-DD.json; não apagar guarda sem avaliar duplicação/custo |

## Observabilidade e limites

API registra JSON event/http_request, rota padronizada, status, request_id e duração medida. Health não implica AWS/IAM/Ollama funcionais. Coleta local registra status no SQLite e eventos seguros; Lambda registra guarda, término e request_id. Não há dashboard de métricas, alarmes pagos, tracing distribuído ou integração CloudWatch da API local.

SDK CE/S3: connect_timeout=2s, read_timeout=4s, total_max_attempts=2. Paginação e backoff podem exceder os 15s da Lambda em contas maiores; template estático não comprova suficiência. Uma falha após reserva S3 bloqueia nova tentativa naquele dia; intervenção manual ou próximo dia é necessária. Retentativas EventBridge e Lambda desabilitadas no template para limitar duplicação. Nunca afirmar SLA sem teste real.
