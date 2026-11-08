# CloudFormation — implantação e remoção planejadas

Estado: template validado estaticamente; **nenhum deploy, upload ou recurso AWS executado**. A stack não hospeda API/SPA nem persiste SQLite. Relatório HTML é privado, sem S3 Website público.

## Preparar e validar sem credenciais

```bash
uv run cfn-lint infra/serverless.yaml
uv run python scripts/package_lambda.py
```

Pacote em reports/collector.zip contém apenas módulos do coletor. Boto3 vem do runtime gerenciado; não inclui dependências pesadas do dashboard/API. Python 3.14/x86_64, 128MB e timeout15s são configuração proposta, não desempenho comprovado. Revisar em conta de teste antes de qualquer implantação real.

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

Sem credenciais no template. IAM coletor: ce:GetCostAndUsage (não aceita resource ARN específico), s3:PutObject apenas reports/* e locks/* no bucket da stack; logs apenas no grupo da função. Sem STS de identidade, IAM administrativo, leitura/exclusão geral S3 ou exposição pública.

## Remover com proteção dos dados

1. Desabilitar agenda e aguardar execução terminar.
2. Identificar e guardar relatórios necessários por procedimento privado.
3. Revisar Change Set/recursos e executar exclusão da stack somente com autorização.
4. Bucket ReportsBucket tem DeletionPolicy/UpdateReplacePolicy Retain: permanece, com versões e potencial cobrança. A exclusão da stack não apaga esses dados.
5. Para remover bucket retido, operador deve aprovar e excluir versões/delete markers e então bucket; não há script destrutivo automático.
6. Bucket de artefatos não pertence à stack e tem ciclo de vida independente. Verificar cobranças remanescentes.

Região/runtime disponível, IAM efetivo, duração e remoção real **não foram verificados**. Expiração de locks7dias não substitui auditoria; logs têm retenção configurável7/14/30/90dias, versões antigas dos relatórios30dias. Relatório corrente fica até política do operador.
