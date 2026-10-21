# Diagnóstico Push automático — TESTES

**Instruções atualizadas:** consulte [DIAGNOSTICO-PUSH-SEM-GITHUB-SECRETS.md](./DIAGNOSTICO-PUSH-SEM-GITHUB-SECRETS.md).

O fluxo antigo baseado em GitHub Secrets não deve ser usado. A automação atual chama o serviço privado Google Cloud Run por OIDC e não lê GitHub Secrets.

## Estado real

- O workflow de agendamento foi alterado para OIDC.
- O serviço de diagnóstico está versionado em `diagnostico-api/`.
- O Worker ACK do PWA de testes já tem código no repositório.
- Ainda é necessário provisionar e configurar os recursos de nuvem, o acesso privado ao banco e o endpoint ACK. Até essas etapas serem feitas e um teste real confirmar o aparelho, não considerar o diagnóstico operacional.

## Regras de segurança

- Usar somente Firebase `ibne-escala-midia-test` e banco de dados de testes.
- Não guardar chaves Firebase nem credenciais de banco no código.
- Não configurar GitHub Secrets para esse fluxo.
- Não alterar a PWA oficial nem o aplicativo de produção.
- O script nunca desativa tokens automaticamente.

## Interpretação

- 🟢 Somente quando o service worker da PWA de testes registra confirmação ACK no banco.
- 🟡 Firebase aceitou o envio, mas não houve ACK; isso não prova que o aparelho não recebeu.
- 🔴 Falha explícita de envio.
- Três dias consecutivos de falhas explícitas devem ser destacados no painel administrativo.
