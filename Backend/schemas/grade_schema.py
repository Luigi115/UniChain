"""
schemas/grade_schema.py
Definizione dei contratti JSON Schema e helper di namespacing 
per le classi Voti e Careers.
"""

# ==============================================================================
# 1. SCHEMI CLASSE VOTI (VERBALIZZAZIONE DOCENTE)
# ==============================================================================

# Payload HTTP inviato dal Docente per registrare un esito d'esame
GRADE_RECORD_CREATE_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "GradeRecordCreatePayload",
    "type": "object",
    "properties": {
        "student_matricola": {
            "type": "string",
            "pattern": r"^[0-9]{7}$"
        },
        "grade": {
            "type": ["integer", "null"],
            "minimum": 18,
            "maximum": 30
        },
        "has_honors": {
            "type": "boolean"
        },
        "outcome_status": {
            "type": "string",
            "enum": ["PASSED", "REJECTED", "WITHDRAWN", "ABSENT"]
        }
    },
    "required": [
        "student_matricola",
        "grade",
        "has_honors",
        "outcome_status"
    ],
    "additionalProperties": False
}

# Record persistito on-chain nel World State (classe Voti)
GRADE_ONCHAIN_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "GradeOnChainRecord",
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
        "docente_matricola": {
            "type": "string",
            "pattern": r"^[0-9]{7}$"
        },
        "grade": {
            "type": ["integer", "null"],
            "minimum": 18,
            "maximum": 30
        },
        "has_honors": {
            "type": "boolean"
        },
        "outcome_status": {
            "type": "string",
            "enum": ["PASSED", "REJECTED", "WITHDRAWN", "ABSENT"]
        },
        "signed_at": {
            "type": "integer",
            "minimum": 0
        }
    },
    "required": [
        "session_id",
        "student_matricola",
        "docente_matricola",
        "grade",
        "has_honors",
        "outcome_status",
        "signed_at"
    ],
    "additionalProperties": False
}


# ==============================================================================
# 2. SCHEMI CLASSE CAREERS (GESTIONE CARRIERA E STATI)
# ==============================================================================

# Payload HTTP inviato dallo Studente per richiesta passaggio di corso
CAREER_TRANSFER_REQUEST_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "CareerTransferRequestPayload",
    "type": "object",
    "properties": {
        "target_degree_id": {
            "type": "string",
            "minLength": 2,
            "maxLength": 20
        },
        "motivation": {
            "type": "string",
            "minLength": 5,
            "maxLength": 500
        }
    },
    "required": ["target_degree_id", "motivation"],
    "additionalProperties": False
}

# Payload HTTP inviato dallo Studente per istanza di rinuncia agli studi
CAREER_WITHDRAWAL_REQUEST_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "CareerWithdrawalRequestPayload",
    "type": "object",
    "properties": {
        "reason": {
            "type": "string",
            "minLength": 5,
            "maxLength": 500
        }
    },
    "required": ["reason"],
    "additionalProperties": False
}

# Payload HTTP per l'approvazione e proclamazione di Laurea
CAREER_GRADUATE_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "CareerGraduatePayload",
    "type": "object",
    "properties": {
        "final_grade": {
            "type": "integer",
            "minimum": 66,
            "maximum": 110
        },
        "has_honors": {
            "type": "boolean"
        }
    },
    "required": ["final_grade", "has_honors"],
    "additionalProperties": False
}

# Struttura del singolo esame verbalizzato all'interno della carriera
PASSED_EXAM_SUB_SCHEMA = {
    "type": "object",
    "properties": {
        "course_id": {
            "type": "string",
            "minLength": 2,
            "maxLength": 20
        },
        "grade": {
            "type": "integer",
            "minimum": 18,
            "maximum": 30
        },
        "has_honors": {
            "type": "boolean"
        },
        "recorded_at": {
            "type": "integer",
            "minimum": 0
        }
    },
    "required": ["course_id", "grade", "has_honors", "recorded_at"],
    "additionalProperties": False
}

# Record persistito on-chain nel World State (classe Careers)
CAREER_ONCHAIN_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "CareerOnChainRecord",
    "type": "object",
    "properties": {
        "student_matricola": {
            "type": "string",
            "pattern": r"^[0-9]{7}$"
        },
        "degree_id": {
            "type": "string",
            "minLength": 2,
            "maxLength": 20
        },
        "cfu_total": {
            "type": "integer",
            "minimum": 0,
            "maximum": 180
        },
        "status": {
            "type": "string",
            "enum": ["ENROLLED", "TRANSFER_PENDING", "WITHDRAWN", "GRADUATED"]
        },
        "passed_exams": {
            "type": "array",
            "items": PASSED_EXAM_SUB_SCHEMA
        },
        "graduation_request_date": {
            "type": ["integer", "null"],
            "minimum": 0
        },
        "last_updated": {
            "type": "integer",
            "minimum": 0
        }
    },
    "required": [
        "student_matricola",
        "degree_id",
        "cfu_total",
        "status",
        "passed_exams",
        "graduation_request_date",
        "last_updated"
    ],
    "additionalProperties": False
}


# ==============================================================================
# 3. HELPER NAMESPACING (CHIAVI ON-CHAIN)
# ==============================================================================

def build_grade_key(session_id: str, student_matricola: str) -> str:
    """Costruisce la chiave logica del voto verbalizzato."""
    return f"voto:{session_id}:{student_matricola}"

def build_career_key(student_matricola: str) -> str:
    """Costruisce la chiave logica della carriera accademica dello studente."""
    return f"career:{student_matricola}"