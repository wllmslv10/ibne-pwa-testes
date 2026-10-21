# Diagnóstico automático de Push — somente TESTES

O agendamento e a confirmação ficam no repositório isolado `wllmslv10/ibne-pwa-testes`. O script também foi mantido na branch `visual/ibne-visual-1-0` do aplicativo de testes. A produção e a PWA oficial não participam do diagnóstico.

## 1. Configurar os segredos

No repositório `wllmslv10/ibne-pwa-testes`, abra **Settings → Secrets and variables → Actions** e cadastre:

- `IBNE_TEST_DATABASE_URL`: URL do banco Neon usado exclusivamente pelo aplicativo de testes.
- `IBNE_TEST_FIREBASE_SERVICE_ACCOUNT_JSON`: JSON completo da conta de serviço do projeto Firebase `ibne-escala-midia-test`.
- `PUSH_DIAGNOSTICO_REGISTRO_IDS`: IDs numéricos, separados por vírgula, dos registros ativos de `notificacoes_push` no banco de testes autorizados a receber as mensagens de diagnóstico.
- `CLOUDFLARE_API_TOKEN`: token Cloudflare com permissão para publicar Workers.
- `CLOUDFLARE_ACCOUNT_ID`: ID da conta Cloudflare.

O segredo `PUSH_DIAGNOSTICO_ACK_URL` será adicionado depois de publicar o Worker, conforme a etapa 2.

## 2. Publicar o endpoint de confirmação

No mesmo repositório, abra **Actions → Publicar confirmação Push — TESTES** e execute **Run workflow**. O workflow utiliza `IBNE_TEST_DATABASE_URL` para configurar a conexão segura do Worker com o banco de testes.

O log informará a URL HTTPS do Worker. Copie-a e acrescente `/ack`. Em seguida, cadastre o endereço completo como segredo `PUSH_DIAGNOSTICO_ACK_URL` no repositório `wllmslv10/ibne-pwa-testes`.

## 3. Iniciar a primeira verificação

Depois de configurar os segredos e publicar o Worker:
1. Abra **Actions → Diagnóstico Push automático — TESTES**.
2. Clique em **Run workflow** para executar a primeira verificação.
3. Confira os resultados no histórico do workflow e no painel de monitoramento da aplicação de testes.

O workflow também está agendado para três ciclos diários em horários variados. O agendamento do GitHub Actions pode não executar exatamente no minuto programado; a execução manual serve para a primeira validação.

## Como interpretar as bolinhas

- 🟢 O service worker da PWA de testes confirmou que exibiu a notificação e a confirmação foi registrada no banco.
- 🟡 O Firebase aceitou o envio, mas não chegou confirmação do aparelho em cinco minutos. Isso, por si só, não prova falha de entrega.
- 🔴 O envio falhou explicitamente. Três dias consecutivos com falhas explícitas geram um alerta no painel.
- O script nunca desativa tokens automaticamente.
- Se o endpoint não estiver configurado, o diagnóstico não consegue confirmar o recebimento e não repetirá o envio apenas por falta de confirmação.

**Não coloque senhas, URLs de banco ou JSON da conta Firebase nos arquivos do repositório ou em mensagens.** Cadastre esses valores apenas como segredos no GitHub.
