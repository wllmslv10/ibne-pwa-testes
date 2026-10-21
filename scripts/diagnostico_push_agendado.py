#!/usr/bin/env python3
"""Diagnóstico agendado de Push apenas no Firebase/banco de testes."""
import hashlib
import json
import os
import sys
import uuid

import psycopg2
from psycopg2.extras import RealDictCursor
import firebase_admin
from firebase_admin import credentials, messaging

PROJECT_TESTE = "ibne-escala-midia-test"


def exigir_configuracao():
    if os.getenv("IBNE_PUSH_DIAGNOSTICO_AMBIENTE") != "testes":
        raise RuntimeError("Execução bloqueada: ambiente não marcado como testes.")
    db_url = os.getenv("DATABASE_URL", "").strip()
    cred_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON", "").strip()
    ids_raw = os.getenv("PUSH_DIAGNOSTICO_REGISTRO_IDS", "").strip()
    ack_url = os.getenv("PUSH_DIAGNOSTICO_ACK_URL", "").strip().rstrip("/")
    if not all((db_url, cred_json, ids_raw, ack_url)):
        raise RuntimeError("Faltam segredos obrigatórios. Nenhum Push enviado.")
    if not ack_url.startswith("https://") or "/ack" not in ack_url:
        raise RuntimeError("PUSH_DIAGNOSTICO_ACK_URL deve ser endpoint HTTPS terminado em /ack.")
    try:
        ids = sorted({int(x.strip()) for x in ids_raw.split(",") if x.strip()})
    except ValueError as exc:
        raise RuntimeError("Os IDs autorizados devem ser numéricos.") from exc
    if not ids:
        raise RuntimeError("Nenhum dispositivo explicitamente autorizado.")
    service_account = json.loads(cred_json)
    if service_account.get("project_id") != PROJECT_TESTE:
        raise RuntimeError("Conta de serviço não pertence ao Firebase de testes esperado.")
    return db_url, service_account, ids, ack_url


def preparar_tabela(conn):
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS diagnostico_push_agendado (
                id BIGSERIAL PRIMARY KEY,
                notificacao_push_id BIGINT,
                funcionario_id BIGINT,
                device_id_hash TEXT,
                agendado_para TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                tentado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                resultado TEXT NOT NULL,
                firebase_message_id TEXT,
                codigo_erro TEXT,
                detalhe TEXT,
                confirmacao_recebida_em TIMESTAMPTZ,
                ack_nonce TEXT,
                criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            ALTER TABLE diagnostico_push_agendado
                ADD COLUMN IF NOT EXISTS ack_nonce TEXT;
            CREATE INDEX IF NOT EXISTS idx_diag_push_agendado_criado
                ON diagnostico_push_agendado (criado_em DESC);
        """)
    conn.commit()


def registrar(conn, row_id, funcionario_id, device_id, resultado, *,
              message_id=None, codigo_erro=None, detalhe=None,
              ack_nonce=None, diagnostico_id=None):
    device_hash = hashlib.sha256(str(device_id or "").encode()).hexdigest()[:16]
    if diagnostico_id is None:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO diagnostico_push_agendado
                  (notificacao_push_id, funcionario_id, device_id_hash, resultado,
                   codigo_erro, detalhe)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (row_id, funcionario_id, device_hash, resultado, codigo_erro, (detalhe or "")[:500]))
        conn.commit()
        return
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE diagnostico_push_agendado
               SET resultado=CASE
                     WHEN resultado='confirmado_no_aparelho'
                          AND %s='firebase_aceitou_confirmacao_pendente'
                     THEN resultado ELSE %s END,
                   firebase_message_id=%s, codigo_erro=%s, detalhe=%s
             WHERE id=%s AND ack_nonce=%s
        """, (resultado, resultado, message_id, codigo_erro, (detalhe or "")[:500], diagnostico_id, ack_nonce))
    conn.commit()


def main():
    db_url, service_account, ids, ack_url = exigir_configuracao()
    try:
        firebase_admin.get_app()
    except ValueError:
        firebase_admin.initialize_app(credentials.Certificate(service_account))
    app = firebase_admin.get_app()
    if app.project_id != PROJECT_TESTE:
        raise RuntimeError("Bloqueado: Firebase inicializado com projeto diferente do projeto de testes.")

    with psycopg2.connect(db_url, connect_timeout=15) as conn:
        preparar_tabela(conn)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id, funcionario_id, device_id, token
                  FROM notificacoes_push
                 WHERE id = ANY(%s) AND ativo = TRUE
                   AND token IS NOT NULL AND BTRIM(token) <> ''
                 ORDER BY id
            """, (ids,))
            devices = cur.fetchall()

        encontrados = {int(d["id"]) for d in devices}
        for missing_id in sorted(set(ids) - encontrados):
            registrar(conn, missing_id, None, "", "ignorado",
                      codigo_erro="REGISTRO_NAO_ATIVO",
                      detalhe="Registro não ativo/disponível no banco de testes; envio não realizado.")

        if not devices:
            print("Nenhum registro autorizado está ativo com token. Nenhum Push enviado.")
            return 0

        for device in devices:
            nonce = str(uuid.uuid4())
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO diagnostico_push_agendado
                      (notificacao_push_id, funcionario_id, device_id_hash, resultado, ack_nonce)
                    VALUES (%s, %s, %s, 'enviado_aguardando_confirmacao', %s)
                    RETURNING id
                """, (device["id"], device["funcionario_id"],
                      hashlib.sha256(str(device["device_id"] or "").encode()).hexdigest()[:16], nonce))
                diag_id = cur.fetchone()[0]
            conn.commit()
            try:
                message = messaging.Message(
                    notification=messaging.Notification(
                        title="🔎 Teste de conectividade Push — IBNE",
                        body="Verificação automática do ambiente de testes. Nenhuma ação é necessária."
                    ),
                    data={
                        "tipo": "ibne_push_diagnostico",
                        "ambiente": "testes",
                        "diagnostico_id": str(diag_id),
                        "nonce": nonce,
                        "ack_url": ack_url
                    },
                    token=device["token"],
                )
                message_id = messaging.send(message, app=app)
                registrar(conn, device["id"], device["funcionario_id"], device["device_id"],
                          "firebase_aceitou_confirmacao_pendente", message_id=message_id,
                          detalhe="Firebase aceitou o envio; aguardando confirmação do service worker.",
                          ack_nonce=nonce, diagnostico_id=diag_id)
                print(f"Registro {device['id']}: aceito pelo Firebase; confirmação pendente.")
            except messaging.UnregisteredError as exc:
                registrar(conn, device["id"], device["funcionario_id"], device["device_id"],
                          "token_invalido_confirmado", codigo_erro="UNREGISTERED",
                          detalhe=str(exc), ack_nonce=nonce, diagnostico_id=diag_id)
                print(f"Registro {device['id']}: Firebase informou token não registrado.")
            except Exception as exc:
                code = getattr(exc, "code", None) or exc.__class__.__name__
                registrar(conn, device["id"], device["funcionario_id"], device["device_id"],
                          "falha_envio_sem_desativar_token", codigo_erro=str(code),
                          detalhe=str(exc), ack_nonce=nonce, diagnostico_id=diag_id)
                print(f"Registro {device['id']}: falha {code}; token mantido ativo.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"DIAGNÓSTICO BLOQUEADO/ERRO: {exc}", file=sys.stderr)
        sys.exit(1)
