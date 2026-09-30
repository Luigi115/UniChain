"""
routes/student_routes.py
Livello 5: RESTful API Controller per lo Studente.
Presidia prenotazioni, consultazione appelli e visualizzazione libretto on-chain.
"""

import time
from flask import Blueprint, jsonify, request, g
import jsonschema

from security import require_role
from schemas import (
    validate_schema,
    EXAM_BOOKING_CREATE_SCHEMA,
    CAREER_TRANSFER_REQUEST_SCHEMA,
    CAREER_WITHDRAWAL_REQUEST_SCHEMA,
)
from services import ExamService, GradeService, AdminService
from fabric.lisp_client import LispClient

student_bp = Blueprint("student_bp", __name__, url_prefix="/api/v1")


@student_bp.route("/exams/sessions/available", methods=["GET"])
@require_role(["STUDENTE"])
def get_available_exam_sessions():
    """
    GET /api/v1/exams/sessions/available
    Restituisce l'elenco degli appelli aperti con finestra di registrazione attiva.
    """
    now = int(time.time())
    res = LispClient.execute("GetKeys", "Appelli")
    keys = res.get("keys", []) if isinstance(res, dict) else []

    available = []
    for key in keys:
        session = LispClient.get_kv("Appelli", key)
        if session and session.get("status") == "OPEN":
            if session.get("reg_start_date", 0) <= now <= session.get("reg_end_date", 0):
                available.append(session)

    return jsonify({"status": "SUCCESS", "sessions": available}), 200


@student_bp.route("/exams/bookings", methods=["POST"])
@require_role(["STUDENTE"])
def book_exam():
    """
    POST /api/v1/exams/bookings
    Invia la prenotazione a un esame. Esegue verifiche formali e propedeuticità (U2).
    """
    data = request.get_json() or {}

    try:
        validate_schema(data, EXAM_BOOKING_CREATE_SCHEMA)
    except jsonschema.exceptions.ValidationError as e:
        return jsonify({"status": "FAILED", "code": "VALIDATION_ERR", "message": e.message}), 400

    student_matr = g.current_user["matricola"]
    result = ExamService.book_exam_session(
        session_id=data["session_id"],
        student_matricola=student_matr,
        notes=data.get("notes")
    )

    if not result.get("success"):
        return jsonify({
            "status": "FAILED",
            "code": result.get("code"),
            "message": result.get("error")
        }), 400

    return jsonify({"status": "SUCCESS", "booking": result["data"]}), 201


@student_bp.route("/exams/bookings/<session_id>", methods=["DELETE"])
@require_role(["STUDENTE"])
def cancel_booking(session_id: str):
    """
    DELETE /api/v1/exams/bookings/<session_id>
    Revoca una prenotazione prima della scadenza della finestra didattica.
    """
    student_matr = g.current_user["matricola"]
    result = ExamService.cancel_booking(session_id, student_matr)

    if not result.get("success"):
        return jsonify({
            "status": "FAILED",
            "code": result.get("code"),
            "message": result.get("error")
        }), 400

    return jsonify({"status": "SUCCESS", "data": result["data"]}), 200


@student_bp.route("/career/transcript", methods=["GET"])
@require_role(["STUDENTE"])
def get_transcript():
    """
    GET /api/v1/career/transcript
    Restituisce in sola lettura il libretto accademico dello studente.
    """
    student_matr = g.current_user["matricola"]
    result = GradeService.get_student_transcript(student_matr)

    if not result.get("success"):
        return jsonify({
            "status": "FAILED",
            "code": result.get("code"),
            "message": result.get("error")
        }), 404

    return jsonify({"status": "SUCCESS", "transcript": result["transcript"]}), 200


@student_bp.route("/career/requests/transfer", methods=["POST"])
@require_role(["STUDENTE"])
def request_transfer():
    """
    POST /api/v1/career/requests/transfer
    Inoltra formale richiesta di passaggio di corso.
    """
    data = request.get_json() or {}
    try:
        validate_schema(data, CAREER_TRANSFER_REQUEST_SCHEMA)
    except jsonschema.exceptions.ValidationError as e:
        return jsonify({"status": "FAILED", "code": "VALIDATION_ERR", "message": e.message}), 400

    student_matr = g.current_user["matricola"]
    result = AdminService.approve_course_transfer(
        matricola=student_matr,
        new_degree_id=data["target_degree_id"],
        notes=data.get("motivation")
    )

    if not result.get("success"):
        return jsonify({"status": "FAILED", "code": result.get("code"), "message": result.get("error")}), 400

    return jsonify({"status": "SUCCESS", "career": result["data"]}), 200


@student_bp.route("/career/requests/withdrawal", methods=["POST"])
@require_role(["STUDENTE"])
def request_withdrawal():
    """
    POST /api/v1/career/requests/withdrawal
    Inoltra formale rinuncia agli studi.
    """
    data = request.get_json() or {}
    try:
        validate_schema(data, CAREER_WITHDRAWAL_REQUEST_SCHEMA)
    except jsonschema.exceptions.ValidationError as e:
        return jsonify({"status": "FAILED", "code": "VALIDATION_ERR", "message": e.message}), 400

    student_matr = g.current_user["matricola"]
    result = AdminService.approve_withdrawal(student_matr, reason=data["reason"])

    if not result.get("success"):
        return jsonify({"status": "FAILED", "code": result.get("code"), "message": result.get("error")}), 400

    return jsonify({"status": "SUCCESS", "career": result["data"]}), 200