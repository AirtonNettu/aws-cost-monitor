# Auditoria técnica v0.2 — D0

Base auditada: `8aa5fd1` na branch `refactor/cloud-finops-v02`. A main não foi modificada. Leitura do roadmap, especificações backend/frontend, documentação V1, módulos Python, testes e SPA precedeu a implementação. Evidências abaixo são de código e execução local, sem conta AWS.

## Baseline executado

- Python 3.14.8: `python -m pytest -q`: **59 passaram**.
- Node 24.19.0: `npm test --prefix frontend`: **37 passaram**.
- Não há workflows CI/CD versionados na base. Dependências Python/Node travadas em uv.lock/package-lock.json.
- Git HTTPS funciona. A tentativa de API GitHub via gh recebeu `Forbidden`; isso não implica ausência de acesso Git. Tratar publicação de PR separadamente.

## Achados

| ID | Gravidade | Evidência | Impacto | Recomendação |
| --- | --- | --- | --- | --- |
| A01 | Alta | Nenhum src/api; React usa adaptadores mock/HTTP | SPA sem backend real | API /api/v1 autenticada e contratos Pydantic/Zod |
| A02 | Alta | repository.py grava apenas agregados positivos e datas sem timezone | Perda de créditos, estimated, série e escopo; filtros incompatíveis | Migração aditiva, snapshot validado transacional, preservar tabelas legadas |
| A03 | Alta | Streamlit chama get_costs a cada rerun; sem cache efetivo | Consultas potencialmente cobradas | Cache diário, atualização de tela sem invalidar coleta |
| A04 | Alta | report_generator.py injeta json.dumps de nomes em script | Nome contendo fechamento de script pode executar HTML | Escapar delimitadores HTML no JSON incorporado e testar |
| A05 | Alta | lambda_function.py retorna str(exc), bucket e custos; logs livres | Exposição acidental de contexto financeiro/identidade | Erros seguros, logs estruturados sem payload sensível |
| A06 | Média | cost_explorer.py cria cliente sem Config explícito; paginação sem limite | Retentativas e duração pouco controladas | Timeout finito, tentativas e páginas limitadas |
| A07 | Média | compare_periods compara últimos buckets; total soma toda janela | Percentual não corresponde ao KPI ou compara mês parcial | Comparar snapshots adjacentes com duração/escopo iguais; null quando não comprovável |
| A08 | Média | untagged_resources no Python vs untagged no Zod | Contrato rejeita alertas válidos | Normalizar no adaptador, com teste |
| A09 | Média | SQLite sem FK ativa, idempotência ou migração explícita | Órfãos, duplicação e incompatibilidade | FK, índice, transação e histórico de jobs com chave diária |
| A10 | Média | README e guias prometem 100% Free Tier/custo zero e tempos fixos | Expectativa financeira sem comprovação | Custos condicionais e fórmulas; sem estimativa inventada |
| A11 | Média | Um teste test_save_report_extensao_por_formato é redefinido no mesmo módulo | Caso HTML deixa de executar | Dar nome único e executar ambos |
| A12 | Média | Ollama textual com timeout; sem estruturação/avaliação/proveniência | Sem garantia de grounding semântico | Preservar IA opcional, não inventar campos; evolução estruturada segue planejada |
| A13 | Média | float em cálculos; métrica configurável mas analyzer lê UnblendedCost | Precisão binária e seleção de métrica incoerente | Rejeitar métrica incompatível na coleta; migração Decimal exige trabalho/testes próprios |
| A14 | Média | Sem template IaC nem segurança de bucket verificável | Deploy manual não reproduzível | CloudFormation validado estaticamente, bucket privado e IAM mínimo |

## Fronteiras preservadas e decisões

Python calcula e aplica regras; Ollama interpreta, React apresenta. API só lê SQLite, sem AWS/Ollama em GET. Demonstração usa snapshots sintéticos com source=mock mesmo em transporte HTTP real. Auth local de operador único com credencial fora do bundle; publicação multiusuário exige outra política. SQLite local não será tratado como armazenamento durável de Lambda. IaC cobre coletor/report privado S3; hospedar API/SPA na AWS permanece fora desta stack. Ver ADRs e plano de execução.

## Limites da auditoria

Não foram testados preços vigentes, cobrança, credenciais AWS, IAM efetivo de uma conta, implantação ou Ollama real. A revisão estática não comprova ausência de todas as vulnerabilidades. Resultados pós-correção serão registrados em docs/validation-v02.md.
