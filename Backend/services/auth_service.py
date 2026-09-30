"""
services/auth_service.py
Livello 3: Business Logic Engine per Autenticazione, Verifica Credenziali e Onboarding.
Interagisce con security/ (Bcrypt, JWT) e fabric/ (Users, Careers).
"""

import time
from typing import Any, Dict, List, Optional

from fabric.lisp_client import LispClient
from schemas.user_schema import build_user_key
from schemas.grade_schema import build_career_key
from security import hash_password, verify_password, create_access_token


class AuthService:

    @staticmethod
    def authenticate_user(matricola: str, plain_password: str) -> Dict[str, Any]:
        """
        Valida le credenziali dell'utente sul World State ed emette il token JWT.
        """
        user_key = build_user_key(matricola)
        user_res = LispClient.get_kv("Users", user_key)
        user_record = user_res.get("value")

        if not user_record:
            return {
                "success": False,
                "error": "Credenziali non valide o utente inesistente",
                "code": "INVALID_CREDENTIALS"
            }

        # Controllo stato amministrativo
        if user_record.get("status") != "ACTIVE":
            return {
                "success": False,
                "error": "Accesso negato: utenza sospesa o non attiva",
                "code": "ACCOUNT_SUSPENDED"
            }

        # Verifica crittografica dell'hash bcrypt
        stored_hash = user_record.get("password_hash", "")
        if not verify_password(plain_password, stored_hash):
            return {
                "success": False,
                "error": "Credenziali non valide",
                "code": "INVALID_CREDENTIALS"
            }

        # Rilascio del token JWT stateless
        roles = user_record.get("roles", [])
        access_token = create_access_token(
            matricola=user_record["matricola"],
            roles=roles
        )

        return {
            "success": True,
            "access_token": access_token,
            "token_type": "Bearer",
            "user": {
                "matricola": user_record["matricola"],
                "roles": roles,
                "name": user_record.get("name"),
                "surname": user_record.get("surname"),
                "email": user_record.get("email")
            }
        }

    @staticmethod
    def register_user(
        matricola: str,
        name: str,
        surname: str,
        email: str,
        plain_password: str,
        role: str,
        degree_id: Optional[str] = "ING-INF"
    ) -> Dict[str, Any]:
        """
        Registra una nuova utenza sul Ledger accademico e inizializza
        la relativa carriera qualora il ruolo sia STUDENTE.
        """
        now = int(time.time())
        user_key = build_user_key(matricola)

        # 1. Verifica collisione di matricola
        existing_user = LispClient.get_kv("Users", user_key).get("value")
        if existing_user:
            return {
                "success": False,
                "error": f"L'utente con matricola {matricola} risulta già registrato",
                "code": "DUPLICATE_USER"
            }

        # 2. Hashing della password tramite Bcrypt
        pwd_hash = hash_password(plain_password)

        # 3. Payload utente per il World State
        user_payload = {
            "matricola": matricola,
            "roles": [role.upper()],
            "name": name,
            "surname": surname,
            "email": email,
            "password_hash": pwd_hash,
            "status": "ACTIVE",
            "created_at": now,
            "updated_at": now
        }

        res_user = LispClient.add_kv("Users", user_key, user_payload)
        if res_user.get("status") == "ERROR":
            return {"success": False, "error": res_user.get("message", "Errore persistenza Fabric"), "code": "FABRIC_ERR"}

        # 4. Inizializzazione automatica carriera per il ruolo STUDENTE
        if role.upper() == "STUDENTE":
            career_key = build_career_key(matricola)
            career_payload = {
                "student_matricola": matricola,
                "degree_id": degree_id,
                "cfu_total": 180,
                "cfu_acquired": 0,
                "status": "ENROLLED",
                "passed_exams": [],
                "created_at": now,
                "last_updated": now
            }
            LispClient.add_kv("Careers", career_key, career_payload)

        # Omissione dell'hash nella risposta per sicurezza
        safe_response = user_payload.copy()
        safe_response.pop("password_hash", None)

        return {"success": True, "data": safe_response}