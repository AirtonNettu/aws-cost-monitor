---
trigger: always_on
---
# FinOps Guardian Protocol — NETTO LABS

Este protocolo assegura que a arquitetura do projeto permaneça rigorosamente dentro do Free Tier (custo zero) da AWS e evite despesas acidentais.

## 1. Controle de Consultas à API
- A API do **AWS Cost Explorer (`ce:GetCostAndUsage`)** custa US$ 0.01 por consulta fora da cota gratuita.
- Toda rotina em nuvem (AWS Lambda) deve rodar de forma agendada no máximo uma vez ao dia via EventBridge cron (`cron(0 11 * * ? *)`), e salvar o resultado estaticamente no S3 Website.
- Em desenvolvimento local, encoraje o uso de snapshots SQLite locais (`data/costs.db`) para evitar consultas redundantes à AWS.

## 2. Padrões de Serveless Econômico
- Funções Lambda devem ser configuradas com tempo limite curto (timeout máximo de 15 segundos) e memória mínima necessária (128 MB a 256 MB), mantendo a execução bem abaixo de 1 milhão de invocações gratuitas por mês.
- O Amazon S3 deve armazenar apenas relatórios HTML leves e artefatos de deploy com ciclo de vida enxuto.
