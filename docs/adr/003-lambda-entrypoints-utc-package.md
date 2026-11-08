# ADR-003 — Handlers seguros, calendário UTC e pacote Lambda fechado

Estado: implementado e validado localmente; execução na AWS não verificada.

## Problema e causa

O template já apontava para o coordenador, mas `lambda_function.lambda_handler` chamava diretamente a geração, permitindo configuração antiga sem reserva. Cost Explorer usava `date.today()` local, enquanto as reservas eram UTC; cruzar meia-noite podia alterar a janela após reservar. O ZIP anterior continha apenas fontes e dependia implicitamente do SDK gerenciado, sem verificar imports ou integridade.

## Decisão

Preservar o nome público antigo como delegação com import tardio para o coordenador, evitando ciclo de imports. Não preservar a semântica de upload direto em index.html nem a resposta financeira do handler antigo. A infraestrutura mantém seu ponto de entrada. Os testes existentes de geração continuam cobrindo o helper interno; novos testes cobrem ambos os handlers e execução duplicada.

Cost Explorer usa calendário UTC e aceita fim exclusivo explícito como argumento opcional. Os coordenadores passam o dia reservado, inclusive na recuperação SQLite. Start inclusivo e End exclusivo, janela e formato ISO existentes são preservados; não se inclui o dia incompleto.

Empacotar os módulos necessários por lista explícita e selecionar boto3/python-dotenv no grupo `lambda`, com transitivas e hashes do uv.lock. Não adicionar dependências novas. Incluir o SDK para eliminar dependência de sua versão gerenciada; rejeitar dependências nativas nesta implementação de Python puro. Alvo Python3.14/Linux x86_64, igual ao template. ZIP com ordem/timestamps/permissões fixos e manifesto SHA-256; validar CRC, allowlist, hashes e imports em Python isolado. CI gera e valida, sem publicar artefatos nem usar AWS.

## Consequências e limites

O pacote é maior que o ZIP apenas de fontes e exige índice/cache de wheels para gerar. Hashes não autenticam um artefato de origem desconhecida; use apenas build revisado. Reprodutibilidade foi testada no mesmo ambiente, não entre versões diferentes de Python/zlib/uv. Imports locais não comprovam funcionamento na Lambda, IAM, duração, custo ou disponibilidade regional. Guardas e recuperação continuam seguindo ADR-002. Sem mudança na arquitetura e sem deploy.
