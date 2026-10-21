/* Service Worker exclusivo do laboratório de Push da PWA de testes.
   A configuração pública do Firebase é lida do IndexedDB, nunca embutida no repositório. */
importScripts('https://www.gstatic.com/firebasejs/10.14.1/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/10.14.1/firebase-messaging-compat.js');

const DB_NAME = 'ibne-push-lab';
const STORE_NAME = 'config';
function readFirebaseConfig() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, 1);
    request.onupgradeneeded = () => request.result.createObjectStore(STORE_NAME);
    request.onerror = () => reject(request.error);
    request.onsuccess = () => {
      const db = request.result;
      const tx = db.transaction(STORE_NAME, 'readonly');
      const get = tx.objectStore(STORE_NAME).get('firebase');
      get.onsuccess = () => { resolve(get.result || null); db.close(); };
      get.onerror = () => { reject(get.error); db.close(); };
    };
  });
}
self.addEventListener('push', () => {});
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const target = new URL('./', self.location.href).href;
  event.waitUntil(self.clients.matchAll({type:'window', includeUncontrolled:true}).then((clients) => {
    for (const client of clients) {
      if ('focus' in client) return client.focus();
    }
    return self.clients.openWindow(target);
  }));
});
self.addEventListener('message', (event) => {
  if (event.data?.type === 'IBNE_PUSH_CONFIG_UPDATED') {
    event.waitUntil?.(Promise.resolve());
  }
});
readFirebaseConfig().then((config) => {
  if (!config || !config.apiKey || !config.projectId || !config.messagingSenderId || !config.appId) return;
  if (!firebase.apps.length) firebase.initializeApp(config);
  const messaging = firebase.messaging();
  messaging.onBackgroundMessage((payload) => {
    const notification = payload.notification || {};
    const title = notification.title || payload.data?.title || 'Escala de Mídia IBNE — Testes';
    const options = {
      body: notification.body || payload.data?.body || 'Você recebeu uma nova mensagem.',
      icon: './icons/icone-ibne.png',
      badge: './icons/icone-ibne.png',
      data: {url: payload.data?.url || './'}
    };
    return self.registration.showNotification(title, options);
  });
}).catch((error) => console.error('IBNE Push: falha ao inicializar Firebase', error));
