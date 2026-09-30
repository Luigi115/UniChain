"""
routes/auth_routes.py
Livello 5: RESTful API Controller per Autenticazione e Profilo Utente.
"""

from flask import Blueprint, jsonify, request, g
from security import require_role
from services import AuthService

auth_bp = Blueprint("auth_bp", __name__, url_prefix="/api/v1/auth")


@auth_bp.route("/login", methods=["POST"])
def login():
    """
    POST /api/v1/auth/login
    Autentica l'utente confrontando l'hash bcrypt on-chain ed emette il JWT.
    """
    data = request.get_json() or {}
    matricola = data.get("matricola")
    password = data.get("password")

    if not matricola or not password:
        return jsonify({
            "status": "FAILED",
            "code": "MISSING_FIELDS",
            "message": "Matricola e password sono obbligatorie"
        }), 400

    result = AuthService.authenticate_user(matricola, password)

    if not result.get("success"):
        status_code = 403 if result.get("code") == "ACCOUNT_SUSPENDED" else 401
        return jsonify({
            "status": "FAILED",
            "code": result.get("code"),
            "message": result.get("error")
        }), status_code

    return jsonify({
        "status": "SUCCESS",
        "access_token": result["access_token"],
        "token_type": result["token_type"],
        "user": result["user"]
    }), 200


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