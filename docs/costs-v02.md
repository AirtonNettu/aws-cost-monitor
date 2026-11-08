# Custos potenciais e limites de gratuidade

Não há comprovação de custo zero. Nenhuma conta foi consultada ou recurso provisionado nesta entrega. Preços, regiões, elegibilidade da conta, créditos e limites do Free Tier precisam ser verificados na data da ativação.

| Componente | Fatores que podem gerar cobrança |
| --- | --- |
| Cost Explorer | Cada chamada de GetCostAndUsage; páginas e tentativas manuais também geram requisições |
| Lambda | Invocações e duração × memória, inclusive falhas/retries; limites dependem da conta |
| S3 | Armazenamento, versões, PUT condicionais de guarda/relatório, LIST limitado, GET/HEAD de reconciliação e transferência |
| EventBridge | Tipo de evento/agenda e cotas aplicáveis; conferir tabela vigente |
| CloudWatch Logs | Ingestão e armazenamento conforme retenção, não apenas número de funções |
| Ollama/local | RAM, CPU, disco e energia; não é serviço de inferência sem custo material |
| CI GitHub | Minutos/armazenamento conforme plano e visibilidade do repositório |

Modelo de estimativa, sem valores inventados:

`C_total = N_ce × preço_ce + invocações/duração Lambda + GB-mês/requests/transferência S3 + logs + eventos`.

O template começa com agenda desabilitada. Antes de habilitar: estimar páginas reais com coleta autorizada, validar timeout, revisar versões/retention do bucket, verificar Free Tier elegível e estabelecer orçamento/alerta na conta por procedimento separado. Uma reserva diária limita execuções, não requisições de paginação. Bucket retido após remoção da stack continua podendo gerar cobrança. Não ativar agenda nem criar orçamento/recursos como parte desta validação.

Fontes oficiais para consulta futura (não verificadas por chamadas AWS nesta sessão):
- https://aws.amazon.com/aws-cost-management/aws-cost-explorer/pricing/
- https://aws.amazon.com/lambda/pricing/
- https://aws.amazon.com/s3/pricing/
- https://aws.amazon.com/cloudwatch/pricing/
- https://aws.amazon.com/eventbridge/pricing/
- https://aws.amazon.com/free/

## Estabilização do PR #8

A configuração proposta aumenta o timeout máximo da Lambda para60s mantendo128MB. Isso amplia a duração potencialmente faturável em falhas; não é uma medição de uso nem estimativa monetária. SDK serverless usa uma tentativa por operação e até5páginas CE. Uma recuperação manual pode autorizar a segunda tentativa do dia, portanto pode haver mais chamadas CE; nunca é apresentada como gratuita. Reconciliação de upload ambíguo evita recolher custos quando o artefato já existe, mas também utiliza requisições S3.

Relatórios diários são objetos distintos: versões não correntes sozinhas não limitariam seu crescimento. A stack agora expira objetos correntes reports/ após ReportRetentionDays (default90; opções30/60/90/180), versões antigas após30dias, guardas após7dias e versões antigas das guardas após30dias. Remove delete markers expirados. Retain protege bucket e grupo de logs na remoção; essa proteção não cancela cobrança nem remove recursos automaticamente. Reconciliar, desabilitar agenda e revisar recursos retidos antes de remoção futura autorizada.
