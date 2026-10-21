# Persistência, segurança, custos e observabilidade

**Status:** requisitos e análise de lacunas; sem migrações ou alterações de runtime.

## SQLite atual: o que existe
`runs(id,created_at,period_start,period_end,total_cost,has_positive_cost,largest_service,previous_total,variation,alerts_json,ai_interpretation)` e `service_costs(run_id,service_name,amount,percentage)`. Não guarda snapshots completos por granularidade, tags disponíveis, `estimated`, `source`, série diária, modelo IA ou `equivalent_periods`.

### Lacunas obrigatórias para satisfazer o frontend
- **Filtro 7/30/90 + tag:** persistir `period_days`, `tag_key` e contexto de agrupamento; evitar retornar run incompatível.
- **Timeline:** persistir pontos diários reais ou retornar `[]`; não construir gráfico falso.
- **Estimated:** preservar o indicador da AWS por período/snapshot.
- **Comparison:** registrar datas dos dois períodos, equivalência e escopo; não comparar mês parcial com mês inteiro.
- **AI:** status, texto, campos estruturados, modelo, versão do prompt, tempo e erro seguro.
- **Proveniência:** `source`, `collected_at` timezone-aware, identificador de coleta, parâmetros.
- **Idempotência:** chave única lógica por janela, escopo, granularidade e instante de coleta; evitar snapshots duplicados.
- **Integridade:** ativar foreign keys, migrações reversíveis, índices e backups; transações atômicas.
- **Privacidade:** conta/ARN e tags podem revelar contexto; sanitizar logs e controlar acesso.

## Segurança de API
- Definir autenticação antes de publicação externa; não assumir que CORS autentica.
- Autorizar **cada** snapshot e download; nunca confiar apenas no ID.
- Se cookies forem usados, avaliar CSRF e SameSite; CORS limitado a origens explícitas.
- Validar limites de `days`, `limit`, `tag`, `id` e formato de exportação.
- SQL parametrizado; paths de relatórios não devem vir diretamente da URL.
- Limitar tamanho de resposta, número de jobs IA, requests por minuto e duração.
- Erros públicos sem stacktrace; logging interno estruturado com `request_id`.
- Credenciais AWS apenas no processo backend, via cadeia de credenciais boto3 e IAM mínimo.
- Ollama em loopback/rede privada, sem proxy público; aplicar isolamento por usuário quando necessário.

## FinOps e custos
- Leitura de snapshots do SQLite é padrão; **GET não chama AWS**.
- Coleta AWS somente em job separado, controlado, com limite explícito e opção desativada por padrão no desenvolvimento.
- Cost Explorer pode cobrar por requisição; valores, cota e Free Tier variam e precisam ser verificados na tabela vigente antes de ativar agendamento.
- Custo zero não pode ser garantido por README ou arquitetura.
- Não publicar AWS credentials nem criar recursos cloud sem autorização.
- No início, Ollama local reduz dependência de APIs pagas, mas consome CPU, RAM e energia.

## Observabilidade
- Logs JSON estruturados: `request_id`, rota, status, duração, `run_id` opaco, tipo de erro.
- Métricas: latência API, cache hit, idade do snapshot, contagem de coleta AWS, tempo de inferência, falha Ollama, taxa de contratos inválidos.
- Health checks separados: liveness não depende de Ollama; readiness informa dependências sem divulgar segredos.
- Evitar logar prompts completos, respostas sensíveis, tokens e identificadores AWS.
- Retenção definida e limpeza segura; alertas sobre dados desatualizados e jobs travados.

## Pontos concretos identificados na auditoria
1. `src/database/repository.py:get_history` faz consulta DESC e depois `reversed(rows)`; documentar e alinhar ordem esperada do contrato.
2. `src/analysis/finops_rules.py` emite tipo `untagged_resources`, mas Zod espera `untagged`; **normalizar no mapper ou corrigir contrato com testes**.
3. `src/analysis/cost_analyzer.py` usa `float`; estudar `Decimal` para serialização financeira, sem alterar cálculos sem testes de equivalência.
4. `src/aws/cost_explorer.py` substitui agrupamento SERVICE por TAG; não prometer ambos simultaneamente.
5. O README/AGENTS podem afirmar custo zero; validar custos atuais e não assumir gratuidade de Cost Explorer.
6. `src/main.py` grava snapshot após relatório; refatorar orquestração para que falhas de relatório não invalidem persistência planejada.
