# Evidências da entrega Cloud/FinOps v0.2

Branch exclusiva: `refactor/cloud-finops-v02`. Base remota auditada: `8aa5fd1`. Nenhum merge ou alteração direta na main; nenhum provisionamento, upload de artefatos ou deploy AWS.

## Resultados executados

| Verificação | Resultado observado |
| --- | --- |
| Baseline Python | 59 testes passaram antes das alterações |
| Baseline frontend | 37 testes passaram antes das alterações |
| uv sync --frozen --dev | Dependências travadas instaladas, Python3.14.8 |
| pytest -q final | **75 passaram**, 1 aviso de depreciação do TestClient/httpx |
| npm test | **38 passaram**, 8 arquivos |
| npm run test:contract | Resposta HTTP do FastAPI/TestClient validada pelo Zod; SQLite temporário, comparação0% e créditos preservados |
| npm run lint | Sem erros ou avisos ESLint |
| npm run build | TypeScript strict e Vite aprovados no modo mock padrão |
| VITE_DATA_MODE=api npm run build | Build de produção em modo API aprovado |
| cfn-lint infra/serverless.yaml | Exit0, sem diagnósticos |
| scripts/package_lambda.py | ZIP local gerado; sem upload/deploy |
| scripts/security_audit.py | 0 alertas e 0 achados |
| CLI --help | Parser e imports existentes funcionais |
| Streamlit AppTest | Histórico local, quatro KPIs e nenhuma consulta AWS; avisos de API Streamlit legada registrados |
| Chromium + Playwright | React → proxy Vite → Uvicorn → SQLite, sem interceptar respostas da API |
| E2E do build de produção API | Mesmo fluxo pelo preview local; login/logout, filtros7/30dias, cinco rotas, histórico/comparação/detalhes, download autenticado e401 sem credencial |
| axe no E2E | 0 violações nas regras wcag2a/wcag2aa/wcag21aa nas cinco áreas desktop e visão geral mobile clara |
| Console/rede E2E | Nenhum erro JS e nenhuma requisição externa |

Os dados E2E são sintéticos persistidos com `source=mock`. Isso valida transporte HTTP real e integração, não coleta financeira em conta real. As capturas [desktop](assets/v02/api-desktop.png) e [mobile](assets/v02/api-mobile.png) não contêm credenciais ou dados de contas.

## Casos de falha e regressões

API: ausência/erro de autenticação, snapshot inexistente, limite inválido, formato inválido, banco ausente503 sem caminho local, correlation ID não confiável, payload não finito e rollback. Persistência: comparação adjacente ignora janela incompatível, totais com créditos, série diária e metadados conservados.

Operação: falha de coleta registrada, reserva impede retry cego e segunda coleta diária, configurações de escopo diferentes são recusadas, paginação repetida falha sem salvar resultado parcial, CE e upload S3 têm timeouts/retentativas explícitos, guarda S3 duplicada não inicia coleta, nome externo não encerra script HTML.

Revisão independente apontou tag configurada não persistida e upload S3 com defaults longos. Ambos foram reproduzidos em testes vermelhos e corrigidos. A tag efetiva é resolvida antes de chamar AWS e persistir. O teste de contrato detectou interferência entre janelas7/30dias e a consulta foi corrigida. Nenhum achado da revisão foi adiado.

O pytest apresenta aviso de futura substituição de httpx por httpx2 no TestClient da versão instalada. Ele não representa teste ignorado ou falha. O Streamlit preservado usa propriedades marcadas como depreciadas; o smoke test passou. Não foram suprimidos avisos, assertions ou testes para obter aprovação.

## Limitações e validações não realizadas

- AWS real, IAM efetivo de conta, runtime Lambda, duração/memória, custos, Free Tier e remoção real não verificados.
- A reserva S3 impede novas tentativas após falha; pode precisar de intervenção privada. Paginação/backoff pode exceder15s da Lambda.
- API é local, de operador único, sem identidade multitenant, rate limiting ou hosting cloud. TLS/reverse proxy e controle de tentativas são pré-requisitos externos.
- Registros legados permanecem, sem promoção automática para snapshots sem proveniência; exige importador futuro e backup.
- Motor float preservado; Decimal e avaliações semânticas/estruturação da IA continuam planejados.
- CI foi criado mas não executado no GitHub nesta validação.
- Automatização axe não comprova acessibilidade universal ou teste manual com leitor de tela.
- Acesso Git remoto funciona; API GitHub bloqueada pela política de rede. Inclusão de api.github.com salva no rascunho do ambiente, ainda não aplicada/publicada. A abertura do Draft PR depende dessa liberação; não é um PR já criado.

## Reprodução

Comandos completos em [runbook](runbook-v02.md), [API](api-v02.md), [infraestrutura](infrastructure-v02.md) e READMEs PT/EN. Ferramentas Playwright/axe foram instaladas fora do pacote do aplicativo para validação local; CI cobre suítes, contrato, auditoria e template, não esse E2E externo.
