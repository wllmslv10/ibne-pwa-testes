# Diagnóstico automático de Push — somente TESTES

A produção não participa deste diagnóstico. O envio e o agendamento ficam na branch `visual/ibne-visual-1-0` do repositório `wllmslv10/escala-midia-ibne`. A confirmação do aparelho fica na PWA isolada `wllmslv10/ibne-pwa-testes`.

## 1. Segredos do agendador (repositório escala-midia-ibne)

Abra **Settings → Secrets and variables → Actions** em `wllmslv10/escala-midia-ibne` e cadastre:
- `IBNE_TEST_DATABASE_URL`: URL do banco Neon usado exclusivamente pelo aplicativo de testes.
- `IBNE_TEST_FIREBASE_SERVICE_ACCOUNT_JSON`: JSON completo da conta de serviço do projeto Firebase `ibne-escala-midia-test`.
- `PUSH_DIAGNOSTICO_REGISTRO_IDS`: IDs numéricos, separados por vírgula, dos registros ativos de `notificacoes_push` no banco de testes autorizados a receber as mensagens de diagnóstico.
- `PUSH_DIAGNOSTICO_ACK_URL`: URL HTTPS do Worker publicado na etapa 2, terminando em `/ack`.

O workflow de diagnóstico está em **Actions → Diagnóstico Push automático — TESTES**. Ele roda três vezes por dia em horários variados e também pode ser iniciado manualmente.

## 2. Publicar o endpoint de confirmação (repositório ibne-pwa-testes)

No repositório `wllmslv10/ibne-pwa-testes`, abra **Settings → Secrets and variables → Actions** e cadastre:
- `CLOUDFLARE_API_TOKEN`: token Cloudflare com permissão para publicar Workers.
- `CLOUDFLARE_ACCOUNT_ID`: ID da conta Cloudflare.
- `IBNE_TEST_DATABASE_URL`: a mesma URL do banco Neon de testes, necessária para que o Worker grave confirmações nesse banco.

Depois, abra **Actions → Publicar confirmação Push — TESTES** e execute **Run workflow**. O log informará a URL HTTPS do Worker. Copie a URL e acrescente `/ack`; cadastre o endereço completo como `PUSH_DIAGNOSTICO_ACK_URL` nos segredos do repositório `escala-midia-ibne`.

## 3. Primeira execução

Após configurar os segredos e publicar o Worker:
1. Abra **Actions → Diagnóstico Push automático — TESTES** no repositório `escala-midia-ibne`.
2. Clique em **Run workflow** para iniciar a primeira verificação.
3. Confira o resultado em **Actions** e no painel de monitoramento da aplicação de testes.

## Como interpretar as bolinhas

- 🟢 O service worker da PWA de testes confirmou que exibiu a notificação e a confirmação foi registrada no banco.
- 🟡 O Firebase aceitou o envio, mas não chegou confirmação do aparelho em cinco minutos. Isso, por si só, não prova falha de entrega.
- 🔴 O envio falhou explicitamente. Três dias consecutivos com falhas explícitas geram um alerta no painel.
- O script nunca desativa tokens automaticamente.
- Se o endpoint não estiver configurado, o diagnóstico não consegue confirmar o recebimento e não repetirá o envio apenas por falta de confirmação.

**Não coloque senhas, URLs de banco ou JSON da conta Firebase nos arquivos do repositório ou em mensagens.** Cadastre esses valores apenas como segredos no GitHub.
