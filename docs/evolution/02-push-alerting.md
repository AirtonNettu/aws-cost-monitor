# Fase 2: Alertas Push Multicanal (Discord, Slack, Telegram, SNS)

Nesta fase, você transforma o monitor em um **guardião proativo**: em vez de o usuário precisar abrir o dashboard para ver se houve problema, o sistema envia uma mensagem diretamente no celular ou canal do time quando um alerta de FinOps for disparado.

---

## 1. Canais Recomendados (Custo R$ 0,00)

1. **Discord Webhook:** Gratuito, mensagens com embeds coloridos, ideal para equipes ágeis.
2. **Slack Incoming Webhook:** O padrão corporativo em 95% das empresas de tecnologia.
3. **Telegram Bot API:** Notificações instantâneas gratuitas direto no seu smartphone pessoal.
4. **Amazon SNS (Simple Notification Service):** Envio de e-mails formatados e SMS nativos da AWS (Free Tier: 1.000.000 de notificações grátis/mês).

---

## 2. Arquitetura Desacoplada (Pattern Dispatcher)

Crie um novo módulo em `src/notifications/`:
```
src/
└── notifications/
    ├── __init__.py
    ├── discord.py      # Envia embed para Discord via requests.post
    ├── slack.py        # Envia payload formatado para Slack
    ├── telegram.py     # Envia mensagem via Telegram Bot API
    └── dispatcher.py   # Orquestrador central de alertas
```

### Exemplo de Implementação Rápida para Discord / Slack:

```python
import os
import requests


def send_discord_alert(webhook_url: str, title: str, alerts: list[dict]):
    """Envia alerta de FinOps para um canal do Discord de forma não-bloqueante."""
    if not webhook_url:
        return

    fields = [
        {"name": f"[{a['severity'].upper()}] {a['type']}", "value": a["message"]}
        for a in alerts
    ]

    payload = {
        "username": "NETTO LABS FinOps Guardian",
        "embeds": [
            {
                "title": f"🚨 Alerta de Custos AWS — {title}",
                "color": 15158332 if any(a["severity"] == "critical" for a in alerts) else 15844367,
                "fields": fields,
            }
        ],
    }

    try:
        requests.post(webhook_url, json=payload, timeout=5)
    except Exception as exc:
        print(f"[WARN] Falha ao enviar notificação: {exc}")
```

---

## 3. Configuração via `.env` ou AWS Lambda Secrets
Basta adicionar variáveis de ambiente opcionais:
```env
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
```
Se a variável estiver vazia, o sistema ignora o envio sem dar erro.
