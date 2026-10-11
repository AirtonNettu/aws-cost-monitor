# Dashboard local · V1

Painel experimental da branch `feature/dashboard-v1`. A ferramenta de terminal continua funcionando como antes. Esta versão não cria infraestrutura, não consulta AWS e não chama Ollama. Importa o JSON que o Python já produz.

## Experimentar sem AWS

Na raiz do repositório, execute:

```bash
python -m http.server 8000 --bind 127.0.0.1 --directory dashboard
```

Abra **http://127.0.0.1:8000**. No Windows, use `py` no lugar de `python`, se necessário. Para encerrar, pressione Ctrl+C no terminal. O dashboard usa apenas a biblioteca padrão e não exige instalar as dependências AWS para demonstrar a interface.

Os dados iniciais são fictícios e estão identificados como demonstração. Use “Importar relatório JSON” para selecionar um relatório local de até 2 MB. Arquivos inválidos preservam o relatório anterior e exibem uma mensagem. “Ver demonstração” restaura os exemplos.

O arquivo fica apenas na memória do navegador. Não é enviado ao servidor, salvo em armazenamento local ou publicado no GitHub. O servidor deve disponibilizar somente a pasta `dashboard`, como no comando acima, sem expor `.env` ou relatórios.

## Usar um relatório real depois

Quando a coleta AWS já estiver configurada e validada no seu PC, defina `REPORT_FORMAT=json` e `AI_ENABLED=false` no `.env` local e execute o monitor como descrito no README principal. Importe o arquivo criado em `reports/`. Não adicione esse arquivo ou credenciais ao GitHub.

A consulta real ao Cost Explorer depende de permissões e pode ter cobrança; o painel não testa nem autoriza essa consulta. Integração real com Ollama também precisa ser validada separadamente. O painel apenas apresenta `ai_interpretation` e `ai_error` existentes no JSON.

Os totais, percentuais, comparações e alertas são os calculados pelo Python. A interface apenas formata, filtra e ordena. Créditos podem reduzir o total, enquanto a lista contém apenas custos positivos; percentuais podem ultrapassar 100%. A comparação é entre os dois períodos mais recentes, não necessariamente entre meses completos. Não há atualização automática nem histórico persistido.

## Testes

```bash
uv sync --frozen
uv run pytest
node --test dashboard/report.test.mjs
```

Node é necessário apenas para testar o JavaScript, não para usar o painel. Testes unitários simulam serviços externos: passar nesses testes não confirma acesso à sua conta AWS ou execução de um modelo no seu PC.

Próxima etapa: testar pessoalmente a coleta e, depois, avaliar uma API local autenticada para atualização automática. Esta V1 não é um serviço multiusuário para publicar na internet.
