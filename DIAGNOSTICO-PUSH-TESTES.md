# Diagnóstico automático de Push — ambiente de testes

Este workflow envia notificações reais de diagnóstico às **10h, 15h e 20h (horário de Brasília)** e registra o retorno do Firebase no banco configurado. Ele foi criado para o ambiente de testes; não deve usar credenciais ou banco de produção.

## Segredos necessários no GitHub

Em **Settings → Secrets and variables → Actions → New repository secret**, configure:

- `IBNE_TEST_DATABASE_URL`: URL do banco exclusivo de testes da Escala de Mídia IBNE.
- `IBNE_TEST_FIREBASE_SERVICE_ACCOUNT_JSON`: conteúdo JSON completo da conta de serviço do projeto Firebase `ibne-escala-midia-test`. Não coloque esse JSON no código, em issues ou no chat.
- `PUSH_DIAGNOSTICO_REGISTRO_IDS`: IDs numéricos dos registros da tabela `notificacoes_push` que foram explicitamente autorizados para receber mensagens de diagnóstico, separados por vírgula (por exemplo, `12,19`). Use somente os IDs conferidos no banco de testes.

O script **não envia nada** se faltar qualquer segredo, se o ambiente não estiver marcado como testes, se o projeto Firebase não for exatamente `ibne-escala-midia-test`, ou se nenhum registro autorizado estiver ativo com token. Registros ausentes/inativos são anotados sem envio. Tokens nunca são impressos nem salvos no histórico.

## Histórico persistente

O script cria a tabela `diagnostico_push_agendado` no banco configurado e registra horário, ID do registro Push, ID do usuário, hash curto do identificador do dispositivo, resultado do Firebase e eventual erro. O token completo não é registrado.

Resultados possíveis incluem:
- `firebase_aceitou_confirmacao_pendente`: Firebase aceitou o envio; **não prova entrega no celular**.
- `token_invalido_confirmado`: o Firebase informou explicitamente que o token não está registrado.
- `falha_envio_sem_desativar_token`: houve erro; o token permanece ativo.
- `ignorado`: o registro autorizado não estava ativo/disponível.

## Limite conhecido: confirmação de recebimento

A confirmação de recebimento no aparelho **ainda não está implementada**. Para completar a triangulação, será necessário um endpoint HTTPS de confirmação, com autenticação/validação e proteção contra falsificação, e o service worker de testes deverá enviar a confirmação a esse endpoint quando processar o Push. Não se deve classificar “sem confirmação” como token inválido nem desativar o dispositivo automaticamente.

## Execução

O workflow roda diariamente nos três horários acima e também pode ser iniciado manualmente em **Actions → Diagnóstico Push automático — ambiente de testes → Run workflow**. Configure e confira os três segredos antes de habilitar uma execução real.
