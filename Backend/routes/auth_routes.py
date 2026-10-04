"""
routes/auth_routes.py
Livello 5: RESTful API Controller per Autenticazione e Profilo Utente.
"""
from flask import Blueprint, jsonify, request, g
import jsonschema
from security import require_role
from services import AuthService
from schemas.user_schema import USER_LOGIN_SCHEMA
from schemas.validator import validate_schema

auth_bp = Blueprint("auth_bp", __name__, url_prefix="/api/v1/auth")


def _execute_login(expected_role: str | None = None):
    """Funzione di supporto interna al controller per non duplicare la gestione HTTP."""
    data = request.get_json() or {}

    try:
        validate_schema(data, USER_LOGIN_SCHEMA)
    except jsonschema.exceptions.ValidationError as e:
        return jsonify({"status": "FAILED", "code": "VALIDATION_ERR", "message": e.message}), 400

    result = AuthService.authenticate_user(
        matricola=data["matricola"],
        plain_password=data["password"],
        expected_role=expected_role
    )

    if not result.get("success"):
        code = result.get("code")
        # 403 se account sospeso o violazione di ruolo U3, altrimenti 401
        status_code = 403 if code in ["ACCOUNT_SUSPENDED", "U3"] else 401
        return jsonify({
            "status": "FAILED",
            "code": code,
            "message": result.get("error")
        }), status_code

    return jsonify({
        "status": "SUCCESS",
        "access_token": result["access_token"],
        "token_type": result["token_type"],
        "user": result["user"]
    }), 200


# 2. Endpoint Login Docente
@auth_bp.route("/docente-login", methods=["POST"])
def docente_login():
    return _execute_login(expected_role="DOCENTE")


# 3. Endpoint Login Studente
@auth_bp.route("/student-login", methods=["POST"])
def student_login():
    return _execute_login(expected_role="STUDENTE")

@auth_bp.route("/profile", methods=["GET"])
@require_role(["SEGRETERIA", "DOCENTE", "STUDENTE"])
def get_profile():
    """
    GET /api/v1/auth/profile
    Restituisce i dati del profilo estratto dal token JWT convalidato.
    """
    current_user = getattr(g, "current_user", {})
    return jsonify({
        "status": "SUCCESS",
        "user": current_user
    }), 200
    

@auth_bp.route("/admin-login", methods=["POST"])
def admin_login():
    """
    POST /api/v1/auth/admin-login
    Data Path 3.4: Endpoint dedicato all'accesso della Segreteria Studenti.
    """
    data = request.get_json() or {}

    # 1. Validazione schema formale (Livello 2)
    try:
        validate_schema(data, USER_LOGIN_SCHEMA)
    except Exception as e:
        return jsonify({
            "status": "FAILED",
            "code": "VALIDATION_ERR",
            "message": str(e)
        }), 400

    # 2. Invocazione del servizio applicativo (Livello 3)
    result = AuthService.login_admin(
        matricola=data["matricola"],
        password=data["password"]
    )

    if not result.get("success"):
        code = result.get("code")
        # 403 Forbidden se c'è violazione di ruolo/cattedra U3 o account sospeso, altrimenti 401
        status_code = 403 if code in ["U3", "ACCOUNT_SUSPENDED"] else 401
        return jsonify({
            "status": "FAILED",
            "code": code,
            "message": result.get("error")
        }), status_code

    return jsonify({
        "status": "SUCCESS",
        "token": result["token"],
        "user": result["user"]
    }), 200