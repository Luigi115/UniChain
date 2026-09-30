"""
routes/docente_routes.py
Livello 5: RESTful API Controller per il Docente.
Presidia creazione appelli, lista prenotati e verbalizzazione voti on-chain.
"""

from flask import Blueprint, jsonify, request, g
import jsonschema

from security import require_role
from schemas import (
    validate_schema,
    EXAM_SESSION_CREATE_SCHEMA,
    GRADE_RECORD_CREATE_SCHEMA,
)
from services import ExamService, GradeService
from fabric.lisp_client import LispClient

docente_bp = Blueprint("docente_bp", __name__, url_prefix="/api/v1")


@docente_bp.route("/exams/sessions", methods=["POST"])
@require_role(["DOCENTE"])
def create_exam_session():
    """
    POST /api/v1/exams/sessions
    Crea una nuova sessione d'esame nel World State.
    """
    data = request.get_json() or {}

    try:
        validate_schema(data, EXAM_SESSION_CREATE_SCHEMA)
    except jsonschema.exceptions.ValidationError as e:
        return jsonify({"status": "FAILED", "code": "VALIDATION_ERR", "message": e.message}), 400

    docente_matr = g.current_user["matricola"]
    result = ExamService.create_exam_session(
        docente_matricola=docente_matr,
        course_id=data["course_id"],
        exam_date=data["exam_date"],
        reg_start_date=data["reg_start_date"],
        reg_end_date=data["reg_end_date"],
        session_type=data["session_type"],
        max_seats=data.get("max_seats")
    )

    if not result.get("success"):
        return jsonify({
            "status": "FAILED",
            "code": result.get("code"),
            "message": result.get("error")
        }), 400

    return jsonify({"status": "SUCCESS", "session": result["data"]}), 201


@docente_bp.route("/exams/sessions/<session_id>/candidates", methods=["GET"])
@require_role(["DOCENTE"])
def get_exam_candidates(session_id: str):
    """
    GET /api/v1/exams/sessions/<session_id>/candidates
    Recupera l'elenco degli studenti iscritti con prenotazione confermata.
    """
    res = LispClient.execute("GetKeys", "Prenotazioni")
    keys = res.get("keys", []) if isinstance(res, dict) else []

    prefix = f"prenotazione:{session_id}:"
    candidates = []

    for key in keys:
        if key.startswith(prefix):
            booking_res = LispClient.get_kv("Prenotazioni", key)
            if booking_res and booking_res.get("status") == "CONFIRMED":
                candidates.append(booking_res)

    return jsonify({"status": "SUCCESS", "session_id": session_id, "candidates": candidates}), 200


@docente_bp.route("/exams/sessions/<session_id>/grades", methods=["POST"])
@require_role(["DOCENTE"])
def record_student_grade(session_id: str):
    """
    POST /api/v1/exams/sessions/<session_id>/grades
    Verbalizza la valutazione didattica. Intercetta Anomalia U3 e Anomalia U4.
    """
    data = request.get_json() or {}

    try:
        validate_schema(data, GRADE_RECORD_CREATE_SCHEMA)
    except jsonschema.exceptions.ValidationError as e:
        return jsonify({"status": "FAILED", "code": "VALIDATION_ERR", "message": e.message}), 400

    docente_matr = g.current_user["matricola"]
    result = GradeService.record_student_grade(
        session_id=session_id,
        student_matricola=data["student_matricola"],
        docente_matricola=docente_matr,
        grade=data.get("grade"),
        has_honors=data.get("has_honors", False),
        outcome_status=data["outcome_status"]
    )

    if not result.get("success"):
        status_code = 403 if result.get("code") == "U3" else 400
        return jsonify({
            "status": "FAILED",
            "code": result.get("code"),
            "message": result.get("error")
        }), status_code

    return jsonify({"status": "SUCCESS", "grade": result["data"]}), 201


@docente_bp.route("/exams/sessions/<session_id>/close", methods=["POST"])
@require_role(["DOCENTE"])
def close_exam_session(session_id: str):
    """
    POST /api/v1/exams/sessions/<session_id>/close
    Chiude e sigilla una sessione d'esame.
    """
    docente_matr = g.current_user["matricola"]
    result = ExamService.close_exam_session(session_id, docente_matr)

    if not result.get("success"):
        status_code = 403 if result.get("code") == "U3" else 400
        return jsonify({
            "status": "FAILED",
            "code": result.get("code"),
            "message": result.get("error")
        }), status_code

    return jsonify({"status": "SUCCESS", "session": result["data"]}), 200


@docente_bp.route("/exams/grades/history/<session_id>/<student_matricola>", methods=["GET"])
@require_role(["DOCENTE", "SEGRETERIA"])
def get_grade_history(session_id: str, student_matricola: str):
    """
    GET /api/v1/exams/grades/history/<session_id>/<student_matricola>
    Estrae l'audit trail inalterabile dello storico voti tramite GetKeyHistory.
    """
    result = GradeService.get_grade_history(session_id, student_matricola)
    return jsonify({"status": "SUCCESS", "history": result.get("history", [])}), 200