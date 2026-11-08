# ADR-001 — Fronteiras e segurança da v0.2

Status: adotada para esta entrega, conforme escopo autorizado no roadmap.

## Decisões

1. FastAPI /api/v1 é somente leitura de SQLite. Alternativas: consultar Cost Explorer por GET (rejeitada por cobrança e latência), migrar para banco gerenciado (rejeitada por infraestrutura desnecessária).
2. API/SPA locais para um operador: HTTP Basic com usuário/senha configurados exclusivamente no servidor, senha de no mínimo 16 caracteres. React mantém Authorization apenas em memória e permite sair; nenhum segredo VITE_*. Sem credenciais, a API não inicia. Todas as rotas de dados/download exigem o mesmo principal com permissão de leitura do workspace. Não é solução multiusuário ou multitenant. TLS é obrigatório fora de loopback; CORS não substitui autenticação. Sem cookies de sessão ou endpoints de escrita, não há ações CSRF.
3. Persistência aditiva: manter runs/service_costs e adicionar snapshots completos validados e collection_jobs. Dados antigos sem metadados não serão promovidos para snapshots confiáveis automaticamente. Backup precede atualização; restauração do arquivo é o rollback.
4. Comparação na SPA usa agregados de janelas adjacentes com mesma duração e tag/source; não reutilizar percentual entre buckets como comparação da janela inteira. Alertas do snapshot usam essa comparação.
5. IA continua opcional, textual e exclusivamente Python. Campos estruturados não são inventados. Sem jobs de IA novos nesta entrega.
6. IaC prepara coletor Lambda, agenda diária desabilitada por padrão, logs com retenção, bucket privado criptografado e acesso mínimo. SQLite é local, não armazenamento de Lambda. API na nuvem, entrega pública de relatórios e autenticação corporativa exigem outra decisão.

## Consequências

Uma credencial autoriza todos os snapshots do workspace, portanto só um operador deve usar esta versão. Não publicar o servidor de desenvolvimento. Atualizar a página exige novo login. Filtros só anunciam snapshots realmente persistidos. Dados ausentes resultam em 404/503, nunca em coleta ou mock silencioso.

Estabilização complementar: ver ADR-002 para recuperação explícita, timeout60s, artefatos diários e permissões de reconciliação. O modelo local de operador único permanece inalterado.
