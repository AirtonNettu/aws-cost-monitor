# ADR-002 — Recuperação explícita e orçamento da coleta

Status: adotada na estabilização do PR #8; nenhuma execução AWS autorizada nesta tarefa.

## Diagnóstico e decisão

A reserva SQLite era confirmada antes de salvar o snapshot, mas a confirmação do job vinha depois em outra transação. Interrupção nesse intervalo deixava snapshot válido com job running. A guarda S3 era apenas claimed, sem resultado, proprietário ou tentativa, e o upload versionado podia duplicar relatório após resposta de rede ambígua.

- SQLite: manter reserva inicial durável; manter exclusão de escritores com BEGIN IMMEDIATE durante uma tentativa. Gravar snapshot e sucesso do job na mesma transação. Identificador de tentativa impede que um processo antigo finalize uma reserva transferida.
- Recuperação local: comando administrativo com identificador esperado, confirmação de processo parado e teto de duas tentativas por dia. Não há endpoint HTTP nem reexecução automática de jobs failed/running. Recuperação bloqueia diante de escritor ativo e só vale para o dia UTC corrente.
- S3: guarda com estado, tentativa, token e escopo; transições condicionais por ETag. Recuperação administrativa exige token/ETag esperado, confirmação de execução parada e lease vencido para running. Máximo de duas tentativas, sem remoção de guarda.
- Publicar um relatório privado por dia com escrita IfNoneMatch e metadado de escopo. LIST com prefixo exato/MaxKeys1 e HEAD somente de objeto listado reconciliam sucesso ambíguo antes de nova coleta. O handler legado conserva seu contrato; o wrapper usa chave diária para eliminar duplicação de versões do mesmo relatório.
- Lambda: manter 128 MB, concorrência1 e agenda desabilitada. Aumentar timeout proposto de15s para60s: até cinco páginas CE, cliente serverless com uma tentativa e timeouts1s/2s, mais guarda, reconciliação e publicação. Checar tempo restante antes de operações; não interpretar esse limite como SLA comprovado.

## Consequências e limites

SQLite mantém um bloqueio de escrita durante rede; leitores da API continuam independentes, mas outros escritores podem receber busy. No S3, ETag protege a guarda, não substitui o dever operacional de parar invocações e aguardar o timeout antes da recuperação. Uma função morta pode deixar running. Guardas legadas sem metadados não são liberadas automaticamente. Nenhuma garantia de exactly-once no transporte AWS; escrita condicional evita duplicação do artefato diário. GetObject é acrescentado apenas aos prefixos do coletor; ListBucket exige prefixo reports/* e max-keys<=1, sem DeleteObject. Não inferir ausência a partir de403: S3 pode negar HEAD de chave inexistente sem permissão de listagem. Confirmação succeeded exige artefato verificado, mesmo quando o handler legado retornou200 sem custos.
