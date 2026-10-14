# NETTO LABS — Arquitetura da Equipe de Cibersegurança & Auditoria

Este documento descreve como a equipe virtual de cibersegurança e os guardrails da **NETTO LABS** estão estruturados, integrados ao código e automatizados no repositório.

---

## 🏛️ Papéis e Responsabilidades (Virtual AI Squad)

Definidos formalmente no arquivo [`AGENTS.md`](../AGENTS.md) e nos protocolos de regras em [`.agents/rules/`](../.agents/rules/):

```
                   ┌────────────────────────────────────────┐
                   │        NETTO LABS AI SQUAD             │
                   └──────────────────┬─────────────────────┘
                                      │
         ┌────────────────────────────┼────────────────────────────┐
         │                            │                            │
         ▼                            ▼                            ▼
┌──────────────────┐        ┌──────────────────┐        ┌──────────────────┐
│ Lead AppSec      │        │ FinOps Guardian  │        │ QA & Reviewer    │
│ Auditor          │        │ Protocol         │        │ Protocol         │
├──────────────────┤        ├──────────────────┤        ├──────────────────┤
│ • Scanner leaks  │        │ • Trava FreeTier │        │ • 100% Mocks     │
│ • Bloqueio AKIA  │        │ • Cron diário    │        │ • Zero divisão 0 │
│ • Git hygiene    │        │ • Cache SQLite   │        │ • Saída estrut.  │
│ • Script auditor │        │ • Alerta untag   │        │ • 59 testes      │
└──────────────────┘        └──────────────────┘        └──────────────────┘
```

1. **Lead AppSec Auditor (`.agents/rules/security-guardrails.md`):**
   - Ativo de forma ininterrupta (`always_on`).
   - Monitora vazamentos acidentais de credenciais (`AKIA...`, `ASIA...`, tokens e chaves privadas).
   - Bloqueia e audita permissões excessivas de IAM.
   - Valida que arquivos sensíveis permaneçam ignorados no `.gitignore`.

2. **FinOps & Cloud Guardian (`.agents/rules/finops-guardian.md`):**
   - Garante que a infraestrutura na AWS opere em custo zero (Free Tier).
   - Limita execuções do Cost Explorer a no máximo uma vez ao dia via EventBridge cron (`cron(0 11 * * ? *)`).
   - Impede custos surpresa de requisições web através de hospedagem estática no S3.

3. **QA & Architecture Reviewer:**
   - Mantém o princípio: *Python calcula, IA interpreta*.
   - Garante suíte de testes 100% baseada em mocks e cobertura total de caminhos críticos.

---

## 🛠️ Suíte Automatizada de Auditoria (`scripts/security_audit.py`)

O repositório possui uma ferramenta interna de auditoria estática desenvolvida em Python.

### Como Executar

```bash
# Execução direta no terminal
uv run python scripts/security_audit.py

# Ou saída formatada em JSON (para integração com CI/CD)
uv run python scripts/security_audit.py --json

# Especificar caminho personalizado do relatório
uv run python scripts/security_audit.py --report reports/meu-relatorio.md
```

### O que o scanner verifica automaticamente:
1. **Padrões de Segredos e Credenciais:**
   - Chaves de acesso AWS (`AKIA...`, `ASIA...`).
   - Padrões de Secret Access Key.
   - Chaves privadas RSA, EC, DSA, OpenSSH.
   - Tokens de autenticação Bearer ou chaves de API genéricas.
   - Identificadores de contas confidenciais.
2. **Integridade do `.gitignore`:**
   - Confirma a presença das regras mandatórias (`.env`, `*.pyc`, `__pycache__`, `.venv`, `*.db`, `*.zip`).
3. **Princípio do Menor Privilégio IAM:**
   - Varre a documentação e políticas em busca de curingas perigosos (`Action: *` ou `ce:*`).
4. **Geração de Relatório Executivo:**
   - Gera um relatório Markdown em `reports/security-audit-report.md` com status de aprovação (`🟢 APROVADO` ou `🔴 AÇÃO REQUERIDA`).

---

## 🧪 Testes Automatizados da Suíte (`tests/test_security_audit.py`)

A própria ferramenta de cibersegurança possui testes unitários para garantir sua eficácia:
- `test_clean_repo_passes`: Garante aprovação em repositório limpo.
- `test_catches_aws_access_key`: Valida que o scanner intercepta chaves AWS.
- `test_catches_missing_gitignore`: Valida alerta se o `.gitignore` for removido ou violado.
- `test_markdown_report_generation`: Valida a integridade do relatório executivo gerado.

Para rodar toda a suíte (59 testes):
```bash
uv run pytest -v
```

---

## 🚀 Como Replicar no "Security Pass" (Próximo SaaS)

Essa mesma estrutura de cibersegurança pode ser copiada para a pasta do `Security Pass`:
1. Copie o arquivo [`AGENTS.md`](../AGENTS.md) e a pasta [`.agents/rules/`](../.agents/rules/).
2. Copie [`scripts/security_audit.py`](../scripts/security_audit.py).
3. Adicione as regras de auditoria específicas de senhas zero-knowledge (Argon2id, salt de 16 bytes, IV de 12 bytes no AES-GCM).
