"""
routes/admin_routes.py
Livello 5: RESTful API Controller per la Segreteria Studenti.
Presidia onboarding, gestione utenze, passaggi, rinunce e proclamazione di laurea (U6).
"""

from flask import Blueprint, jsonify, request
import jsonschema

from security import require_role
from schemas import (
    validate_schema,
    USER_REGISTRATION_SCHEMA,
    CAREER_GRADUATE_SCHEMA,
    build_user_key,
)
from services import AuthService, AdminService
from fabric.lisp_client import LispClient

admin_bp = Blueprint("admin_bp", __name__, url_prefix="/api/v1")


@admin_bp.route("/users/register", methods=["POST"])
@require_role(["SEGRETERIA"])
def register_user():
    """
    POST /api/v1/users/register
    Registra una nuova utenza e ne calcola l'hash bcrypt on-chain.
    """
    data = request.get_json() or {}

    try:
        validate_schema(data, USER_REGISTRATION_SCHEMA)
    except jsonschema.exceptions.ValidationError as e:
        return jsonify({"status": "FAILED", "code": "VALIDATION_ERR", "message": e.message}), 400

    result = AuthService.register_user(
        matricola=data["matricola"],
        name=data["name"],
        surname=data["surname"],
        email=data["email"],
        plain_password=data["password"],
        role=data["role"]
    )

    if not result.get("success"):
        return jsonify({
            "status": "FAILED",
            "code": result.get("code"),
            "message": result.get("error")
        }), 400

    return jsonify({"status": "SUCCESS", "user": result["data"]}), 201


@admin_bp.route("/users/<matricola>", methods=["GET"])
@require_role(["SEGRETERIA"])
def get_user_profile(matricola: str):
    """
    GET /api/v1/users/<matricola>
    Recupera l'anagrafica utente omettendo l'hash della password.
    """
    user_key = build_user_key(matricola)
    res = LispClient.get_kv("Users", user_key)
    user = res.get("value") if isinstance(res, dict) else res

    if not user:
        return jsonify({"status": "FAILED", "code": "NOT_FOUND", "message": "Utente non trovato"}), 404

    safe_user = dict(user)
    safe_user.pop("password_hash", None)

    return jsonify({"status": "SUCCESS", "user": safe_user}), 200


@admin_bp.route("/users/<matricola>/status", methods=["PUT"])
@require_role(["SEGRETERIA"])
def update_user_status(matricola: str):
    """
    PUT /api/v1/users/<matricola>/status
    Aggiorna lo stato amministrativo dell'account (ACTIVE | SUSPENDED).
    """
    data = request.get_json() or {}
    new_status = data.get("status")

    if new_status not in ["ACTIVE", "SUSPENDED"]:
        return jsonify({
            "status": "FAILED",
            "code": "INVALID_STATUS",
            "message": "Stato non valido: ammessi solo ACTIVE o SUSPENDED"
        }), 400

    result = AdminService.update_user_status(matricola, new_status)
    if not result.get("success"):
        return jsonify({"status": "FAILED", "code": result.get("code"), "message": result.get("error")}), 400

    return jsonify({"status": "SUCCESS", "user": result["data"]}), 200


@admin_bp.route("/career/<matricola>/transfer", methods=["POST"])
@require_role(["SEGRETERIA"])
def approve_transfer(matricola: str):
    """
    POST /api/v1/career/<matricola>/transfer
    Convalida il passaggio di corso verso un nuovo ordinamento didattico.
    """
    data = request.get_json() or {}
    new_degree_id = data.get("new_degree_id")

    if not new_degree_id:
        return jsonify({"status": "FAILED", "code": "MISSING_FIELD", "message": "new_degree_id obbligatorio"}), 400

    result = AdminService.approve_course_transfer(
        matricola=matricola,
        new_degree_id=new_degree_id,
        notes=data.get("notes")
    )
    if not result.get("success"):
        return jsonify({"status": "FAILED", "code": result.get("code"), "message": result.get("error")}), 400

    return jsonify({"status": "SUCCESS", "career": result["data"]}), 200


@admin_bp.route("/career/<matricola>/withdraw", methods=["POST"])
@require_role(["SEGRETERIA"])
def approve_withdrawal(matricola: str):
    """
    POST /api/v1/career/<matricola>/withdraw
    Formalizza la rinuncia agli studi e sospende contestualmente l'utenza.
    """
    data = request.get_json() or {}
    reason = data.get("reason", "Rinuncia formale agli studi")

    result = AdminService.approve_withdrawal(matricola, reason=reason)
    if not result.get("success"):
        return jsonify({"status": "FAILED", "code": result.get("code"), "message": result.get("error")}), 400

    return jsonify({"status": "SUCCESS", "career": result["data"]}), 200


@admin_bp.route("/career/<matricola>/graduate", methods=["POST"])
@require_role(["SEGRETERIA"])
def approve_graduation(matricola: str):
    """
    POST /api/v1/career/<matricola>/graduate
    Verifica i requisiti didattici (CFU totali) e proclama la laurea (Anomalia U6 in caso di blocco).
    """
    data = request.get_json() or {}

    try:
        validate_schema(data, CAREER_GRADUATE_SCHEMA)
    except jsonschema.exceptions.ValidationError as e:
        return jsonify({"status": "FAILED", "code": "VALIDATION_ERR", "message": e.message}), 400

    result = AdminService.approve_graduation(
        matricola=matricola,
        final_grade=data["final_grade"],
        has_honors=data.get("has_honors", False)
    )

    if not result.get("success"):
        return jsonify({
            "status": "FAILED",
            "code": result.get("code"),
            "message": result.get("error")
        }), 400

    return jsonify({"status": "SUCCESS", "career": result["data"]}), 200