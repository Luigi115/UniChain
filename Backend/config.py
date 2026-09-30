import os

class Config:
    """Configurazioni centralizzate caricate tramite variabili d'ambiente."""

    # Chiave simmetrica a 256 bit (32 byte) per AES-256-GCM
    AUDIT_AES_KEY = os.environ.get(
        "AUDIT_AES_KEY", 
        "12345678901234567890123456789012"
    ).encode("utf-8")

    # Chiave segreta per la firma dei token JWT
    JWT_SECRET = os.environ.get(
        "JWT_SECRET", 
        "unichain_secret_jwt_key_2026_super_secure"
    )
    
# Configurazioni di rete per il Client Lisp (Restricted Zone)
    LISP_HOST = os.environ.get("LISP_HOST", "160.80.216.209")
    LISP_PORT = int(os.environ.get("LISP_PORT", 9999))