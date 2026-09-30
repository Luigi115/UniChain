"""
services/grade_service.py
Livello 3: Business Logic & Chain-of-Events Engine per Verbalizzazione Voti e Carriere.
Presidia l'esclusività della cattedra (Anomalia U3), la sequenza voto-prenotazione (Anomalia U4)
e l'aggiornamento contestuale del libretto on-chain.
"""

import time
from typing import Any, Dict, Optional

from fabric.lisp_client import LispClient
from schemas.exam_schema import build_exam_key, build_booking_key
from schemas.grade_schema import build_grade_key, build_career_key


class GradeService:

    @staticmethod
    def record_student_grade(
        session_id: str,
        student_matricola: str,
        docente_matricola: str,
        grade: Optional[int],
        has_honors: bool,
        outcome_status: str
    ) -> Dict[str, Any]:
        """
        Registra la valutazione ufficiale dello studente per una specifica sessione d'esame.
        Esegue i controlli deterministici su esclusività cattedra (U3) e sequenzialità (U4).
        """
        now = int(time.time())

        # ----------------------------------------------------------------------
        # 1. Verifica Esclusività della Cattedra (Anomalia U3)
        # ----------------------------------------------------------------------
        exam_key = build_exam_key(session_id)
        res_exam = LispClient.get_kv("Appelli", exam_key)
        appello = res_exam.get("value")

        if not appello:
            return {
                "success": False,
                "error": "Sessione d'esame inesistente",
                "code": "NOT_FOUND"
            }

        if appello.get("docente_matricola") != docente_matricola:
            return {
                "success": False,
                "error": "Violazione cattedra: solo il docente titolare può verbalizzare voti",
                "code": "U3"
            }

        # ----------------------------------------------------------------------
        # 2. Verifica Sequenza Canonica: Presenza Prenotazione (Anomalia U4)
        # ----------------------------------------------------------------------
        booking_key = build_booking_key(session_id, student_matricola)
        res_booking = LispClient.get_kv("Prenotazioni", booking_key)
        booking = res_booking.get("value")

        if not booking or booking.get("status") != "CONFIRMED":
            return {
                "success": False,
                "error": "Evento fuori sequenza: tentativo di verbalizzare un voto senza prenotazione confermata",
                "code": "U4"
            }

        # ----------------------------------------------------------------------
        # 3. Consolidamento del Voto sul Ledger (Classe Voti)
        # ----------------------------------------------------------------------
        grade_key = build_grade_key(session_id, student_matricola)
        voto_payload = {
            "session_id": session_id,
            "student_matricola": student_matricola,
            "docente_matricola": docente_matricola,
            "grade": grade,
            "has_honors": has_honors,
            "outcome_status": outcome_status,
            "signed_at": now
        }

        res_voto = LispClient.add_kv("Voti", grade_key, voto_payload)
        if res_voto.get("status") == "ERROR":
            return {"success": False, "error": res_voto.get("message", "Errore Fabric"), "code": "FABRIC_ERR"}

        # ----------------------------------------------------------------------
        # 4. Aggiornamento Contestuale della Carriera (Classe Careers)
        # ----------------------------------------------------------------------
        if outcome_status == "PASSED" and grade is not None:
            career_key = build_career_key(student_matricola)
            res_career = LispClient.get_kv("Careers", career_key)
            career = res_career.get("value")

            if career and career.get("status") == "ENROLLED":
                # Verifica che non sia già registrato nel libretto per evitare duplicati
                passed_exams = career.get("passed_exams", [])
                course_id = appello.get("course_id", "CORSO-UNKNOWN")
                
                already_recorded = any(item.get("course_id") == course_id for item in passed_exams)
                if not already_recorded:
                    passed_exams.append({
                        "course_id": course_id,
                        "grade": grade,
                        "has_honors": has_honors,
                        "recorded_at": now
                    })
                    career["passed_exams"] = passed_exams
                    career["last_updated"] = now
                    LispClient.add_kv("Careers", career_key, career)

        return {"success": True, "data": voto_payload}

    @staticmethod
    def get_grade_history(session_id: str, student_matricola: str) -> Dict[str, Any]:
        """
        Recupera la cronologia immutabile dei voti verbalizzati per uno studente.
        """
        grade_key = build_grade_key(session_id, student_matricola)
        res = LispClient.get_key_history("Voti", grade_key)
        return {"success": True, "history": res.get("history", [])}

    @staticmethod
    def get_student_transcript(student_matricola: str) -> Dict[str, Any]:
        """
        Recupera il libretto accademico dello studente (stato carriera ed esami verbalizzati).
        """
        career_key = build_career_key(student_matricola)
        res = LispClient.get_kv("Careers", career_key)
        career = res.get("value")

        if not career:
            return {"success": False, "error": "Carriera studente non trovata", "code": "NOT_FOUND"}

        return {"success": True, "transcript": career}