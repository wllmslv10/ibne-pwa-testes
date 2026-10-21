#!/usr/bin/env python3
"""Envia Pushs diagnósticos agendados apenas a registros explicitamente autorizados.

Variáveis obrigatórias:
  DATABASE_URL: banco EXCLUSIVO de testes
  FIREBASE_SERVICE_ACCOUNT_JSON: JSON da conta de serviço do Firebase de testes
  PUSH_DIAGNOSTICO_REGISTRO_IDS: IDs numéricos de notificacoes_push separados por vírgula
  IBNE_PUSH_DIAGNOSTICO_AMBIENTE=testes
"""
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

import psycopg2
from psycopg2.extras import RealDictCursor
import firebase_admin
from firebase_admin import credentials, messaging

PROJECT_TESTE = "ibne-escala-midia-test"


def exigir_configuracao():
    if os.getenv("IBNE_PUSH_DIAGNOSTICO_AMBIENTE") != "testes":
        raise RuntimeError("Execução bloqueada: IBNE_PUSH_DIAGNOSTICO_AMBIENTE deve ser 'testes'.")
    db_url = os.getenv("DATABASE_URL", "").strip()
    cred_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON", "").strip()
    ids_raw = os.getenv("PUSH_DIAGNOSTICO_REGISTRO_IDS", "").strip()
    if not db_url or not cred_json or not ids_raw:
        raise RuntimeError(
            "Execução segura: configure DATABASE_URL, FIREBASE_SERVICE_ACCOUNT_JSON e "
            "PUSH_DIAGNOSTICO_REGISTRO_IDS (IDs de notificacoes_push autorizados). Nenhum Push enviado."
        )
    try:
        ids = sorted({int(x.strip()) for x in ids_raw.split(",") if x.strip()})
    except ValueError as exc:
        raise RuntimeError("PUSH_DIAGNOSTICO_REGISTRO_IDS deve conter apenas IDs numéricos.") from exc
    if not ids:
        raise RuntimeError("Nenhum ID de dispositivo autorizado; nenhum Push enviado.")
    service_account = json.loads(cred_json)
    project_id = service_account.get("project_id")
    if project_id != PROJECT_TESTE:
        raise RuntimeError(
            f"Execução bloqueada: a conta Firebase é do projeto {project_id!r}, "
            f"mas o projeto de testes esperado é {PROJECT_TESTE!r}."
        )
    return db_url, service_account, ids


def registrar_tabela(conn):
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
                criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_diag_push_agendado_criado
                ON diagnostico_push_agendado (criado_em DESC);
        """)
    conn.commit()


def gravar_resultado(conn, *, row_id, funcionario_id, device_id, resultado,
                     message_id=None, codigo_erro=None, detalhe=None):
    device_hash = hashlib.sha256(str(device_id or "").encode("utf-8")).hexdigest()[:16]
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO diagnostico_push_agendado
                (notificacao_push_id, funcionario_id, device_id_hash, agendado_para,
                 tentado_em, resultado, firebase_message_id, codigo_erro, detalhe)
            VALUES (%s, %s, %s, NOW(), NOW(), %s, %s, %s, %s)
        """, (row_id, funcionario_id, device_hash, resultado, message_id,
              codigo_erro, (detalhe or "")[:500]))
    conn.commit()


def main():
    db_url, service_account, ids = exigir_configuracao()
    try:
        firebase_admin.get_app()
    except ValueError:
        firebase_admin.initialize_app(credentials.Certificate(service_account))
    app = firebase_admin.get_app()
    if app.project_id != PROJECT_TESTE:
        raise RuntimeError("Execução bloqueada: Firebase Admin inicializado com projeto diferente do projeto de testes.")

    with psycopg2.connect(db_url, connect_timeout=15) as conn:
        registrar_tabela(conn)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id, funcionario_id, device_id, token
                FROM notificacoes_push
                WHERE id = ANY(%s)
                  AND ativo = TRUE
                  AND token IS NOT NULL
                  AND BTRIM(token) <> ''
                ORDER BY id
            """, (ids,))
            devices = cur.fetchall()

        encontrados = {int(d["id"]) for d in devices}
        faltantes = sorted(set(ids) - encontrados)
        for missing_id in faltantes:
            gravar_resultado(
                conn, row_id=missing_id, funcionario_id=None, device_id="",
                resultado="ignorado", codigo_erro="REGISTRO_NAO_ATIVO",
                detalhe="ID não encontrado como dispositivo ativo com token no banco de testes; nenhum envio realizado."
            )

        if not devices:
            print("Nenhum dos IDs autorizados está ativo com token no banco de testes. Nenhum Push enviado.")
            return 0

        for device in devices:
            try:
                message = messaging.Message(
                    notification=messaging.Notification(
                        title="🔎 Teste de conectividade Push — IBNE",
                        body="Verificação automática do ambiente de testes. Nenhuma ação é necessária."
                    ),
                    data={
                        "tipo": "ibne_push_diagnostico",
                        "ambiente": "testes",
                        "confirmacao": "pendente"
                    },
                    token=device["token"],
                )
                message_id = messaging.send(message, app=app)
                gravar_resultado(
                    conn, row_id=device["id"], funcionario_id=device["funcionario_id"],
                    device_id=device["device_id"], resultado="firebase_aceitou_confirmacao_pendente",
                    message_id=message_id,
                    detalhe="Firebase aceitou o envio; recebimento no celular ainda não foi confirmado."
                )
                print(f"Registro {device['id']}: Firebase aceitou; confirmação do aparelho pendente.")
            except messaging.UnregisteredError as exc:
                gravar_resultado(
                    conn, row_id=device["id"], funcionario_id=device["funcionario_id"],
                    device_id=device["device_id"], resultado="token_invalido_confirmado",
                    codigo_erro="UNREGISTERED", detalhe=str(exc)
                )
                print(f"Registro {device['id']}: Firebase informou token não registrado.")
            except Exception as exc:
                code = getattr(exc, "code", None) or exc.__class__.__name__
                gravar_resultado(
                    conn, row_id=device["id"], funcionario_id=device["funcionario_id"],
                    device_id=device["device_id"], resultado="falha_envio_sem_desativar_token",
                    codigo_erro=str(code), detalhe=str(exc)
                )
                print(f"Registro {device['id']}: falha {code}; token mantido ativo.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"DIAGNÓSTICO BLOQUEADO/ERRO: {exc}", file=sys.stderr)
        sys.exit(1)
