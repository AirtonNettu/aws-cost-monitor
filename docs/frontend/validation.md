# Validação e entrega do frontend

Escopo: React independente em `frontend/`; Python e Streamlit preservados.
Branch: `feat/react-dashboard`, base `01fb16c` de `origin/main`.

## Executar e revisar localmente

```bash
cd frontend
npm ci
npm run dev
```

Abra o endereço exibido pelo Vite no ambiente local. Não precisa configurar AWS,
Ollama ou FastAPI. Os dados são simulados e a interface informa isso.

```bash
npm test
npm run test:coverage
npm run lint
npm run build
npm run preview
```

Há testes de transporte HTTP, contratos, mocks e componentes. São verificados:
query strings e IDs escapados, falhas de rede/HTTP/JSON, timeout/cancelamento,
valores prontos do snapshot, filtros, busca/ordenação, variação zero/null e
períodos não equivalentes, estados IA, histórico vazio/detalhes/comparação,
exportação por capacidade, navegação, tema e foco do menu móvel.

## Verificações de navegador

Chromium headless, com Playwright e axe usados como ferramentas externas de
validação (não são dependências do aplicativo): cinco rotas no desktop 1440px,
menu e viewport móvel 375px, troca de tema, overflow e erros JavaScript. Regras
axe: wcag2a, wcag2aa e wcag21aa. Auditoria automatizada não substitui avaliação
manual com leitor de tela.

Os gráficos oferecem legenda com valores e tabela diária expandível. Teclado:
link para pular conteúdo, foco visível, controles nativos, navegação móvel com
foco no primeiro link e Escape para fechar. prefers-reduced-motion respeitado.

## Limites intencionais

- Contratos HTTP são propostas; nenhum endpoint Python foi criado.
- Mocks e conteúdos IA são fictícios. Zero chamadas AWS/Ollama.
- Histórico SQLite existente não contém timeline; a UI informa sua ausência.
- Exportação requer capacidade da API; fica desabilitada no modo mock.
- Nenhum cálculo de total, participação, comparação ou alerta em TypeScript.
- Sem autenticação, deploy, merge, PR ou coleta AWS nesta entrega.
- README.md e README.en.md preservam as instruções Python e documentam a SPA,
  variáveis públicas, mocks, contratos propostos e próximos trabalhos.

Resultados finais e evidências serão registrados após a última validação da branch.
