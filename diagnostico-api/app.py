import os, time, uuid, hashlib
from flask import Flask, jsonify, request
import firebase_admin
from firebase_admin import messaging
import psycopg2
from psycopg2.extras import RealDictCursor

PROJECT = "ibne-escala-midia-test"
app = Flask(__name__)

def connect():
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        raise RuntimeError("DATABASE_URL ausente no Secret Manager")
    return psycopg2.connect(url, connect_timeout=15)

def fb():
    try:
        firebase_admin.get_app()
    except ValueError:
        firebase_admin.initialize_app(options={"projectId": PROJECT})
    instance = firebase_admin.get_app()
    if instance.project_id != PROJECT:
        raise RuntimeError("Bloqueado: projeto Firebase não é o de testes")
    return instance

def ensure(conn):
    with conn.cursor() as cur:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS diagnostico_push_ack (
          attempt_id TEXT PRIMARY KEY, recebido_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS diagnostico_push_agendado (
          id BIGSERIAL PRIMARY KEY, notificacao_push_id BIGINT, funcionario_id BIGINT,
          device_id_hash TEXT, agendado_para TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          tentado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(), resultado TEXT NOT NULL,
          firebase_message_id TEXT, codigo_erro TEXT, detalhe TEXT,
          confirmacao_recebida_em TIMESTAMPTZ, attempt_id TEXT,
          criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        ALTER TABLE diagnostico_push_agendado ADD COLUMN IF NOT EXISTS attempt_id TEXT;
        """)
    conn.commit()

def record(conn, d, result, aid="", mid=None, code=None, detail=""):
    dh = hashlib.sha256(str(d.get("device_id") or "").encode()).hexdigest()[:16]
    with conn.cursor() as cur:
        cur.execute("""INSERT INTO diagnostico_push_agendado
        (notificacao_push_id,funcionario_id,device_id_hash,resultado,firebase_message_id,codigo_erro,detalhe,attempt_id)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
        (d.get("id"),d.get("funcionario_id"),dh,result,mid,code,detail[:500],aid or None))
    conn.commit()

@app.get("/healthz")
def health():
    return jsonify(ok=True, ambiente="testes")

@app.post("/diagnostico")
def run():
    if os.environ.get("IBNE_PUSH_DIAGNOSTICO_AMBIENTE") != "testes":
        return jsonify(erro="Ambiente bloqueado"), 403
    marker = os.environ.get("DIAGNOSTICO_TRIGGER_MARKER", "")
    if not marker or request.headers.get("X-IBNE-Diagnostico") != marker:
        return jsonify(erro="Origem não autorizada"), 403
    ids_raw = os.environ.get("PUSH_DIAGNOSTICO_REGISTRO_IDS", "")
    try:
        ids = sorted({int(v.strip()) for v in ids_raw.split(",") if v.strip()})
    except ValueError:
        return jsonify(erro="IDs inválidos"), 500
    if not ids:
        return jsonify(erro="Nenhum dispositivo de teste autorizado"), 500
    firebase = fb()
    results=[]
    with connect() as conn:
        ensure(conn)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""SELECT id,funcionario_id,device_id,token FROM notificacoes_push
              WHERE id=ANY(%s) AND ativo=TRUE AND token IS NOT NULL AND BTRIM(token)<>'' ORDER BY id""",(ids,))
            devices=cur.fetchall()
        present={int(d["id"]) for d in devices}
        for missing in sorted(set(ids)-present):
            record(conn,{"id":missing},"ignorado",code="REGISTRO_NAO_ATIVO",detail="ID não ativo ou sem token; nenhum envio.")
        for d in devices:
            success=False
            for n in range(1,4):
                aid=str(uuid.uuid4())
                try:
                    msg=messaging.Message(
                      notification=messaging.Notification(title="🔎 Teste de conectividade Push — IBNE",
                        body=f"Verificação automática do ambiente de testes (tentativa {n}/3). Nenhuma ação necessária."),
                      data={"tipo":"ibne_push_diagnostico","ambiente":"testes","confirmacao":"pendente",
                        "tentativa":str(n),"attempt_id":aid,"ack_url":os.environ.get("PUSH_DIAGNOSTICO_ACK_URL","")},
                      token=d["token"])
                    mid=messaging.send(msg,app=firebase)
                    record(conn,d,"firebase_aceitou_confirmacao_pendente",aid,mid,detail=f"Firebase aceitou tentativa {n}/3; aguardando ACK.")
                    ack_url=os.environ.get("PUSH_DIAGNOSTICO_ACK_URL","")
                    if not ack_url.startswith("https://"):
                        with conn.cursor() as cur:
                            cur.execute("UPDATE diagnostico_push_agendado SET resultado='firebase_aceitou_sem_confirmacao',detalhe='Endpoint ACK HTTPS ausente.' WHERE attempt_id=%s",(aid,))
                        conn.commit(); break
                    for _ in range(30):
                        time.sleep(10)
                        with conn.cursor() as cur:
                            cur.execute("SELECT recebido_em FROM diagnostico_push_ack WHERE attempt_id=%s",(aid,))
                            ack=cur.fetchone()
                        if ack:
                            with conn.cursor() as cur:
                                cur.execute("""UPDATE diagnostico_push_agendado SET resultado='confirmado_no_dispositivo',
                                confirmacao_recebida_em=%s,detalhe='Service worker de testes confirmou a exibição.'
                                WHERE attempt_id=%s""",(ack[0],aid))
                            conn.commit(); success=True; break
                    if success: break
                    with conn.cursor() as cur:
                        cur.execute("UPDATE diagnostico_push_agendado SET resultado='firebase_aceitou_sem_confirmacao',detalhe=%s WHERE attempt_id=%s",
                          (f"Sem ACK em cinco minutos (tentativa {n}/3).",aid))
                    conn.commit()
                except messaging.UnregisteredError as e:
                    record(conn,d,"token_invalido_confirmado",aid,code="UNREGISTERED",detail=f"{e}; token preservado.")
                    break
                except Exception as e:
                    record(conn,d,"falha_envio_sem_desativar_token",aid,code=type(e).__name__,detail=f"{n}/3: {e}; token preservado.")
                    if n<3: time.sleep(300)
            results.append({"registro":int(d["id"]),"resultado":"confirmado" if success else "sem_confirmacao_ou_falha"})
    return jsonify(ok=True,ambiente="testes",quantidade=len(devices),resultados=results)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT","8080")))
