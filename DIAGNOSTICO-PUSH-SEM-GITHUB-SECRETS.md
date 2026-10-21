# Diagnóstico Push — somente TESTES, sem GitHub Secrets

A automação usa GitHub Actions com OIDC para chamar um serviço privado no Google Cloud Run. Não há chave de serviço Firebase no repositório e nenhuma credencial precisa ser armazenada em GitHub Secrets. A PWA de produção e o Firebase de produção não participam.

## O que já está no repositório

- Workflow agendado `.github/workflows/diagnostico-push-testes.yml`: chama o Cloud Run usando identidade federada OIDC.
- Serviço `diagnostico-api/`: usa identidade de runtime do Cloud Run para Firebase Admin e lê `DATABASE_URL` do ambiente privado do Cloud Run.
- Worker ACK do PWA de testes, já existente.

## Configuração única necessária no Google Cloud

A infraestrutura do Google Cloud não pode ser criada só por um commit no GitHub: alguém com acesso administrativo ao projeto precisa executar a configuração abaixo no projeto de TESTES.

1. No projeto Google Cloud associado ao Firebase `ibne-escala-midia-test` (ID esperado `ibne-escala-midia-test`), habilitar Cloud Run, Cloud Build, Artifact Registry, IAM Credentials, Security Token Service, Secret Manager e Firebase Cloud Messaging.
2. Criar um Secret Manager secret `ibne-test-database-url` com a URL do banco Neon exclusivamente de testes.
3. Criar uma conta de serviço de runtime para o Cloud Run. Dar a ela acesso de leitura apenas ao secret do banco e a permissão necessária para enviar Firebase Cloud Messaging no projeto `ibne-escala-midia-test`. Não criar nem carregar JSON de chave privada.
4. Criar o serviço Cloud Run `ibne-push-diagnostico-testes` a partir da pasta `diagnostico-api`, com autenticação IAM obrigatória, timeout de até 30 minutos e região escolhida pelo administrador. Definir variáveis privadas `IBNE_PUSH_DIAGNOSTICO_AMBIENTE=testes`, `PUSH_DIAGNOSTICO_REGISTRO_IDS` (IDs autorizados dos dispositivos de teste) e `PUSH_DIAGNOSTICO_ACK_URL` (URL HTTPS do Worker ACK publicado). Montar `DATABASE_URL` a partir do Secret Manager.
5. Criar Workload Identity Pool e Provider OIDC para `https://token.actions.githubusercontent.com`. Restringir a condição ao repositório `wllmslv10/ibne-pwa-testes`, branch `refs/heads/main` e workflow autorizado. Permitir que essa identidade impersonifique somente a conta de serviço que tem permissão de invocar o Cloud Run.
6. Dar `roles/run.invoker` à conta federada apenas no serviço Cloud Run.
7. No repositório `wllmslv10/ibne-pwa-testes`, em Settings → Secrets and variables → Actions → Variables, criar variáveis (não Secrets): `GCP_WORKLOAD_IDENTITY_PROVIDER` (resource name completo do provider), `GCP_DIAGNOSTICO_SERVICE_ACCOUNT` (e-mail da conta de serviço autorizada a invocar Cloud Run), `CLOUD_RUN_DIAGNOSTICO_URL` (URL base do serviço). O workflow não lê GitHub Secrets.
8. Testar primeiro `/healthz` no serviço Cloud Run com identidade autorizada; depois executar manualmente o workflow. Confirmar chegada no aparelho e registro ACK no banco de testes.

## Limitações importantes

- O código no GitHub não cria automaticamente recursos do Google Cloud nem concede IAM; a configuração administrativa única acima é necessária.
- O workflow falhará com mensagem clara até que as três variáveis GitHub e os recursos OIDC/Cloud Run estejam configurados.
- O endpoint ACK deve estar publicado e gravando no mesmo banco de testes. A URL precisa ser a real do Worker, terminando em `/ack`.
- A bolinha verde só deve ser exibida quando houver registro ACK. Firebase aceitou sem ACK é amarelo; erro explícito é vermelho. Token algum é desativado automaticamente.
- A conta de runtime Firebase deve ser validada no projeto real antes de executar. Se IAM do projeto não permitir o envio, o diagnóstico registrará falha explícita; não usar credenciais de produção como atalho.
