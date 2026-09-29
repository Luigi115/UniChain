"""
security/rbac.py
Gestione delle sessioni stateless e controllo accessi basato sui ruoli (RBAC):
- Generazione e validazione dei JSON Web Token (JWT)
- Decoratore @require_role per proteggere le route REST
- Intercettazione dell'Anomalia U3 (Violazione del controllo accessi)
"""

import time
from functools import wraps
from flask import request, jsonify, g
import jwt

# Configurazioni di default (sovrascrivibili da config.py)
JWT_SECRET = "unichain_secret_jwt_key_2026_super_secure"
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_SECONDS = 28800  # 8 ore di validità


# ==============================================================================
# 1. GESTIONE DEI TOKEN JWT
# ==============================================================================

def create_access_token(
    matricola: str,
    roles: list[str],
    expires_in: int = JWT_EXPIRATION_SECONDS,
    secret_key: str = JWT_SECRET
) -> str:
    """
    Genera un token JWT firmato crittograficamente con algoritmo HS256.
    Include nel payload matricola, ruoli, timestamp di emissione e di scadenza.
    """
    now = int(time.time())
    payload = {
        "matricola": matricola,
        "roles": roles,
        "iat": now,
        "exp": now + expires_in
    }
    return jwt.encode(payload, secret_key, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str, secret_key: str = JWT_SECRET) -> dict:
    """
    Decodifica e verifica la firma e la validità temporale del token JWT.
    Solleva eccezioni PyJWT se il token è scaduto, manomesso o non valido.
    """
    return jwt.decode(token, secret_key, algorithms=[JWT_ALGORITHM])


# ==============================================================================
# 2. DECORATORE RBAC PER FLASK (@require_role)
# ==============================================================================

def require_role(allowed_roles: list[str]):
    """
    Decoratore per endpoint Flask.
    1. Estrae il token JWT dall'header 'Authorization: Bearer <token>'
    2. Valida la firma e la scadenza del token
    3. Controlla che almeno uno dei ruoli dell'utente sia presente tra gli allowed_roles
    4. Se l'utente non ha i permessi necessari, solleva l'Anomalia U3 (403 Forbidden)
    5. Inietta i dati dell'utente autenticato in flask.g.current_user
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            auth_header = request.headers.get("Authorization", None)
            
            # Controllo presenza e formato header
            if not auth_header or not auth_header.startswith("Bearer "):
                return jsonify({
                    "error": "Token di autenticazione mancante o formato non valido",
                    "code": "MISSING_TOKEN"
                }), 401

            token = auth_header.split(" ", 1)[1].strip()

            try:
                payload = decode_access_token(token)
            except jwt.ExpiredSignatureError:
                return jsonify({
                    "error": "Sessione scaduta: effettuare nuovamente il login",
                    "code": "TOKEN_EXPIRED"
                }), 401
            except jwt.InvalidTokenError:
                return jsonify({
                    "error": "Token non valido o manomesso",
                    "code": "INVALID_TOKEN"
                }), 401

            # Controllo ruoli (RBAC)
            user_roles = payload.get("roles", [])
            has_permission = any(role in allowed_roles for role in user_roles)

            if not has_permission:
                # Violazione del controllo accessi: Anomalia U3
                return jsonify({
                    "error": "Accesso negato: privilegi insufficienti per questa operazione",
                    "code": "U3",
                    "anomaly": "Violazione del controllo accessi (RBAC)"
                }), 403

            # Memorizza i dettagli dell'utente nel contesto globale della richiesta
            g.current_user = payload

            return f(*args, **kwargs)
        return decorated_function
    return decorator