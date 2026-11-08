# Operação e troubleshooting

## Inicialização local segura

```bash
uv sync --frozen --dev
uv run python scripts/seed_demo.py --database data/demo.db
export DATABASE_PATH=data/demo.db
export API_USERNAME=operator
read -r -s -p 'Senha local da API (16+ caracteres ASCII): ' API_PASSWORD
export API_PASSWORD
uv run uvicorn src.api.app:create_app --factory --no-access-log --host 127.0.0.1 --port 8000
```

A semente recusa sobrescrever arquivo existente; não remover banco de usuário para fazê-la passar. Todos os valores semeados são fictícios, source=mock. Em outro terminal:

```bash
cd frontend
npm ci
VITE_DATA_MODE=api npm run dev -- --host 127.0.0.1
```

Abra o endereço local impresso pelo Vite e entre com a credencial do servidor. Para demonstração sem API: `npm run dev` (modo mock padrão). `VITE_API_BASE_URL` padrão /api/v1; proxy do Vite aponta para 127.0.0.1:8000. CORS e hosting de produção não são configurados automaticamente.

## Banco e recuperação

1. Parar todos os escritores (CLI, Streamlit e coleta).
2. Fazer backup consistente: `uv run python -c "import sqlite3; a=sqlite3.connect('data/costs.db'); b=sqlite3.connect('data/costs-backup.db'); a.backup(b); b.close(); a.close()"`.
3. Iniciar API para executar migração aditiva. Testar ready e histórico autenticados.
4. Se necessário, parar processos e restaurar backup. Não apagar tabelas/arquivos em runtime para fazer testes passarem.
5. Backups contêm dados financeiros: manter fora do Git, com acesso restrito e retenção definida pelo operador. Schema legado não é promovido automaticamente: ver arquitetura.

## Coleta controlada

API nunca coleta. Uma chamada explicitamente autorizada de `src.operations.collection.collect_once(db_path, days=30, tag=None)` reserva o dia UTC em collection_jobs. Resoluções de configuração de tag são aplicadas antes da consulta e da gravação. Concluída retorna o run salvo somente para os mesmos parâmetros; outro escopo é recusado; novas chamadas no mesmo banco/dia não consultam AWS. Não há retry automático depois de falha ou estado running.

### Recuperação local explícita

Snapshot e sucesso do job agora são confirmados na mesma transação, sob BEGIN IMMEDIATE. A reserva inicial permanece durável; uma queda deixa running, mas não confirma snapshot órfão da tentativa. Leitores da API continuam operando; outro escritor ativo bloqueia a recuperação (timeout SQLite5s).

```bash
uv run python scripts/recover_collection.py local-status --database data/costs.db
# Após parar o processo/escritores e avaliar possível cobrança de nova coleta:
uv run python scripts/recover_collection.py local-recover --database data/costs.db \
  --expected-token TOKEN_OBSERVADO --confirm-stopped --allow-paid-retry
```

O status mostra somente data UTC, estado, tentativa, token operacional, horários, código seguro e run_id. Nunca imprime escopo/tag, credenciais ou valores financeiros. Recuperação exige o token atual; token obsoleto, job succeeded, escritor ativo ou duas tentativas já consumidas são recusados. Só há uma repetição manual no dia corrente. Depois da segunda falha, aguardar o próximo dia e investigar a causa; não editar/excluir a reserva para contornar o teto.

Antes de recuperar running: parar os processos responsáveis e verificar que não permanecem ativos. A confirmação não é um detector de processos. BEGIN IMMEDIATE e o token protegem o protocolo contra concorrência e finalizações de um proprietário antigo. Arquivos SQLite devem estar em armazenamento local com semântica de locking suportada, não em filesystem remoto sem garantias.

Reservas anteriores à estabilização sem token ou com referência ambígua não são reabertas automaticamente. Preservar backup e investigar histórico; aguardar o próximo dia, sem adivinhar associação a um snapshot ou liberar a reserva por SQL manual. A nova atomicidade evita repetir esse intervalo de inconsistência em futuras tentativas.

### Recuperação S3/Lambda — procedimento futuro, não executado nesta tarefa

A stack usa `reports/AAAA-MM-DD.html`, guarda `locks/AAAA-MM-DD.json` e estados running/failed/succeeded. Chave diária e IfNoneMatch impedem versões duplicadas do mesmo relatório. Sucesso exige verificar existência e metadado de escopo do artefato; coleta vazia não é publicação bem-sucedida. Consulta de ausência usa ListObjectsV2 com prefixo exato e MaxKeys1; não interpreta 403 de HEAD como chave ausente.

1. Desabilitar a agenda. Verificar a função, suas versões e invocações; aguardar término/timeout de todas as execuções (60s na configuração proposta). Não recuperar enquanto houver escritor ativo.
2. Inspecionar a guarda do dia com identidade autorizada. Não ler nem publicar o relatório para diagnosticar o estado. Comando abaixo faz leitura AWS e NÃO foi executado nesta estabilização:

```bash
uv run python scripts/recover_collection.py s3-status --bucket "$S3_BUCKET_NAME" --allow-aws-read
```

3. Registrar token, ETag e attempts. Para running, também aguardar recover_after (120s após reserva) e confirmar que a execução realmente terminou. Para failed, corrigir a causa primeiro. Não apagar guarda, relatório, versões ou delete markers como estratégia de retry.
4. Preparar o evento administrativo. Este comando apenas gera JSON, sem consultar AWS ou invocar a função:

```bash
uv run python scripts/recover_collection.py s3-event \
  --expected-token TOKEN_OBSERVADO --expected-etag '"ETAG_OBSERVADO"' \
  --confirm-stopped --allow-paid-retry > /tmp/finops-recovery.json
```

