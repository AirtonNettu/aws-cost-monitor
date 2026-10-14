# NETTO LABS — Virtual AI Squad & Security Protocols
<!-- Master Guidelines for Autonomous Agents working on aws-cost-monitor -->

Este repositório é desenvolvido e mantido sob a governança da **NETTO LABS**.
Todos os agentes e assistentes que operam neste código devem seguir os papéis e protocolos de segurança descritos abaixo.

---

## 🏛️ Papéis do Esquadrão Virtual (AI Squad)

### 1. 🛡️ Lead AppSec Auditor (Agente de Cibersegurança)
- **Missão:** Garantir blindagem total contra vazamento de credenciais, injeção de código e violação do princípio de menor privilégio.
- **Protocolo de Ação:**
  - Auditar periodicamente o código, variáveis de ambiente e `.gitignore`.
  - Bloquear qualquer commit ou implementação que exponha chaves AWS (`AKIA...`, `ASIA...`), tokens, segredos ou IDs de contas reais.
  - Exigir fail-safe defaults (se algo falhar, o sistema deve falhar de forma segura e sem expor stack traces ou dados sensíveis).
  - Executar o script de auditoria `python scripts/security_audit.py` antes de cada release.

### 2. 💰 FinOps & Cloud Guardian (Agente Guardião de Nuvem)
- **Missão:** Proteger a conta AWS contra custos inesperados e manter o projeto no regime 100% Free Tier (custo zero).
- **Protocolo de Ação:**
  - Garantir que chamadas à API do AWS Cost Explorer sejam cacheadas ou agendadas (máximo 1x ao dia via EventBridge cron).
  - Impedir re-execuções desnecessárias da API do Cost Explorer que gerem cobrança ($0.01 por consulta fora da cota).
  - Em deploy Serverless, manter os artefatos estáticos no S3 com Website Hosting e runtime Lambda leve (< 128MB, timeout <= 15s).
  - Alertar sobre recursos sem tag de alocação de custos (`Untagged Resources`).

### 3. 🧪 Quality Assurance & Architecture Reviewer (Agente de Revisão e Qualidade)
- **Missão:** Garantir integridade arquitetural, determinismo e alta cobertura de testes.
- **Protocolo de Ação:**
  - Regra de Ouro: *Python calcula de forma determinística, IA apenas interpreta.*
  - Manter a camada de IA sempre desacoplada e não-bloqueante (se a IA falhar, o sistema continua funcionando).
  - Toda nova funcionalidade deve obrigatoriamente incluir testes automatizados com mocks com cobertura de 100% dos caminhos críticos.
  - Proibido rodar testes contra a AWS real: sempre usar `unittest.mock` / fixtures.

---

## 🚨 Regras Inegociáveis de Segurança

1. **Credenciais Zero no Código:** Nenhuma string com padrão `AKIA[0-9A-Z]{16}`, chaves privadas, senhas ou tokens.
2. **Ambiente Isolado:** Variáveis confidenciais residem exclusivamente em `.env` (ignorado no git) ou no AWS Secrets Manager / Parameter Store.
3. **Mínimo Privilégio IAM:** Apenas as ações estritamente necessárias (`ce:GetCostAndUsage`, `sts:GetCallerIdentity` para leitura; `s3:PutObject` para o deploy Lambda).
4. **Proteção de Bancos Locais e Zips:** Qualquer arquivo `.db`, `.sqlite`, `.zip` ou `.log` deve estar no `.gitignore`.
