"""
services/auth_service.py
Livello 3: Business Logic Engine per Autenticazione, Verifica Credenziali e Onboarding.
Interagisce con security/ (Bcrypt, JWT) e fabric/ (Users, Careers).
"""
import time
from typing import Any, Dict, Optional
from fabric.lisp_client import LispClient
from schemas.user_schema import build_user_key
from schemas.grade_schema import build_career_key
from security import hash_password, verify_password, create_access_token


class AuthService:

    @staticmethod
    def authenticate_user(
        matricola: str, 
        plain_password: str, 
        expected_role: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Valida le credenziali dell'utente sul World State ed emette il token JWT.
        Se 'expected_role' è specificato, verifica che l'utente possieda tale ruolo
        nel proprio record on-chain, sollevando Anomalia U3 in caso di discrepanza.
        """
        user_key = build_user_key(matricola)
        user_res = LispClient.get_kv("Users", user_key)
        user_record = user_res.get("value") if isinstance(user_res, dict) and "value" in user_res else user_res

        # 1. Verifica esistenza record on-chain
        if not user_record or not isinstance(user_record, dict):
            return {
                "success": False,
                "error": "Credenziali non valide",
                "code": "U5"
            }

        # 2. Controllo stato amministrativo
        if user_record.get("status") != "ACTIVE":
            return {
                "success": False,
                "error": "Accesso negato: utenza sospesa o non attiva",
                "code": "ACCOUNT_SUSPENDED"
            }

        # 3. Controllo corrispondenza ruolo (Isolamento Portale / Anomalia U3)
        user_roles = user_record.get("roles", [])
        if expected_role and expected_role.upper() not in user_roles:
            return {
                "success": False,
                "error": f"Accesso negato: l'utenza non possiede il ruolo {expected_role}",
                "code": "U3"
            }

        # 4. Verifica crittografica dell'hash bcrypt
        stored_hash = user_record.get("password_hash", "")
        if not verify_password(plain_password, stored_hash):
            return {
                "success": False,
                "error": "Credenziali non valide",
                "code": "U5"
            }

        # 5. Rilascio del token JWT stateless
        access_token = create_access_token(
            matricola=user_record["matricola"],
            roles=user_roles
        )

        safe_user = {
            "matricola": user_record["matricola"],
            "roles": user_roles,
            "name": user_record.get("name"),
            "surname": user_record.get("surname"),
            "email": user_record.get("email")
        }

        return {
            "success": True,
            "access_token": access_token,
            "token_type": "Bearer",
            "user": safe_user
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
        existing_user = LispClient.get_kv("Users", user_key)
        val = existing_user.get("value") if isinstance(existing_user, dict) and "value" in existing_user else existing_user
        if val:
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

        safe_response = dict(user_payload)
        safe_response.pop("password_hash", None)
        return {"success": True, "data": safe_response}
    @staticmethod
    def login_admin(matricola: str, password: str) -> Dict[str, Any]:
        """
        Data Path 3.4: Login per gli operatori di Segreteria.
        Verifica esistenza utente, stato ACTIVE, ruolo SEGRETERIA e password hash.
        """
        user_key = build_user_key(matricola)
        res = LispClient.get_kv("Users", user_key)
        user = res.get("value") if isinstance(res, dict) and "value" in res else res

        # 1. Verifica esistenza
        if not user or not isinstance(user, dict):
            return {
                "success": False,
                "error": "Credenziali non valide",
                "code": "U5"
            }

        # 2. Verifica stato utenza
        if user.get("status") != "ACTIVE":
            return {
                "success": False,
                "error": "Utenza disabilitata o sospesa",
                "code": "ACCOUNT_SUSPENDED"
            }

        # 3. Controllo esclusività del ruolo SEGRETERIA (Anomalia U3)
        roles = user.get("roles", [])
        if "SEGRETERIA" not in roles:
            return {
                "success": False,
                "error": "Accesso non autorizzato: l'utenza non appartiene al personale di Segreteria",
                "code": "U3"
            }

        # 4. Verifica password bcrypt
        pwd_hash = user.get("password_hash", "")
        if not verify_password(password, pwd_hash):
            return {
                "success": False,
                "error": "Credenziali non valide",
                "code": "U5"
            }

        # 5. Generazione Token JWT
        token = create_access_token(
            matricola=user["matricola"],
            roles=user["roles"],
            name=user.get("name", "")
        )

        safe_user = dict(user)
        safe_user.pop("password_hash", None)

        return {
            "success": True,
            "token": token,
            "user": safe_user
        }