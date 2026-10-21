import { neon } from "@neondatabase/serverless";

const json = (body, status = 200) => new Response(JSON.stringify(body), {
  status,
  headers: {
    "content-type": "application/json; charset=utf-8",
    "access-control-allow-origin": "https://wllmslv10.github.io",
    "access-control-allow-methods": "POST, OPTIONS",
    "access-control-allow-headers": "content-type",
    "cache-control": "no-store"
  }
});

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (request.method === "OPTIONS") return new Response(null, {
      status: 204,
      headers: {
        "access-control-allow-origin": "https://wllmslv10.github.io",
        "access-control-allow-methods": "POST, OPTIONS",
        "access-control-allow-headers": "content-type",
        "access-control-max-age": "600"
      }
    });
    if (url.pathname !== "/ack" || request.method !== "POST") return json({ ok: false }, 404);
    if (request.headers.get("origin") !== "https://wllmslv10.github.io") return json({ ok: false }, 403);
    if (!env.DATABASE_URL) return json({ ok: false, error: "not_configured" }, 503);

    let body;
    try { body = await request.json(); } catch { return json({ ok: false }, 400); }
    const id = Number(body?.diagnostico_id);
    const nonce = String(body?.nonce || "");
    if (!Number.isSafeInteger(id) || id < 1 || !/^[a-f0-9-]{36}$/i.test(nonce)) {
      return json({ ok: false }, 400);
    }

    try {
      const sql = neon(env.DATABASE_URL);
      const rows = await sql`
        UPDATE diagnostico_push_agendado
           SET confirmacao_recebida_em = NOW(),
               resultado = 'confirmado_no_aparelho'
         WHERE id = ${id}
           AND ack_nonce = ${nonce}
           AND resultado IN ('firebase_aceitou_confirmacao_pendente', 'enviado_aguardando_confirmacao')
        RETURNING id
      `;
      if (!rows.length) return json({ ok: false, error: "not_found_or_already_confirmed" }, 404);
      return json({ ok: true });
    } catch {
      return json({ ok: false, error: "database_error" }, 500);
    }
  }
};
