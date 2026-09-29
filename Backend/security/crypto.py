"""
security/crypto.py
Gestione delle operazioni crittografiche del Security Gateway:
- Hashing e verifica sicura delle password tramite Bcrypt
- Cifratura e decifratura simmetrica autenticata AES-256-GCM per metadati sensibili (IP, User-Agent)
"""

import os
import base64
import bcrypt
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# ==============================================================================
# 1. HASHING PASSWORD (BCRYPT)
# ==============================================================================

def hash_password(plain_password: str) -> str:
    """
    Genera un hash sicuro bcrypt con salt a 12 round per la password in chiaro.
    Restituisce una stringa UTF-8 pronta per il campo 'password_hash' on-chain.
    """
    salt = bcrypt.gensalt(rounds=12)
    pwd_bytes = plain_password.encode("utf-8")
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica computazionalmente se una password in chiaro corrisponde al digest salvato.
    Restituisce True se valida, False altrimenti.
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8")
        )
    except Exception:
        return False


# ==============================================================================
# 2. CIFRATURA SIMMETRICA METADATI DI AUDIT (AES-256-GCM)
# ==============================================================================

def encrypt_aes_gcm(plaintext: str, key: bytes) -> str:
    """
    Cifra una stringa arbitraria in AES-256-GCM.
    Richiede una chiave simmetrica a 256 bit (32 byte).
    Restituisce una stringa codificata in Base64 contenente: nonce (12B) + ciphertext + tag (16B).
    """
    if len(key) != 32:
        raise ValueError("La chiave AES-256 deve essere esattamente di 32 byte.")

    aesgcm = AESGCM(key)
    nonce = os.urandom(12)  # Nonce standard a 96 bit (12 byte)
    ciphertext_and_tag = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    
    # Concatena nonce + ciphertext/tag e serializza in Base64
    payload = nonce + ciphertext_and_tag
    return base64.b64encode(payload).decode("utf-8")


def decrypt_aes_gcm(encrypted_b64: str, key: bytes) -> str:
    """
    Decifra la stringa Base64 verificando l'integrità del tag di autenticazione GCM.
    Restituisce la stringa in chiaro originale.
    """
    if len(key) != 32:
        raise ValueError("La chiave AES-256 deve essere esattamente di 32 byte.")

    raw_data = base64.b64decode(encrypted_b64.encode("utf-8"))
    nonce = raw_data[:12]
    ciphertext_and_tag = raw_data[12:]
    
    aesgcm = AESGCM(key)
    plaintext_bytes = aesgcm.decrypt(nonce, ciphertext_and_tag, None)
    return plaintext_bytes.decode("utf-8")