5. Somente após autorização operacional/custos, invocar a função uma vez com o evento. Exemplo futuro, não executado:

```bash
aws lambda invoke --function-name "$COLLECTOR_FUNCTION" \
  --invocation-type RequestResponse --cli-binary-format raw-in-base64-out \
  --payload fileb:///tmp/finops-recovery.json /tmp/finops-result.json
```

6. Verificar status e guarda novamente. O coordenador compara ETag/token/escopo e atualiza por IfMatch. Relatório já existente e de escopo correspondente é reconciliado, inclusive após a segunda tentativa, sem coletar outra vez. Caso contrário, permite no máximo a tentativa2. Repetir o evento antigo não autoriza outra execução.

403 de leitura, escopo divergente, guarda legada/malformada ou CAS concorrente falham de forma segura. Guardas legadas claimed não possuem identidade suficiente para recuperação automática: manter desabilitada a execução antiga, reconciliar privadamente o relatório legado e aguardar o próximo dia UTC para iniciar o novo protocolo. Não recuperar datas passadas com a janela do dia atual.

A transição pode falhar por rede ou timeout após publicar. Nesse caso, o relatório pode existir e a guarda continuar running/failed. Inspeção e reconciliação substituem o retry cego. Escrita condicional protege o artefato, mas não garante exactly-once da consulta CE ou ausência de requisições faturáveis.

CLI e Streamlit legados continuam disponíveis. Streamlit inicia em histórico local e usa cache de 24 horas por configuração no modo AWS. Isso não é trava global: alterar filtros, reiniciar processo ou executar CLI manualmente pode realizar novas consultas. Para política diária estrita usar coleta reservada/agenda preparada. Paginação até 20 páginas e duas tentativas por página; uma execução diária NÃO significa uma única requisição faturável.

## Sintomas e ações

| Sintoma | Diagnóstico e recuperação |
| --- | --- |
| API não inicia | Configurar usuário/senha ASCII adequada sem imprimir valores; conferir diretório gravável |
| 401 | Credencial inválida/ausente; entrar novamente; nunca colocar senha no bundle |
| 404 no snapshot | Não há janela/tag salva; consultar histórico; não fazer coleta automática |
| 422 | days deve ser 7/30/90, limit 1..50, formato json/csv |
| 503 | Banco ausente, bloqueado/corrompido ou snapshot inválido; verificar backup e permissão local |
| 500 | Usar X-Request-ID e logs seguros; não divulgar traceback ao navegador |
| Sem série diária | Coleta mensal ou registro legado não permite série; não interpolar valores inventados |
| IA indisponível | FinOps continua; configurar Ollama apenas em Python privado se desejado |
| Tela vazia após npm ci | Parar Vite antes de reinstalar; iniciar um único servidor com --force |
| Lambda sem relatório | Agenda desabilitada? Ver logs e reserva locks/AAAA-MM-DD.json; seguir recuperação explícita por token/ETag; não excluir guarda |

## Observabilidade e limites

API registra JSON event/http_request, rota padronizada, status, request_id e duração medida. Health não implica AWS/IAM/Ollama funcionais. Coleta local registra status no SQLite e eventos seguros; Lambda registra guarda, término e request_id. Não há dashboard de métricas, alarmes pagos, tracing distribuído ou integração CloudWatch da API local.

Coletor local/legado: SDK connect2s/read4s, até duas tentativas por requisição e até20páginas. Coordenador serverless: connect1s/read2s, uma tentativa por operação, até5páginas, timeout Lambda60s e concorrência1. Verifica tempo restante antes de começar trabalho, páginas e finalização; interrompe coleta sem publicar resultado parcial quando não há orçamento. Retentativas EventBridge/Lambda permanecem desabilitadas.

Budget é cooperativo: parsing, CPU, fluxo de rede e SDK real ainda podem exceder previsões; o timeout da Lambda é o limite final. Uma morte abrupta pode deixar a guarda running. Só validar com conta de teste autorizada no futuro, sem prometer SLA ou produção pela aprovação dos mocks. Retenção de relatórios correntes é configurável30/60/90/180dias (default90), versões antigas30dias, guardas correntes7dias e não correntes30dias. Logs e bucket são retidos na remoção da stack; avaliar custo e exclusão manual separadamente.


## Hardening dos handlers, UTC e pacote

- A infraestrutura continua usando `src.operations.serverless.lambda_handler`. Configurações antigas com `lambda_function.lambda_handler` agora delegam ao mesmo coordenador, inclusive em recuperação; não há coleta ou upload direto nesse ponto de entrada. O retorno legado foi alinhado às respostas operacionais do coordenador (por exemplo, configuração ausente503). `run_report` é helper interno da geração, não um handler suportado; não o configure na Lambda. `S3_OBJECT_KEY/index.html` não define o destino dos handlers públicos.
- O fim da consulta é o dia UTC reservado (exclusivo); o início é esse dia menos a janela em dias (inclusivo). O dia corrente incompleto permanece excluído. Reserva em31/dez às23:59:59UTC mantém essa janela mesmo se a coleta terminar em1/jan. O mesmo princípio vale para SQLite e recuperação. Uma recuperação do dia anterior continua bloqueada, conforme ADR-002; não recrie uma guarda para reconsultar o passado.
- Antes de preparar qualquer implantação futura, gere e valide o ZIP com os comandos de [infraestrutura](infrastructure-v02.md). Se houver falha de hash/import/CRC, não use o artefato: confira fontes e uv.lock, gere novamente e compare o checksum. Não tente corrigir incluindo a `.venv` inteira ou bancos locais. A geração requer uv/Python3.14 e acesso aos wheels ou cache. A validação é local, sem conta AWS.
