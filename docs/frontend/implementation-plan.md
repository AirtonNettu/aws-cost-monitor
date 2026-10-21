# React dashboard — plano de implementação

**Objetivo:** entregar a SPA aprovada no pedido, preservando o backend.
**Spec:** [design.md](design.md). **Execução:** nesta sessão pelo agente principal.
**Stack:** React/TS strict, Vite, Tailwind, Router, Query, Recharts, Lucide, Zod, Vitest/RTL.

## Restrições globais

Frontend apenas em frontend/; documentação em docs/ e READMEs. Sem alterações Python, AWS real, segredos, PR ou deploy. Mocks explícitos; cálculos críticos permanecem Python. Branch feat/react-dashboard.

## Foco de revisão

Payload malformado nunca vira zero financeiro; timeout e abort chegam a estados seguros; variação zero difere de null; filtros não alteram totais indevidamente; histórico sem série e IA sem campos estruturados continuam utilizáveis.

## 1. Contratos e transporte

Arquivos: frontend/package.json, configurações Vite/TS/ESLint, src/api/{contracts,http,client}.ts, src/mocks/{adapter,fixtures}.ts/json, docs/frontend/api-contract.md.
Interface: DataClient.getSnapshot({days,tag},signal), getHistory(signal), getRun(id,signal), exportReport(id,format,signal); Snapshot/History/Filters tipados e validados.

- [x] Criar testes para validação, URL/query, HTTP/JSON inválido, timeout/cancelamento e isolamento mock.
- [x] Executar testes vermelhos antes de implementar comportamento.
- [x] Implementar schemas, transporte e fixtures sintéticas pré-calculadas em Python, sem levar código de cálculo ao frontend.
- [x] Validar e fazer commit de contratos e infraestrutura.

## 2. Interface e fluxos

Arquivos: src/app/, src/components/, src/features/{overview,costs,alerts,ai,history}/, src/styles.css, testes de componentes e utilitários.
Interface: App recebe DataClient; QueryProvider fornece cache; componentes recebem Snapshot validado. Rotas compartilham filtros e snapshot.

- [x] Escrever testes vermelhos de navegação, filtros/ordenação, comparação null/não equivalente/zero, tema, recuperação de erro, IA, histórico e exportação por capacidade.
- [x] Implementar layout acessível, cartões, gráficos com dados textuais, filtros, alertas, IA e histórico.
- [x] Executar suíte completa, lint e build; verificar navegador em 375px e desktop.
- [x] Fazer commits por unidade testável.

## 3. Documentação e revisão final

Arquivos: README.md, README.en.md, docs/README.md, docs/frontend/*.

- [x] Documentar arquitetura atual/futura, comandos, variáveis, cenários mock, contratos, limites de IA e próximos trabalhos.
- [x] Executar npm ci, npm test, npm run lint, npm run build, pytest e auditoria; revisar diff e segurança.
- [x] Registrar evidências e limitações; commit e push da branch. Não abrir PR.
