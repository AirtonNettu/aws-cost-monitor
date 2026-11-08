## Problema e resultado

A SPA usava somente demonstrações, sem API implementada, e a persistência não guardava o contrato completo de snapshots. Esta entrega acrescenta FastAPI autenticado de leitura, snapshots SQLite validados e integração React local sem consultas AWS por GET. Preserva CLI, relatórios, Streamlit e IA opcional.

## Mudanças

- Auditoria D0 e ADR de fronteiras, autenticação de operador único e migração aditiva.
- Contratos Pydantic/Zod, histórico/filtros, downloads JSON/CSV e sessão React em memória.
- Logs JSON, request_id, health/readiness, timeouts/retries/paginação limitados, reserva diária local/S3 e correções de segurança do HTML.
- CloudFormation com bucket privado criptografado, IAM mínimo, logs com retenção e agenda desabilitada. Sem API/SQLite cloud nesta stack.
- CI e documentação PT/EN de arquitetura, operação, custos, implantação/remoção e evidências.

## Validação

- 75 testes Python e38frontend passaram; pytest emite um aviso de depreciação TestClient/httpx.
- Contrato HTTP FastAPI → Zod, lint e builds mock/API passaram.
- cfn-lint sem diagnósticos; ZIP gerado apenas localmente; auditoria de segurança sem achados.
- E2E desktop/mobile contra Uvicorn/SQLite reais locais, inclusive build de produção API; dados sintéticos source=mock; axe sem violações nas regras executadas.
- Smoke Streamlit com quatro KPIs e sem chamadas AWS.

## Riscos e limites para revisão

Sem deploy ou validação AWS real; preços/Free Tier não comprovados. Lambda15s pode ser insuficiente para contas grandes. Bucket retido após remoção pode continuar gerando cobrança. Registros antigos sem proveniência não são promovidos automaticamente. Autenticação atual é de operador único; TLS e limitação de tentativas necessários antes de exposição externa. IA estruturada, Decimal, armazenamento cloud e multitenancy permanecem planejados.

Ver docs/validation-v02.md, docs/runbook-v02.md e docs/adr/001-v02-boundaries.md. Não realizar merge sem revisão humana.
