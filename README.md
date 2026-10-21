# Escala de Mídia IBNE — PWA de Testes

Cópia isolada do PWA para validar instalação e acesso ao aplicativo de testes.

- Aplicativo de testes: https://ibne-escala-midia-teste.streamlit.app/
- PWA oficial separado: https://wllmslv10.github.io/ibne-pwa/
- Branch experimental: `push-android-nativo`
- Laboratório: `https://wllmslv10.github.io/ibne-pwa-testes/push-lab.html` (ambiente experimental).
- O laboratório aceita somente o Firebase de testes `ibne-escala-midia-test` (Sender ID `607844080420`).
- A configuração Web pública e a chave VAPID são informadas no navegador e guardadas no IndexedDB local. Não são gravadas no repositório.
- Não cole chaves de conta de serviço, arquivos JSON privados ou credenciais administrativas no laboratório.
- A notificação local confirma apenas a apresentação no Android; o envio remoto depende de token válido e de um emissor autorizado do Firebase.

## Publicação e validação

O laboratório será servido pelo GitHub Pages do repositório de testes, em HTTPS. Para não substituir o Service Worker principal da PWA, o worker de Firebase usa o escopo isolado `./push-scope/`. A implementação não altera a PWA oficial nem o Firebase de produção. O primeiro teste solicita permissão e obtém o token do dispositivo. O envio remoto será validado separadamente, sem colocar credenciais administrativas no navegador.
