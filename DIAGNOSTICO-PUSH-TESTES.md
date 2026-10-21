# Diagnóstico automático de Push — somente TESTES

O diagnóstico é isolado da produção. O workflow de envio fica no repositório da PWA de testes e faz checkout do script na branch `visual/ibne-visual-1-0` do aplicativo de testes.

## Segredos necessários

Configure em **Settings → Secrets and variables → Actions**.

### No repositório `wllmslv10/ibne-pwa-testes`
- `IBNE_TEST_DATABASE_URL`: URL do banco Neon usado exclusivamente pelo aplicativo de testes.
- `IBNE_TEST_FIREBASE_SERVICE_ACCOUNT_JSON`: JSON completo da conta de serviço do projeto Firebase `ibne-escala-midia-test`.
- `PUSH_DIAGNOSTICO_REGISTRO_IDS`: IDs numéricos, separados por vírgula, de registros ativos de `notificacoes_push` do banco de testes que foram autorizados para receber o diagnóstico.
- `CLOUDFLARE_API_TOKEN`: token Cloudflare com permissão para publicar Workers.
- `CLOUDFLARE_ACCOUNT_ID`: ID da conta Cloudflare.

### No repositório `wllmslv10/escala-midia-ibne`
Configure também `IBNE_TEST_DATABASE_URL`, `IBNE_TEST_FIREBASE_SERVICE_ACCOUNT_JSON` e `PUSH_DIAGNOSTICO_REGISTRO_IDS`, pois o workflow de envio faz checkout do script desse repositório e lê os segredos do repositório que executa o workflow (`ibne-pwa-testes`). Portanto, para evitar duplicação de configuração, o workflow de envio deve ser executado no repositório da PWA de testes; os segredos usados pelo script são lidos de lá.

## Ordem de ativação
1. Configure os segredos de banco de testes, Firebase de testes e IDs autorizados.
2. Em **Actions → Publicar confirmação Push — TESTES**, execute manualmente o workflow. Ele publica o Worker `ibne-push-ack-testes) e mostra a URL `workers.dev` no log.
3. Copie a URL HTTPS publicada e acrescente `/ack`. Cadastre esse endereço como segredo `PUSH_DIAGNOSTICO_ACK_URL` no repositório `wllmslv10/ibne-pwa-testes`.
4. Execute manualmente **Diagnóstico Push automático — TESTES** para a primeira verificação. Depois disso, os ciclos diários ficam agendados.

## Como interpretar
- 🟢 Só aparece quando o service worker envia uma confirmação que é registrada no banco de testes.
- 🟡 Firebase aceitou o envio, mas não chegou confirmação no intervalo de cinco minutos. Isso não prova que o celular falhou.
- 🔴 Falha de envio explicitamente registrada; três dias consecutivos com falhas registradas geram alerta no painel.
- O script nunca desativa tokens automaticamente.

**Importante:** o agendamento foi criado, mas não deve ser considerado operacional até configurar os segredos e publicar o Worker. Nenhuma credencial deve ser gravada nos arquivos do repositório.
