"""
schemas/exam_schema.py
Definizione dei contratti JSON Schema e helper di namespacing 
per le classi Appelli e Prenotazioni.
"""

# ==============================================================================
# 1. SCHEMI CLASSE APPELLI
# ==============================================================================

# Payload HTTP inviato dal Docente per creare una sessione d'esame
EXAM_SESSION_CREATE_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "ExamSessionCreatePayload",
    "type": "object",
    "properties": {
        "course_id": {
            "type": "string",
            "minLength": 2,
            "maxLength": 20
        },
        "academic_year": {
            "type": "string",
            "pattern": r"^[0-9]{4}/[0-9]{4}$"  # es. 2025/2026
        },
        "session_period": {
            "type": "string",
            "enum": ["INVERNALE", "ESTIVA", "AUTUNNALE", "STRAORDINARIA"]
        },
        "exam_date": {
            "type": "integer",
            "minimum": 0
        },
        "reg_start_date": {
            "type": "integer",
            "minimum": 0
        },
        "reg_end_date": {
            "type": "integer",
            "minimum": 0
        },
        "session_type": {
            "type": "string",
            "enum": ["ORDINARIO", "STRAORDINARIO"]
        },
        "max_seats": {
            "type": ["integer", "null"],
            "minimum": 1
        }
    },
    "required": [
        "course_id",
        "academic_year",
        "session_period",
        "exam_date",
        "reg_start_date",
        "reg_end_date",
        "session_type"
    ],
    "additionalProperties": False
}

# Record persistito on-chain nel World State (classe Appelli)
EXAM_SESSION_ONCHAIN_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "ExamSessionOnChainRecord",
    "type": "object",
    "properties": {
        "session_id": {
            "type": "string",
            "minLength": 1,
            "maxLength": 64
        },
        "course_id": {
            "type": "string",
            "minLength": 2,
            "maxLength": 20
        },
        "docente_matricola": {
            "type": "string",
            "pattern": r"^[0-9]{7}$"
        },
        "academic_year": {
            "type": "string",
            "pattern": r"^[0-9]{4}/[0-9]{4}$"
        },
        "session_period": {
            "type": "string",
            "enum": ["INVERNALE", "ESTIVA", "AUTUNNALE", "STRAORDINARIA"]
        },
        "exam_date": {
            "type": "integer",
            "minimum": 0
        },
        "reg_start_date": {
            "type": "integer",
            "minimum": 0
        },
        "reg_end_date": {
            "type": "integer",
            "minimum": 0
        },
        "session_type": {
            "type": "string",
            "enum": ["ORDINARIO", "STRAORDINARIO"]
        },
        "max_seats": {
            "type": ["integer", "null"],
            "minimum": 1
        },
        "status": {
            "type": "string",
            "enum": ["OPEN", "CLOSED", "RECORDED", "CANCELLED"]
        },
        "cancelled_at": {
            "type": ["integer", "null"],
            "minimum": 0
        },
        "created_at": {
            "type": "integer",
            "minimum": 0
        }
    },
    "required": [
        "session_id",
        "course_id",
        "docente_matricola",
        "academic_year",
        "session_period",
        "exam_date",
        "reg_start_date",
        "reg_end_date",
        "session_type",
        "status",
        "created_at"
    ],
    "additionalProperties": False
}


# ==============================================================================
# 2. SCHEMI CLASSE PRENOTAZIONI
# ==============================================================================

# Payload HTTP inviato dallo Studente per prenotarsi all'appello
EXAM_BOOKING_CREATE_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "ExamBookingCreatePayload",
    "type": "object",
    "properties": {
        "session_id": {
            "type": "string",
            "minLength": 1,
            "maxLength": 64
        },
        "notes": {
            "type": ["string", "null"],
            "maxLength": 255
        }
    },
    "required": ["session_id"],
    "additionalProperties": False
}

# Record persistito on-chain nel World State (classe Prenotazioni)
EXAM_BOOKING_ONCHAIN_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "ExamBookingOnChainRecord",
    "type": "object",
    "properties": {
        "session_id": {
            "type": "string",
            "minLength": 1,
            "maxLength": 64
        },
        "student_matricola": {
            "type": "string",
            "pattern": r"^[0-9]{7}$"
        },
        "booking_date": {
            "type": "integer",
            "minimum": 0
        },
        "status": {
            "type": "string",
            "enum": ["CONFIRMED", "CANCELLED"]
        },
        "cancelled_reason": {
            "type": ["string", "null"],
            "maxLength": 100
        },
        "cancelled_at": {
            "type": ["integer", "null"],
            "minimum": 0
        },
        "notes": {
            "type": ["string", "null"],
            "maxLength": 255
        }
    },
    "required": [
        "session_id",
        "student_matricola",
        "booking_date",
        "status"
    ],
    "additionalProperties": False
}


# ==============================================================================
# 3. HELPER NAMESPACING (CHIAVI ON-CHAIN)
# ==============================================================================

def build_exam_key(session_id: str) -> str:
    """Costruisce la chiave univoca per la sessione d'esame."""
    return f"appello:{session_id}"

def build_booking_key(session_id: str, student_matricola: str) -> str:
    """Costruisce la chiave univoca composta per la prenotazione."""
    return f"prenotazione:{session_id}:{student_matricola}"