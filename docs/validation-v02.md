# Evidências da entrega Cloud/FinOps v0.2

Branch exclusiva: `refactor/cloud-finops-v02`. Base remota auditada: `8aa5fd1`. Nenhum merge ou alteração direta na main; nenhum provisionamento, upload de artefatos ou deploy AWS.

## Hardening final — três achados da revisão

Estado local verificado nesta entrega (substitui os totais anteriores):

| Verificação | Resultado observado |
| --- | --- |
| `uv sync --frozen --dev` | Lockfile consistente, sem atualização de versões |
| `pytest -q` | **116 passaram**, 1 aviso conhecido TestClient/httpx |
| `npm test` | **38 passaram**, 8 arquivos |
| `npm run test:contract` | FastAPI → Zod aprovado, dados sintéticos |
| `npm run lint` / `npm run build` | ESLint e TypeScript/Vite aprovados |
| `cfn-lint infra/serverless.yaml` | Exit0, sem diagnósticos |
| `python scripts/security_audit.py` | 0 alertas, 0 achados |
| `python scripts/package_lambda.py` e `--validate` | CRC, manifesto, allowlist e imports isolados aprovados |
| Teste de reprodutibilidade | Duas gerações locais com SHA-256 idêntico; adulteração recusada |
| `git diff --check` | Sem erros de whitespace |

Artefato local: 2204 arquivos, 16.603.249 bytes comprimidos, 22.948.485 bytes descompactados. SHA-256 observado: `ac0d451cda9e38d7bc0609ef59141be7f73ee99ba69f2f2bf9b6ba20839d8364`. O ZIP não é versionado nem publicado. A CI agora também gera e valida o pacote; o checksum não é promessa de identidade entre compressores/versões distintos.

Os testes novos reproduziram antes das correções o bypass do handler legado, ausência de referência UTC/fim explícito e falta de empacotamento verificável. Regressões cobrem ambos os handlers na mesma reserva (uma coleta/uma publicação), virada de ano, ano bissexto, consulta ancorada na reserva SQLite/S3, runtime/arquitetura/handler do template, ausência de dependências da API/dashboard no ZIP e recusa de conteúdo extra/adulterado. Os testes antigos da geração foram mantidos, apontando explicitamente ao helper interno `run_report`; não foram removidos nem suas asserções relaxadas.

O contrato falhou inicialmente por cache uv em diretório somente leitura (`/home/agent/.cache/uv`). Reexecutado com `UV_CACHE_DIR=/workspace/.cache/uv`, passou; não foi defeito de contrato. A mesma configuração local foi usada para geração/testes Python. Nenhuma credencial ou conta AWS foi acessada.

Lint Python suplementar com Ruff: módulos de datas/coleta, empacotador e novos testes passaram. A varredura ampliada também identificou **4 diagnósticos preexistentes** em `lambda_function.py`/`serverless.py` (BLE001 e S110, capturas genéricas de exceção e guarda de melhor esforço). A baseline foi reproduzida via `git show`. Permanecem registrados, sem `noqa` ou supressão: essas fronteiras preservam respostas sanitizadas e a reserva em falhas ambíguas; não se ampliou esta missão para redesenhar o tratamento de falhas. ESLint exigido pela CI passou. Este relatório não declara o Ruff ampliado aprovado.

