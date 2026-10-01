# Troubleshooting — AWS Cost Monitor V1

> Guia baseado nos comportamentos reais do código. Cada item cita a mensagem/condição que o código realmente produz.

## "[ERRO] Falha ao coletar custos: Credenciais da AWS não encontradas ou incompletas..."

- **Causa:** boto3 não encontrou credenciais (ou estão incompletas).
- **Origem no código:** `get_costs` captura `NoCredentialsError`/`PartialCredentialsError`.
- **Solução:** rode `aws configure` ou defina as variáveis de ambiente padrão da AWS. Verifique com `uv run python src/test_aws.py`.

## "[ERRO] ... Permissão insuficiente para consultar o Cost Explorer..."

- **Causa:** a identidade AWS não tem `ce:GetCostAndUsage`.
- **Origem:** `ClientError` com código `AccessDenied`/`AccessDeniedException`/`UnauthorizedOperation`.
- **Solução:** anexe uma policy com `ce:GetCostAndUsage` (ver [aws-permissions.md](aws-permissions.md)).

## "[ERRO] ... O AWS Cost Explorer retornou um erro (<código>): ..."

- **Causa:** outro erro de API (ex.: parâmetro inválido, throttling).
- **Origem:** `ClientError` com código fora do conjunto de acesso negado.
- **Solução:** leia o código entre parênteses; valide `COST_GRANULARITY`/`COST_METRIC`/janela de datas em [configuration.md](configuration.md).

## "[ERRO] ... Falha de comunicação com a AWS: ..."

- **Causa:** problema de rede/endpoint (`BotoCoreError`).
- **Solução:** verifique conectividade e a região `AWS_REGION`.

## "[AVISO] O Cost Explorer não retornou dados para o período..."

- **Causa:** `get_costs` retornou lista vazia.
- **Origem:** checagem `if not costs` em `main.run` (encerra com código 0).
- **Solução:** aumente `COST_PERIOD_DAYS` ou confirme que a conta tem custos no intervalo.

## "[AVISO] IA indisponível: Não foi possível conectar ao Llama em http://localhost:11434..."

- **Causa:** servidor Llama/Ollama não está rodando no endpoint configurado.
- **Origem:** `ConnectionError` em `interpret` → `LlamaUnavailableError`, capturado por `main.run`.
- **Impacto:** o relatório é gerado normalmente, sem a seção de IA.
- **Solução:** inicie o servidor (ex.: Ollama) e confira `LLAMA_BASE_URL`/`LLAMA_MODEL`, ou defina `AI_ENABLED=false` para desativar a IA de propósito.

## "[AVISO] IA indisponível: O Llama não respondeu dentro de Ns."

- **Causa:** timeout.
- **Solução:** aumente `LLAMA_TIMEOUT` ou use um modelo mais leve.

## Relatório sai com "Interpretação da IA: Indisponível. Camada de IA desativada por configuração (AI_ENABLED=false)."

- **Causa:** `AI_ENABLED` não está em `{"1","true","yes"}`.
- **Solução:** defina `AI_ENABLED=true` se quiser a interpretação.

## Relatório mostra "Nenhum serviço apresentou custo positivo no período."

- **Causa:** `has_positive_cost` é falso (sem serviços com valor > 0).
- **Nota:** comportamento esperado, não é erro. Pode ocorrer em contas sem custos no período.

## Relatório mostra "Variação: indisponível (período anterior com custo zero)."

- **Causa:** `previous_total == 0`, variação definida como `None`.
- **Nota:** comportamento esperado (divisão por zero evitada).

## Relatório mostra "Não há períodos suficientes para comparação."

- **Causa:** `compare_periods` recebeu menos de dois períodos.
- **Nota:** com `MONTHLY` e janela de 30 dias, pode haver só um período. Comportamento esperado.

## `ValueError: A variável de ambiente ... não é um inteiro válido.`

- **Causa:** `COST_PERIOD_DAYS` ou `LLAMA_TIMEOUT` definidas com valor não-inteiro.
- **Origem:** `config._get_int`, na importação de `src.config`.
- **Solução:** corrija o valor no ambiente/`.env`.

## Erro de dependência / import

- **Causa:** ambiente não sincronizado.
- **Solução:** `uv sync --dev`. Rode os comandos via `uv run ...` para usar o ambiente do projeto.

## Testes falhando

- **Solução:** `uv run pytest -v` para ver o teste específico. Os testes não dependem de AWS/Llama; falhas indicam mudança de código ou ambiente. Ver [testing.md](testing.md).

## Relatório não aparece no Git

- **Nota:** isto é esperado. O `.gitignore` ignora `reports/*` (exceto `.gitkeep`). O caminho do arquivo gerado é impresso por `main.run`.
