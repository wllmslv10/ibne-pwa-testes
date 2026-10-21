import { neon } from '@neondatabase/serverless';

const allowedOrigin = 'https://wllmslv10.github.io';
export default {
  async fetch(request, env) {
    const origin = request.headers.get('Origin') || '';
    const headers = {
      'Access-Control-Allow-Origin': origin === allowedOrigin ? allowedOrigin : 'null',
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
      'Vary': 'Origin'
    };
    if (request.method === 'OPTIONS') return new Response(null, { status: 204, headers });
    if (request.method !== 'POST' || origin !== allowedOrigin) {
      return new Response('Not found', { status: 404, headers });
    }
    if (!env.DATABASE_URL) return new Response('Service not configured', { status: 503, headers });
    let body;
    try { body = await request.json(); } catch { return new Response('Invalid JSON', { status: 400, headers }); }
    const attemptId = String(body?.attempt_id || '');
    if (!/^[0-9a-f-]{36}$/i.test(attemptId)) return new Response('Invalid attempt id', { status: 400, headers });
    try {
      const sql = neon(env.DATABASE_URL);
      await sql`INSERT INTO diagnostico_push_ack (attempt_id, recebido_em)
                VALUES (${attemptId}, NOW())
                ON CONFLICT (attempt_id) DO NOTHING`;
      return new Response('ACK recorded', { status: 200, headers });
    } catch (error) {
      return new Response('Storage unavailable', { status: 503, headers });
    }
  }
};
