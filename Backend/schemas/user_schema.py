"""
schemas/user_schema.py
Definizione dei contratti JSON Schema e helper di namespacing per la classe Users.
"""

# 1. Schema per l'onboarding / registrazione (payload HTTP in ingresso)
USER_REGISTRATION_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "UserRegistrationPayload",
    "type": "object",
    "properties": {
        "matricola": {
            "type": "string",
            "pattern": r"^[0-9]{7}$"
        },
        "name": {
            "type": "string",
            "minLength": 2,
            "maxLength": 50
        },
        "surname": {
            "type": "string",
            "minLength": 2,
            "maxLength": 50
        },
        "email": {
            "type": "string",
            "format": "email",
            "maxLength": 100
        },
        "password": {
            "type": "string",
            "minLength": 8,
            "maxLength": 128
        },
        "role": {
            "type": "string",
            "enum": ["SEGRETERIA", "DOCENTE", "STUDENTE"]
        }
    },
    "required": ["matricola", "name", "surname", "email", "password", "role"],
    "additionalProperties": False
}

# 2. Schema per la persistenza del record On-Chain (World State di Fabric)
USER_ONCHAIN_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "UserOnChainRecord",
    "type": "object",
    "properties": {
        "matricola": {
            "type": "string",
            "pattern": r"^[0-9]{7}$"
        },
        "roles": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": ["SEGRETERIA", "DOCENTE", "STUDENTE"]
            },
            "minItems": 1
        },
        "name": {
            "type": "string",
            "minLength": 2,
            "maxLength": 50
        },
        "surname": {
            "type": "string",
            "minLength": 2,
            "maxLength": 50
        },
        "email": {
            "type": "string",
            "format": "email",
            "maxLength": 100
        },
        "password_hash": {
            "type": "string",
            "maxLength": 255
        },
        "status": {
            "type": "string",
            "enum": ["ACTIVE", "SUSPENDED"]
        },
        "created_at": {
            "type": "integer"
        },
        "updated_at": {
            "type": "integer"
        }
    },
    "required": [
        "matricola",
        "roles",
        "name",
        "surname",
        "email",
        "password_hash",
        "status",
        "created_at",
        "updated_at"
    ],
    "additionalProperties": False
}

# Aggiungere in schemas/user_schema.py

STUDENT_ENROLLMENT_SCHEMA = {
    "type": "object",
    "required": ["matricola", "name", "surname", "email", "password", "degree_id"],
    "properties": {
        "matricola": {
            "type": "string",
            "pattern": r"^[0-9]{7}$"
        },
        "name": {"type": "string", "minLength": 2, "maxLength": 50},
        "surname": {"type": "string", "minLength": 2, "maxLength": 50},
        "email": {"type": "string", "format": "email", "maxLength": 100},
        "password": {"type": "string", "minLength": 8},
        "degree_id": {"type": "string", "minLength": 2, "maxLength": 30}
    },
    "additionalProperties": False
}

USER_LOGIN_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "UserLoginPayload",
    "type": "object",
    "properties": {
        "matricola": {
            "type": "string",
            "pattern": r"^[0-9]{7}$"
        },
        "password": {
            "type": "string",
            "minLength": 8,
            "maxLength": 128
        }
    },
    "required": ["matricola", "password"],
    "additionalProperties": False
}

# 3. Helper per determinare la chiave on-chain (Namespacing)
def build_user_key(matricola: str) -> str:
    """Costruisce la chiave logica deterministica per il World State di Fabric."""
    return f"user:{matricola}"