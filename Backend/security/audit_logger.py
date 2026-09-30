"""
security/audit_logger.py
Middleware e utility per la telemetria di sicurezza on-chain:
- Cattura richieste/risposte HTTP
- Cifra metadati sensibili (IP, User-Agent) tramite AES-256-GCM
- Scrive il record immutabile sul Ledger (classe AuditLogs) tramite LispClient
"""

import time
import hashlib
from flask import request, g
from security.crypto import encrypt_aes_gcm
from fabric.lisp_client import LispClient
from config import Config

# Chiave simmetrica a 256 bit (32 byte) per AES-256-GCM
# In produzione viene caricata da config.py / variabili d'ambiente
AUDIT_AES_KEY = Config.AUDIT_AES_KEY


def generate_log_id(
    description: str,
    created_at: int,
    level: str,
    from_ip: str,
    user_agent: str,
    method: str,
    payload_size: int,
) -> str:
    """
    Calcola l'hash univoco SHA-256 dei parametri dell'evento
    per garantire l'integrità e la non-ripudiabilità del record.
    """
    raw_data = (
        f"{description}:{created_at}:{level}:{from_ip}:"
        f"{user_agent}:{method}:{payload_size}"
    )
    return hashlib.sha256(raw_data.encode("utf-8")).hexdigest()


def log_audit_event(
    description: str,
    level: str = "INFO",
    status_code: int = 200,
    anomaly_trigger: str | None = None,
    aes_key: bytes = AUDIT_AES_KEY,
) -> dict:
    """
    Costruisce il payload del log, cifra i campi sensibili e persiste
    l'evento sulla blockchain Fabric nella classe AuditLogs.
    """
    now = int(time.time())

    # Estrazione metadati da Flask request
    raw_ip = request.headers.get("X-Forwarded-For", request.remote_addr or "127.0.0.1")
    if "," in raw_ip:
        raw_ip = raw_ip.split(",")[0].strip()

    raw_ua = request.headers.get("User-Agent", "UNKNOWN_AGENT")
    method = request.method
    payload_size = request.content_length or 0

    # Cifratura simmetrica AES-256-GCM dei metadati personali
    from_ip_encrypted = encrypt_aes_gcm(raw_ip, aes_key)
    user_agent_encrypted = encrypt_aes_gcm(raw_ua, aes_key)

    # Identificativo univoco
    log_id = generate_log_id(
        description=description,
        created_at=now,
        level=level,
        from_ip=raw_ip,
        user_agent=raw_ua,
        method=method,
        payload_size=payload_size,
    )

    # Dati dell'attore autenticato (se presenti dal JWT)
    actor_matricola = None
    actor_role = None
    if hasattr(g, "current_user") and g.current_user:
        actor_matricola = g.current_user.get("matricola")
        roles = g.current_user.get("roles", [])
        actor_role = roles[0] if roles else None

    # Struttura del valore conforme alle specifiche on-chain
    log_value = {
        "id": log_id,
        "description": description,
        "created_at": now,
        "level": level,
        "status_code": status_code,
        "method": method,
        "payload_size": payload_size,
        "from_ip": from_ip_encrypted,
        "user_agent": user_agent_encrypted,
        "actor_matricola": actor_matricola,
        "actor_role": actor_role,
        "anomaly_trigger": anomaly_trigger,
    }

    # Chiave deterministica on-chain
    log_key = f"log:{now}:{log_id[:16]}"

    # Persistenza sulla Blockchain tramite il Livello 1 (Fabric Adapter)
    try:
        response = LispClient.add_kv(
            class_name="AuditLogs",
            key=log_key,
            value=log_value,
        )
        return {"log_key": log_key, "fabric_response": response}
    except Exception as e:
        # Fallback difensivo: l'errore del logger non deve interrompere il gateway
        return {"log_key": log_key, "error": str(e)}


def init_audit_middleware(app):
    """
    Registra l'hook after_request su Flask per catturare automaticamente
    il completamento di ciascuna transazione e registrarne la telemetria.
    """
    @app.after_request
    def after_request_callback(response):
        # Esclude chiamate statiche o favicon se presenti
        if request.path.startswith("/static"):
            return response

        # Rilevamento automatico di severità e codice anomalia da eventuali header o status
        level = "INFO"
        anomaly_code = getattr(g, "anomaly_trigger", None)

        if response.status_code >= 400:
            level = "ALERT"
            if response.status_code == 403 and not anomaly_code:
                anomaly_code = "U3"

        description = f"HTTP {request.method} {request.path} -> {response.status_code}"

        # Registrazione asincrona o diretta
        log_audit_event(
            description=description,
            level=level,
            status_code=response.status_code,
            anomaly_trigger=anomaly_code,
        )

        return response