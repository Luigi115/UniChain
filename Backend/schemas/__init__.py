"""
schemas package
Espone il validatore e tutti i contratti JSON Schema del sistema UniChain.
"""
from schemas.validator import validate_schema

from schemas.user_schema import (
    USER_REGISTRATION_SCHEMA,
    USER_ONCHAIN_SCHEMA,
    build_user_key,
)

from schemas.exam_schema import (
    EXAM_SESSION_CREATE_SCHEMA,
    EXAM_SESSION_ONCHAIN_SCHEMA,
    EXAM_BOOKING_CREATE_SCHEMA,
    EXAM_BOOKING_ONCHAIN_SCHEMA,
    build_exam_key,
    build_booking_key,
)

from schemas.grade_schema import (
    GRADE_RECORD_CREATE_SCHEMA,
    GRADE_ONCHAIN_SCHEMA,
    CAREER_TRANSFER_REQUEST_SCHEMA,
    CAREER_WITHDRAWAL_REQUEST_SCHEMA,
    CAREER_GRADUATE_SCHEMA,
    CAREER_ONCHAIN_SCHEMA,
    build_grade_key,
    build_career_key,
)

__all__ = [
    "validate_schema",
    "USER_REGISTRATION_SCHEMA",
    "USER_ONCHAIN_SCHEMA",
    "build_user_key",
    "EXAM_SESSION_CREATE_SCHEMA",
    "EXAM_SESSION_ONCHAIN_SCHEMA",
    "EXAM_BOOKING_CREATE_SCHEMA",
    "EXAM_BOOKING_ONCHAIN_SCHEMA",
    "build_exam_key",
    "build_booking_key",
    "GRADE_RECORD_CREATE_SCHEMA",
    "GRADE_ONCHAIN_SCHEMA",
    "CAREER_TRANSFER_REQUEST_SCHEMA",
    "CAREER_WITHDRAWAL_REQUEST_SCHEMA",
    "CAREER_GRADUATE_SCHEMA",
    "CAREER_ONCHAIN_SCHEMA",
    "build_grade_key",
    "build_career_key",
]

'''
per fare un test si usa questo comando da mettere sul bash rimanendo nella cartella Backend!python -c "
from schemas import validate_schema, USER_REGISTRATION_SCHEMA, build_user_key
import jsonschema

# 1. Test dati validi
payload_ok = {
    'matricola': '0386587',
    'name': 'Mario',
    'surname': 'Rossi',
    'email': 'mario.rossi@unichain.it',
    'password': 'PasswordSegreta123',
    'role': 'STUDENTE'
}
try:
    validate_schema(payload_ok, USER_REGISTRATION_SCHEMA)
    print('PASS 1: Payload valido accettato.')
except Exception as e:
    print('FAIL 1: Errore inatteso ->', e)

# 2. Test chiave deterministica
chiave = build_user_key(payload_ok['matricola'])
assert chiave == 'user:0386587', 'Errore build_user_key'
print('PASS 2: Helper namespacing generato ->', chiave)

# 3. Test blocco matricola non a 7 cifre
payload_errato = payload_ok.copy()
payload_errato['matricola'] = '1234'
try:
    validate_schema(payload_errato, USER_REGISTRATION_SCHEMA)
    print('FAIL 3: La matricola errata non doveva passare.')
except jsonschema.exceptions.ValidationError:
    print('PASS 3: Matricola corta bloccata correttamente.')

# 4. Test blocco injection / campi extra
payload_inject = payload_ok.copy()
payload_inject['cmd_inject'] = '(eval (del-all))'
try:
    validate_schema(payload_inject, USER_REGISTRATION_SCHEMA)
    print('FAIL 4: Il campo extra non doveva passare.')
except jsonschema.exceptions.ValidationError:
    print('PASS 4: Campo extra bloccato da additionalProperties.')
"
'''
