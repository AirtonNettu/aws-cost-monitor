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

## Resultados finais

| Validação executada | Resultado |
| --- | --- |
| npm ci com package-lock.json | Instalação limpa reproduzida |
| npm test / npm run test:coverage | 37 testes, 7 arquivos, todos passaram |
| Cobertura V8 do escopo configurado | 96,90% linhas, 95,12% statements, 90,17% branches, 92,85% funções |
| Cliente HTTP (http.ts) | 100% statements, branches, funções e linhas |
| npm run lint | 0 erros e 0 avisos |
| npm run build | TypeScript strict e Vite aprovados |
| pytest -q | 59 testes Python passaram |
| scripts/security_audit.py | 0 alertas, 0 achados |
| npm audit --omit=dev | 0 vulnerabilidades conhecidas nas dependências de produção |
| Chromium + axe na distribuição de produção | Cinco rotas desktop e IA mobile em tema claro: 0 violações nas regras executadas |
| Navegação móvel 375px | Sem overflow horizontal, menu e troca de tema funcionais |
| Console e rede, modo mock | 0 erros JavaScript, 0 requisições externas |
| Modo API com HTTP interceptado no navegador | Snapshot validado renderizado, download anunciado recebido, HTTP 500 tratado sem expor corpo ou cair em mock |
| Preservação do backend | Nenhuma alteração em src/, tests/, pyproject.toml, uv.lock, main.py, dashboard.py ou lambda_function.py |

A cobertura não inclui arquivos de bootstrap, fixtures JSON ou setup DOM; o
escopo exato está em vite.config.ts. Os 100% do cliente HTTP não representam
100% de cobertura de toda a aplicação. Nenhuma integração real FastAPI/AWS/Ollama
foi validada ou declarada implementada.

### Revisão independente e regressões

Uma revisão independente encontrou três problemas de apresentação. Todos foram
reproduzidos em testes vermelhos, corrigidos e validados com a suíte completa:

1. Filtro de serviço/pesquisa permanecia oculto ao voltar de custos para visão
   geral. A identidade do conteúdo agora inclui a seção e reinicia esses filtros.
2. O anel normaliza custos positivos visíveis, mas a legenda mostrava percentuais
   do snapshot sem distinguir os escopos. Ambos os escopos agora estão explícitos.
3. Créditos/zeros mudavam os índices de cores dos arcos em relação à legenda.
   As cores agora são associadas ao nome do serviço no snapshot completo.

Também foram cobertos cancelamento HTTP em andamento e timeout durante a leitura
do corpo. Na revisão visual, corrigimos a rolagem inicial causada pelo foco em
mobile e garantimos foco do menu/Escape. Nenhum achado da revisão foi adiado.

Durante as verificações, executar npm ci enquanto dois servidores Vite estavam
ativos invalidou o cache compartilhado de dependências otimizadas e causou tela
vazia local. Reiniciar um único servidor com --force restabeleceu o fluxo; a
validação final usou npm run preview sobre o build de produção. Isso foi um
problema do procedimento de validação, não uma falha persistente da SPA.

### Capturas para revisão

Todas as capturas usam apenas dados simulados:

- [Visão geral no desktop](assets/overview-desktop.png)
- [Visão geral no celular](assets/overview-mobile.png)
- [Analista IA no tema claro, celular](assets/ai-light-mobile.png)

### Arquivos da entrega

- `frontend/package.json`, `package-lock.json`, `tsconfig.json`, `vite.config.ts`,
  `eslint.config.js`, `.gitignore`, `index.html`: ferramentas e execução.
- `frontend/src/api/`: contratos Zod/TypeScript, cliente HTTP, seleção de adaptador
  e testes de transporte/contratos.
- `frontend/src/app/`: App, Layout, contexto/hooks e testes de navegação/fluxos.
- `frontend/src/components/`: gráficos, KPIs/comparação, tabela, exportação,
  carregamento/erro/vazio e testes de regressão.
- `frontend/src/features/{overview,alerts,ai,history}/`: áreas funcionais; custos
  reutiliza o conteúdo de snapshot em overview.
- `frontend/src/mocks/`: fixtures sintéticas e adaptador com cenários e testes.
- `frontend/src/lib/format.ts`, `src/test/setup.ts`, `src/main.tsx`, `src/styles.css`:
  formatação, suporte aos testes, bootstrap e temas responsivos.
- `README.md`, `README.en.md`, `docs/README.md`: documentação existente atualizada.
- `docs/frontend/{design,implementation-plan,api-contract,validation}.md` e
  `docs/frontend/assets/`: auditoria, plano, contratos, evidências e capturas.
- `.gitignore` da raiz: acrescentada proteção para logs locais.

Para listar cada arquivo e cada commit: `git diff --name-status origin/main...HEAD`
e `git log --oneline origin/main..HEAD`.

## Integração e revisão humana

A branch será enviada ao remoto sem abrir Pull Request. PR, merge, deploy,
FastAPI e evolução real do Ollama aguardam etapas posteriores. Revisar a
interface e os contratos propostos antes de autorizar o PR.
