# CloudFormation — implantação e remoção planejadas

Estado: template validado estaticamente; **nenhum deploy, upload ou recurso AWS executado**. A stack não hospeda API/SPA nem persiste SQLite. Relatório HTML é privado, sem S3 Website público.

## Preparar e validar sem credenciais

```bash
uv run cfn-lint infra/serverless.yaml
uv run python scripts/package_lambda.py
uv run python scripts/package_lambda.py --validate
```

Pacote em reports/collector.zip contém uma lista explícita de fontes do coletor e as oito dependências transitivas do grupo `lambda` do uv.lock: boto3, botocore, s3transfer, jmespath, python-dateutil, six, urllib3 e python-dotenv. O SDK é incluído para evitar variações do SDK gerenciado. Não inclui dashboard/API, `.env`, perfis AWS, bancos, relatórios financeiros ou arquivos locais. Nenhum pacote novo foi adicionado: o grupo apenas seleciona dependências existentes.

Pré-requisitos de geração: uv no PATH, Python 3.14 e acesso ao índice/cache dos wheels travados. O instalador exige hashes e wheels para Linux x86_64/manylinux2014, compatíveis com o runtime proposto. Dependências nativas são recusadas; o conjunto atual é Python puro. A validação roda imports em processo Python3.14 `-I -S`, sem site-packages do projeto, com ambiente mínimo e diretório temporário. Não chama SDKs nem lê credenciais. Não substitui teste no runtime gerenciado da AWS.

O ZIP normaliza ordem, timestamps e permissões e inclui `artifact-manifest.json` com SHA-256 dos arquivos e do lockfile. Dois builds são comparados byte a byte por SHA-256 em teste. A reprodutibilidade comprovada vale para os mesmos fontes/lockfile e ferramenta Python/uv/zlib; não se promete igualdade entre compressores diferentes. `--validate` confere CRC, manifesto, caminhos e imports, sem baixar dependências. O manifesto verifica integridade, não assinatura/autenticidade. Guarde o checksum impresso fora do artefato para comparar na revisão. Scripts de console, bytecode e metadados de instalação temporários não entram no pacote.

A CI gera e valida o ZIP além de executar os testes de reprodutibilidade; não faz upload do artefato. Python 3.14/x86_64, 128MB e timeout60s são configuração proposta, não desempenho comprovado. Revisar em conta de teste antes de qualquer implantação real.

## Implantação futura por operador autorizado

1. Conferir custos, região, conta e permissões; usar identidade temporária e evitar impressão de IDs/ARNs.
2. Preparar bucket privado separado para artefatos, revisar o ZIP e registrar checksum; upload exige autorização própria.
3. Submeter template com EnvironmentName, ArtifactBucket, ArtifactKey e ScheduleState=DISABLED; revisar Change Set e IAM antes de executar.
4. Validar bucket privado/criptografia, logs e função sem executar CE automaticamente. Uma invocação real autorizada pode cobrar.
5. Habilitar agenda apenas após comprovar orçamento, duração e guardas. Não habilitar retries sem rever custo/idempotência.

Comando de referência, **não executado**:

```bash
aws cloudformation deploy --template-file infra/serverless.yaml \
  --stack-name cost-monitor-dev --capabilities CAPABILITY_IAM \
  --parameter-overrides EnvironmentName=dev ArtifactBucket=SEU_BUCKET_PRIVADO ArtifactKey=collector.zip ScheduleState=DISABLED
```

Sem credenciais no template. IAM coletor: ce:GetCostAndUsage (não aceita resource ARN específico), s3:PutObject/GetObject apenas reports/* e locks/*; ListBucket no bucket da stack somente para prefixo reports/* e max-keys<=1; logs apenas no grupo da função. Sem STS de identidade, IAM administrativo ou exclusão S3 ou exposição pública.

## Remover com proteção dos dados

1. Desabilitar agenda e aguardar execução terminar.
2. Identificar e guardar relatórios necessários por procedimento privado.
3. Revisar Change Set/recursos e executar exclusão da stack somente com autorização.
4. Bucket ReportsBucket e CollectorLogGroup têm DeletionPolicy/UpdateReplacePolicy Retain: permanece, com versões e potencial cobrança. A exclusão da stack não apaga esses dados nem os logs retidos.
5. Para remover bucket retido, operador deve aprovar e excluir versões/delete markers e então bucket; não há script destrutivo automático.
6. Bucket de artefatos não pertence à stack e tem ciclo de vida independente. Verificar cobranças remanescentes.

Região/runtime disponível, IAM efetivo, duração e remoção real **não foram verificados**. Expiração de locks7dias não substitui auditoria; logs têm retenção configurável7/14/30/90dias, versões antigas dos relatórios30dias. Relatório diário corrente expira conforme ReportRetentionDays (default90dias). Versões antigas de guardas expiram30dias; marcadores expirados são removidos. A função usa chave diária em reports/, não sobrescreve index.html. Ver ADR-002 e runbook para recuperação, rollout e reconciliação.
