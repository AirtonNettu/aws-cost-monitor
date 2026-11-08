# Plano de evolução — AWS Cost Monitor v0.2

Status: **planejamento; implementação não iniciada**.

## Objetivo
Evoluir a solução existente de análise de custos AWS para uma aplicação FinOps verificável, segura e bem documentada, preservando as funções atuais e evitando alterações diretas na branch main.

## Diagnóstico inicial (documentação existente)
- Motor Python com Boto3/Cost Explorer, regras determinísticas FinOps, SQLite, relatórios e cliente Ollama opcional.
- Interface Streamlit existente e frontend React/TypeScript com dados simulados.
- FastAPI e integração do frontend com dados reais ainda planejados.
- Implantação serverless documentada; execução em conta AWS e custos reais não verificados.
- Testes descritos no README; resultados atuais não executados nesta auditoria.

## Etapas propostas
### D0 — Auditoria e baseline
- Inventariar código, dependências, interfaces, testes, workflows, IAM, segredos e implantação.
- Executar testes Python e frontend em ambiente reproduzível; registrar falhas reais.
- Corrigir afirmações de custo zero e documentar limitações do Free Tier e cobrança do Cost Explorer.
- Entrega: relatório de achados com severidade e evidências.

### D1 — Contratos e integração
- Definir API de leitura de snapshots e histórico; versionar contratos e respostas de erro.
- Implementar FastAPI com autenticação/autorização apropriadas ao modelo de implantação.
- Integrar React sem acesso direto a credenciais AWS; eliminar fallback silencioso para mocks.
- Entrega: testes de contrato, integração e demonstração funcional.

### D2 — Operação e observabilidade
- Definir coleta agendada, persistência, logs estruturados, alertas e tratamento de falhas.
- Validar idempotência, retenção, paginação, limites de chamadas e recuperação.
- Entrega: runbooks e testes de falhas.

### D3 — Infraestrutura como código
- Definir arquitetura-alvo e estimativa de custos ANTES de provisionar.
- Provisionamento reprodutível, IAM mínimo, parâmetros, ambientes e destruição segura.
- Não executar deploy em conta real sem aprovação explícita.

### D4 — Documentação de portfólio
- Problema, requisitos, arquitetura, ADRs, segurança, implementação, validação, custos, troubleshooting e evidências.
- Separar implementado, testado e planejado.

## Critérios de aceite globais
- Sem regressão nos relatórios e regras FinOps existentes.
- Testes e verificações de segurança com resultados registrados.
- Sem segredos no repositório ou no bundle frontend.
- Sem alegações de custo zero ou produção sem evidências.
- Sem merge na main sem revisão explícita.

## Fora do escopo inicial
- Renomear repositório, excluir Streamlit, criar recursos AWS pagos ou implantar produção sem decisão arquitetural.
