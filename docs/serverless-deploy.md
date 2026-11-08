# Implantação serverless

O procedimento atual está em [infrastructure-v02.md](infrastructure-v02.md), com CloudFormation, bucket privado, IAM mínimo, retenção e remoção segura.

O fluxo manual antigo de S3 Website público não é o padrão recomendado: pode expor dados financeiros e não comprova custo zero. O handler legado permanece no código por compatibilidade; o template usa wrapper com guarda diária. Nenhum deploy foi executado. Ver [custos](costs-v02.md) antes de ativar qualquer agenda.
