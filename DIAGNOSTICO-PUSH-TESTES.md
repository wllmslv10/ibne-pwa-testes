# Diagnóstico automático de Push — ambiente de testes

O fluxo está preparado para enviar notificações reais às **10h, 15h e 20h (horário de Brasília)** e distinguir a aceitação do Firebase da confirmação enviada pelo service worker do PWA. Ele é exclusivo do ambiente de testes e não deve usar credenciais nem banco de produção.

## Antes de ativar os envios

1. Publique o endpoint ACK em Cloudflare Workers seguindo a seção abaixo.
2. Confirme o banco de testes e o registro `notificacoes_push` autorizado.
3. Configure os segredos do GitHub descritos a seguir.
4. Execute o workflow manualmente e verifique o resultado antes de deixar o agendamento diário operar.

## Endpoint de confirmação (ACK)

O código fica em `ack-worker/`. Para publicar:
- Crie um Cloudflare Worker chamado `ibne-push-ack-testes`.
- No Cloudflare, defina o segredo do Worker `DATABASE_URL` com a URL do **banco de testes** (Settings/Variables and Secrets).
- No GitHub do repositório `ibne-pwa-testes), configure os segredos `CLOUDFLARE_API_TOKEN` e `CLOUDFLARE_ACCOUNT_ID`.
- Execute Actions → **Publicar endpoint ACK do Push de testes** → Run workflow.
- Copie a URL HTTPS pública do Worker, acrescentando `/ack`. Ela será o segredo `PUSH_DIAGNOSTICO_ACK_URL`.

O endpoint só aceita POST de origem `https://wllmslv10.github.io`, exige ID de tentativa e nonce aleatório exclusivo, e atualiza somente a linha cujo nonce corresponde. Ele não recebe nem registra o token FCM. A confirmação significa que o service worker de testes processou a mensagem e conseguiu chamar o endpoint; não é uma confirmação de leitura humana.

## Segredos do workflow de diagnóstico

Em **Settings → Secrets and variables → Actions → New repository secret**, configure:
- `IBNE_TEST_DATABASE_URL`: URL do banco EXCLUSIVO de testes.
- `IBNE_TEST_FIREBASE_SERVICE_ACCOUNT_JSON`: JSON completo da conta de serviço do projeto `ibne-escala-midia-test`.
- `PUSH_DIAGNOSTICO_REGISTRO_IDS`: IDs numéricos explicitamente autorizados da tabela `notificacoes_push`, separados por vírgula.
- `PUSH_DIAGNOSTICO_ACK_URL`: URL HTTPS do endpoint publicado, terminada em `/ack`.

O workflow não envia nada se faltar qualquer segredo. O script bloqueia conta Firebase de outro projeto e só consulta os IDs explicitamente autorizados, ativos e com token no banco configurado. **Não use IDs desconhecidos nem o banco/credenciais de produção.**

## Horários e execução

O agendamento usa cron UTC `0 13,18,23 * * *`, equivalente a 10h, 15h e 20h em Brasília (UTC-3). O GitHub Actions pode atrasar execuções agendadas; os horários são alvos, não garantia de execução exata. Também é possível iniciar em Actions → **Diagnóstico Push automático — ambiente de testes** → Run workflow.

## Como interpretar

- `confirmado_no_aparelho`: service worker recebeu/processou a mensagem e confirmou ao endpoint.
- `firebase_aceitou_confirmacao_pendente`: Firebase aceitou a solicitação, mas ainda não há ACK.
- `token_invalido_confirmado`: Firebase informou token não registrado.
- `falha_envio_sem_desativar_token`: falha de envio; token continua ativo.
- `ignorado`: registro autorizado não estava ativo/disponível.

O script não desativa tokens automaticamente. O endpoint e o workflow precisam ser publicados/configurados e testados antes de afirmar que a triangulação está operacional.
