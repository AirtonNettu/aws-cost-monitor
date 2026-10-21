# Dashboard React — auditoria e decisões

Data: 2026-10-20. Escopo autorizado: frontend e documentação; implementação e push em `feat/react-dashboard`, sem PR, merge ou deploy.

## Auditoria anterior à implementação

Foram lidos README.md, README.en.md, AGENTS.md, CONTRIBUTING.md, docs/ e os módulos de coleta, análise, regras FinOps, persistência, IA, orquestração e dashboard Streamlit. A documentação V1 contém retratos antigos (39/55 testes); o código e a suíte atual (59 testes) prevalecem.

| Implementado em Python | Reaproveitamento e limites |
| --- | --- |
| get_costs | Períodos start/end/estimated e grupos UnblendedCost; DAILY/MONTHLY; paginação. Agrupar por tag substitui SERVICE, não fornece cruzamento simultâneo serviço/tag. |
| analyze_costs | services, total_cost, positive_services, percentages, largest_service, has_positive_cost. Créditos entram no total, mas não no ranking positivo. |
| compare_periods | previous_total/current_total/variation; pode ser null; compara os dois últimos grupos temporais, que podem ter durações distintas. Não assumir equivalência. |
| generate_alerts | type/severity/message: growth, concentration, top_services e untagged. Crescimento por limiar não é detecção estatística de anomalias. |
| SQLite | runs e service_costs; totais/percentuais/alertas/IA e datas. Não guarda série temporal detalhada, tags disponíveis, modelo de IA ou datas equivalentes de comparação. |
| interpret | Texto livre via Ollama exclusivamente em Python, com falha não bloqueante. Não oferece hoje quatro campos estruturados de recomendações. |
| reports | txt/json/markdown/html em disco; não existe download HTTP. |
| Streamlit | KPIs, gráficos, filtros, exportação CSV e seleção de histórico; permanece preservado. |

Não implementados: FastAPI, autenticação web, endpoints de snapshots/filtros/exportação, comparação entre execuções por API, IA estruturada, anomalias estatísticas, previsão, multi-conta. São propostas ou roadmap.

## Alternativas e escolha

1. **SPA React separada com adaptadores mock/HTTP (escolhida):** preserva o Python, contratos explícitos e substituição do transporte sem alterar componentes.
2. React incorporado ao Streamlit: reduz separação de responsabilidades e dificulta a futura API.
3. FastAPI junto com React agora: resolve transporte, mas viola o escopo frontend.

## Design

React + TypeScript strict, Vite, Tailwind CSS, React Router, TanStack Query, Recharts e Lucide. Vitest + Testing Library para comportamento. Zod valida respostas externas em runtime, evitando exibir payloads financeiros malformados; é a única dependência adicional de runtime além da stack e seus pares.

Sidebar com cinco rotas: `/`, `/costs`, `/alerts`, `/ai`, `/history`; detalhe `/history/:runId`. Tema escuro inicial com alternativa clara persistida; navegação móvel com botão acessível. Paleta grafite, verde esmeralda e cores de gráfico distintas; números tabulares, cartões, tabelas e legendas legíveis.

Mocks ficam isolados e carregados apenas no modo mock. Cenários de sucesso, vazio, falha, carregamento e estados IA podem ser selecionados por variável Vite. Badge permanente de simulação. Sem chamadas AWS/Ollama, sem credenciais, sem geração de consultas cobradas. Nenhum texto mock representa achado real.

Contratos propostos em `api-contract.md`: snapshots de leitura com KPIs prontos; períodos com fim exclusivo; metadados de origem, moeda, estimativa e equivalência. Filtro de período/tag busca snapshot completo pelo adaptador. Serviço/pesquisa/ordenação restringem visualmente tabela e gráficos, mantendo KPIs e alertas identificados como pertencentes ao snapshot. Sem recomputar totais, variações, alertas ou recomendações no navegador.

AI preserva texto livre atual; seções estruturadas opcionais somente quando fornecidas pelo backend. Processando/indisponível não bloqueiam finanças. Sem inferir desperdícios; renderizar texto escapado. Exportação somente com capacidade anunciada pelo backend; mocks não anunciam download real. Histórico compara lado a lado valores fornecidos, sem calcular variações entre execuções.

Query sem refetch em foco ou polling; atualizar relê snapshot em cache no servidor, nunca dispara coleta AWS. Cliente HTTP com timeout, abort/cancelamento, erros seguros e validação de payload. Não há fallback silencioso de HTTP para mock.

## Critérios de aceite

- [x] Cinco áreas navegáveis, detalhe histórico e comparação lado a lado.
- [x] KPIs vindos do snapshot; comparação indisponível para períodos não equivalentes ou variação null.
- [x] Série temporal e distribuição, com tabela textual acessível e estados vazios.
- [x] Período/tag suportados pelo transporte; busca/serviço/ordenação apenas de apresentação, com escopo explícito.
- [x] Carregamento, erro recuperável, dados vazios, IA processando/sucesso/indisponível e histórico vazio.
- [x] Dark/light, teclado, labels, foco visível, layout sem overflow em 375px e desktop.
- [x] Testes de contratos, HTTP (erro/timeout/cancelamento), filtros, navegação, histórico e IA.
- [x] npm ci, testes, lint, TypeScript e build aprovados; 59 testes Python preservados e auditoria executada.
- [x] READMEs PT/EN e contratos distinguem implementado, simulado e planejado.
- [x] Commits por tarefa e push sem PR.
