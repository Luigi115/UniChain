"""
security package
Policy Enforcement Point, Crittografia e Audit Logger per UniChain.
"""

from security.crypto import (
    hash_password,
    verify_password,
    encrypt_aes_gcm,
    decrypt_aes_gcm,
)

from security.rbac import (
    create_access_token,
    decode_access_token,
    require_role,
)

from security.audit_logger import (
    log_audit_event,
    init_audit_middleware,
)

__all__ = [
    "hash_password",
    "verify_password",
    "encrypt_aes_gcm",
    "decrypt_aes_gcm",
    "create_access_token",
    "decode_access_token",
    "require_role",
    "log_audit_event",
    "init_audit_middleware",
]