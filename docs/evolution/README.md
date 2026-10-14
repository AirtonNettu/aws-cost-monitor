# NETTO LABS — Guia de Evolução Arquitetural do AWS Cost Monitor
<!-- Plano Estratégico de Maturidade: Do Portfólio ao Produto Comercial -->

Este documento estabelece o **Roadmap Estratégico de Evolução** para transformar o `aws-cost-monitor` em uma ferramenta de nível corporativo e, potencialmente, em um **Micro-SaaS B2B de FinOps**.

---

## 🎯 Modelo de Maturidade FinOps (Maturity Levels)

```
┌────────────────────────────────────────────────────────────────────────┐
│ Nível 4: Multi-Tenant Enterprise SaaS (Marketplace AWS / Stripe)       │
├────────────────────────────────────────────────────────────────────────┤
│ Nível 3: Multi-Conta & AWS Organizations (Cross-Account IAM Roles)     │
├────────────────────────────────────────────────────────────────────────┤
│ Nível 2: Alertas Push em Tempo Real (Slack / Discord / Telegram / SNS) │
├────────────────────────────────────────────────────────────────────────┤
│ Nível 1: Detecção Estatística de Anomalias & Previsão de Fatura        │
├────────────────────────────────────────────────────────────────────────┤
│ ✅ Nível 0: v0.2.0 Atual (Coleta, FinOps Rules, SQLite, Lambda, S3, UI)│
└────────────────────────────────────────────────────────────────────────┘
```

---

## 📂 Guias Técnicos Disponíveis nesta Pasta

| Fase | Documento | O que você vai aprender e construir | Esforço |
| :---: | :--- | :--- | :---: |
| **Fase 1** | [`01-finops-anomalies.md`](./01-finops-anomalies.md) | **Detecção Estatística de Anomalias:** Algoritmo Z-score e médias móveis em Python para detectar picos anormais de gasto diário e prever a fatura do final do mês. | 🟢 1 dia |
| **Fase 2** | [`02-push-alerting.md`](./02-push-alerting.md) | **Alertas Push Multicanal:** Integração direta com Webhooks do Slack, Discord, bots do Telegram e Amazon SNS para notificar gestores no celular quando um alerta crítico disparar. | 🟢 1 dia |
| **Fase 3** | [`03-multi-account-aws-organizations.md`](./03-multi-account-aws-organizations.md) | **Multi-Conta & AWS Organizations:** Monitorar dezenas de contas AWS simultaneamente usando `sts:AssumeRole` entre contas (padrão enterprise). | 🟡 2 dias |
| **Fase 4** | [`04-saas-monetization.md`](./04-saas-monetization.md) | **Comercialização & Micro-SaaS:** Como embalar este projeto em um produto pago para cobrar R$ 97 a R$ 297/mês de pequenas e médias empresas. | 🟡 3 dias |

---

## 💡 Princípio de Evolução: "Passo a Passo sem Quebrar o que Funciona"
Cada evolução foi planejada para ser **aditiva e não-bloqueante**:
- Se um canal de alerta (Slack) falhar, o relatório continua gerando.
- Se a conta não for multi-account, o modo single-account continua rodando liso.
- O custo de infraestrutura permanece **R$ 0,00 no AWS Free Tier**.
