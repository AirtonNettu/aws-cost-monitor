# Plano executável v0.2

Spec: docs/roadmap-cloud-finops-v02.md. Decisões: docs/adr/001-v02-boundaries.md.
Execução direta autorizada pelo usuário; sem confirmações por arquivo.

- [x] D0: ler a base remota correta, executar baseline e documentar achados.
- [x] D1: testes vermelhos de persistência/API; modelos, migração aditiva, serviço de leitura, auth, erros e downloads; login React e contrato real.
- [x] D2: testes de falhas; logs/correlação, health/readiness, coleta diária idempotente, timeout/retry limitado, cache Streamlit e proteção HTML.
- [x] D3: template CloudFormation sem deploy; IAM mínimo, bucket privado, agenda desabilitada, retenção e validação cfn-lint.
- [x] D4: documentação PT/EN, runbooks, custos, evidências e limites; testes completos e navegador contra API real.
- [x] Revisão independente e correções reproduzidas/testadas; commits por responsabilidade.
- [x] Push final realizado na branch autorizada, sem merge.
- [ ] Draft PR para main: tentativa gh pr create --draft bloqueada por Forbidden em api.github.com/graphql; descrição pronta em docs/draft-pr-v02.md.

Interfaces: repository.save_run conserva assinatura e retorno; snapshot serviço lê SQLite por id/filtros; Snapshot Pydantic segue schema Zod; DataClient recebe Authorization em memória; coleta nunca é chamada por API. Todos os testes isolam AWS/Ollama.