CI da estabilização anterior: [42530859877, d6173b9, Success](https://github.com/AirtonNettu/aws-cost-monitor/actions/runs/42530859877). O resultado da CI dos commits deste hardening será informado na entrega após o push; consultar [Checks do PR #8](https://github.com/AirtonNettu/aws-cost-monitor/pull/8/checks).

### Riscos e parecer

Os três achados foram corrigidos com regressões locais; ver [ADR-003](adr/003-lambda-entrypoints-utc-package.md) e [runbook](runbook-v02.md). A aprovação no escopo de laboratório/portfólio depende da CI do HEAD e da revisão humana. Runtime gerenciado, IAM efetivo, latência, custos e recuperação na AWS não foram executados nem comprovados. Guardas continuam exigindo confirmação humana de processo parado; manifesto é integridade, não assinatura. Não há aprovação de produção, merge ou deploy.

## Estabilização final do PR #8

- **105 testes Python passaram**, com o aviso conhecido de TestClient/httpx; **38 testes frontend passaram**.
- Contrato FastAPI/Zod, lint, build TypeScript/Vite, auditoria de segurança (0achados) e cfn-lint aprovados localmente.
- Novos testes exercitam rollback antes de confirmar job, escritor SQLite ativo, token obsoleto, teto de recuperação, ETag concorrente, upload com resposta perdida, reconciliação após tentativa2, lease running, falta de orçamento, teto de5páginas sem publicação parcial, guarda com erro de rede, todas as leituras autenticadas, CORS restrito e JSON corrompido503.
- A revisão independente encontrou dois defeitos reproduzidos: HEAD de chave ausente podia resultar403 com o IAM disponível; e coleta vazia retornava200 sem artefato. A consulta passou a LIST com prefixo exato/MaxKeys1, IAM correspondente e HEAD só de objeto listado. Sucesso agora exige artefato verificado. Ambos têm testes de regressão.
- IAM revisado: S3 privado, TLS obrigatório, GetObject/PutObject nos prefixos da stack, ListBucket apenas reports/*/max-keys1, sem DeleteObject. Autenticação permanece de operador único; nenhuma credencial AWS chega à API/SPA.
- CI anterior: [execução42528443435, commit5d4cf5c](https://github.com/AirtonNettu/aws-cost-monitor/actions/runs/42528443435), Success. Avisos de Actions Node20 motivaram atualização para Actions Node24 fixadas por SHA e runner Ubuntu24.04. Resultado dos commits novos: consultar [Checks do PR #8](https://github.com/AirtonNettu/aws-cost-monitor/pull/8/checks); não confundir a CI da base com a da estabilização.
- Nenhuma conta AWS foi consultada. Nenhuma função AWS foi executada. Não houve deploy, criação de recursos ou merge.

[Procedimento de recuperação](runbook-v02.md) e [ADR-002](adr/002-recovery-and-deadlines.md) descrevem confirmação de parada, migração aditiva, tokens/ETags, duas tentativas, expiração, reconciliação e risco residual. CLI auxiliar foi acrescentada em scripts/recover_collection.py. Pacote Lambda inclui o módulo de orçamento; foi gerado somente localmente.

### Recomendação e riscos residuais

As correções são candidatas à aprovação para o escopo local/portfólio e infraestrutura preparada, condicionadas à CI do HEAD e revisão humana. Não equivalem à aprovação de produção ou implantação. Validar IAM efetivo, runtime/SDK empacotado, tempo real, custos, concorrência de versões e procedimento de recuperação em conta de teste futura explicitamente autorizada. Budget é cooperativo, não garante latência; guardas legadas sem identidade não são reabertas; SQLite exige locking confiável e pode bloquear outros escritores. A confirmação de processo parado é uma responsabilidade do operador, não prova automática. Metadados financeiros/segredos não são impressos pela recuperação.

## Evidências anteriores à estabilização

## Resultados executados

| Verificação | Resultado observado |
| --- | --- |
| Baseline Python | 59 testes passaram antes das alterações |
| Baseline frontend | 37 testes passaram antes das alterações |
| uv sync --frozen --dev | Dependências travadas instaladas, Python3.14.8 |
| pytest -q antes da estabilização | **75 passaram**, 1 aviso de depreciação do TestClient/httpx |
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
- A recuperação de reservas é manual e limitada; ver ADR-002. Lambda proposta60s, sem comprovação de duração em AWS; parsing e rede podem causar interrupção e exigir reconciliação.
- API é local, de operador único, sem identidade multitenant, rate limiting ou hosting cloud. TLS/reverse proxy e controle de tentativas são pré-requisitos externos.
- Registros legados permanecem, sem promoção automática para snapshots sem proveniência; exige importador futuro e backup.
- Motor float preservado; Decimal e avaliações semânticas/estruturação da IA continuam planejados.
- CI da base5d4cf5c confirmada como Success na execução42528443435; a execução da estabilização deve ser consultada nos Checks do PR #8.
- Automatização axe não comprova acessibilidade universal ou teste manual com leitor de tela.
- O PR #8 já existe em Draft na branch refactor/cloud-finops-v02. API GitHub continua bloqueada (Forbidden), mas a página pública permitiu consultar histórico e metadados da CI. Logs de Actions exigem login; nenhum PR novo foi criado. A atualização usa commits na mesma branch.

## Reprodução

Comandos completos em [runbook](runbook-v02.md), [API](api-v02.md), [infraestrutura](infrastructure-v02.md) e READMEs PT/EN. Ferramentas Playwright/axe foram instaladas fora do pacote do aplicativo para validação local; CI cobre suítes, contrato, auditoria e template, não esse E2E externo.
