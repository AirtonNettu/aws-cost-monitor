---
trigger: always_on
---
# Security Guardrails Protocol — NETTO LABS

Este protocolo de segurança é ativado permanentemente em todas as interações e edições de código no repositório.

## 1. Prevenção de Vazamento de Segredos
- **Credenciais AWS:** Nunca insira ou versione strings que correspondam a chaves de acesso da AWS (`AKIA...`, `ASIA...`) ou chaves secretas (40 caracteres base64).
- **IDs de Conta:** Em documentações e exemplos de testes, use sempre IDs fictícios (exemplo: `123456789012`). Nunca use o ID real da conta do usuário.
- **Tokens e Senhas:** Nunca versione tokens JWT, chaves de API externas ou senhas hardcoded.

## 2. Higiene de Arquivos e Git
- Garanta que arquivos `.env`, bancos SQLite locais (`*.db`, `*.sqlite`), arquivos de dump, caches (`__pycache__`, `.pytest_cache`) e arquivos compactados (`*.zip`) permaneçam ignorados no `.gitignore`.
- Se um novo arquivo com potencial sensível for criado, adicione-o imediatamente ao `.gitignore`.

## 3. Segurança em APIs e Funções
- **Sanitização de Entrada:** Valide todos os argumentos de entrada (ex: parâmetros de data, flags de linha de comando) para evitar injeções ou caminhos maliciosos.
- **Divisão por Zero e Exceções:** Trate explicitamente divisões matemáticas e falhas de rede com blocos try/except defensivos.
- **Logs Limpos:** Nunca registre em log o conteúdo de credenciais ou dados pessoais identificáveis (PII).
