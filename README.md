# Escala de Mídia IBNE — PWA de Testes

Cópia isolada do PWA para validar instalação e acesso ao aplicativo de testes.

- Aplicativo de testes: https://ibne-escala-midia-teste.streamlit.app/
- PWA oficial separado: https://wllmslv10.github.io/ibne-pwa/
- Branch experimental: `push-android-nativo`
- Laboratório: `push-lab.html` (disponível quando esta branch for publicada no GitHub Pages).
- O laboratório aceita somente o Firebase de testes `ibne-escala-midia-test` (Sender ID `607844080420`).
- A configuração Web pública e a chave VAPID são informadas no navegador e guardadas no IndexedDB local. Não são gravadas no repositório.
- Não cole chaves de conta de serviço, arquivos JSON privados ou credenciais administrativas no laboratório.
- A notificação local confirma apenas a apresentação no Android; o envio remoto depende de token válido e de um emissor autorizado do Firebase.

## Publicação e validação

Esta implementação está isolada na branch experimental. Ela não altera a branch `main`, o aplicativo Streamlit de testes, o Firebase de produção nem a PWA oficial. Antes do teste no celular, a branch precisa ser publicada em um endereço HTTPS. O primeiro teste do laboratório solicita permissão, registra o Service Worker e obtém o token do dispositivo. O envio remoto será validado separadamente, sem colocar credenciais administrativas no navegador.
