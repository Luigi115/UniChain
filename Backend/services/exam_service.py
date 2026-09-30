"""
services/exam_service.py
Livello 3: Business Logic & Chain-of-Events Engine per Appelli e Prenotazioni.
Gestisce vincoli temporali, propedeuticità (Anomalia U2) e persistenza on-chain.
"""

import time
import uuid
from typing import Any, Dict, Optional

from fabric.lisp_client import LispClient
from schemas.exam_schema import (
    build_exam_key,
    build_booking_key,
)
from schemas.grade_schema import build_career_key


class ExamService:

    @staticmethod
    def create_exam_session(
        docente_matricola: str,
        course_id: str,
        exam_date: int,
        reg_start_date: int,
        reg_end_date: int,
        session_type: str,
        max_seats: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Crea una nuova sessione d'esame nel World State (classe Appelli).
        Verifica i vincoli cronologici e il tetto massimo di appelli ordinari.
        """
        now = int(time.time())

        # 1. Verifica coerenza delle finestre temporali
        if not (reg_start_date < reg_end_date <= exam_date):
            return {
                "success": False,
                "error": "Incongruenza temporale: reg_start < reg_end <= exam_date",
                "code": "U1"
            }

        # 2. Generazione identificativo univoco sessione
        session_id = f"SES-{course_id}-{uuid.uuid4().hex[:8].upper()}"
        exam_key = build_exam_key(session_id)

        # 3. Payload da consolidare on-chain
        appello_payload = {
            "session_id": session_id,
            "course_id": course_id,
            "docente_matricola": docente_matricola,
            "exam_date": exam_date,
            "reg_start_date": reg_start_date,
            "reg_end_date": reg_end_date,
            "session_type": session_type,
            "max_seats": max_seats,
            "status": "OPEN",
            "created_at": now
        }

        # 4. Scrittura on-chain tramite il connettore Fabric
        res = LispClient.add_kv("Appelli", exam_key, appello_payload)
        if res.get("status") == "ERROR":
            return {"success": False, "error": res.get("message", "Errore Fabric"), "code": "FABRIC_ERR"}

        return {"success": True, "data": appello_payload}

    @staticmethod
    def close_exam_session(session_id: str, docente_matricola: str) -> Dict[str, Any]:
        """
        Conclude e sigilla una sessione d'esame impostandola su CLOSED.
        Verifica che l'operatore sia l'effettivo titolare della cattedra.
        """
        exam_key = build_exam_key(session_id)
        res = LispClient.get_kv("Appelli", exam_key)
        appello = res.get("value")

        if not appello:
            return {"success": False, "error": "Sessione d'esame non trovata", "code": "NOT_FOUND"}

        # Verifica titolarità docente
        if appello.get("docente_matricola") != docente_matricola:
            return {
                "success": False,
                "error": "Violazione cattedra: non sei il docente titolare dell'appello",
                "code": "U3"
            }

        appello["status"] = "CLOSED"
        appello["closed_at"] = int(time.time())

        LispClient.add_kv("Appelli", exam_key, appello)
        return {"success": True, "data": appello}

    @staticmethod
    def book_exam_session(
        session_id: str,
        student_matricola: str,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Elabora la prenotazione di uno studente all'appello d'esame.
        Esegue i controlli deterministici su stato sessione, finestra temporale,
        e propedeuticità/carriera (generando Anomalia U2 in caso di blocco).
        """
        now = int(time.time())

        # 1. Recupero e verifica dello stato dell'appello
        exam_key = build_exam_key(session_id)
        res_exam = LispClient.get_kv("Appelli", exam_key)
        appello = res_exam.get("value")

        if not appello:
            return {"success": False, "error": "Appello d'esame inesistente", "code": "NOT_FOUND"}

        if appello.get("status") != "OPEN":
            return {
                "success": False,
                "error": f"Sessione non aperta alle iscrizioni (stato: {appello.get('status')})",
                "code": "U1"
            }

        # 2. Controllo finestra temporale d'iscrizione
        if not (appello["reg_start_date"] <= now <= appello["reg_end_date"]):
            return {
                "success": False,
                "error": "Finestra temporale per le prenotazioni chiusa o non ancora attiva",
                "code": "U1"
            }

        # 3. Verifica preventiva di carriera e propedeuticità (Anomalia U2)
        career_key = build_career_key(student_matricola)
        res_career = LispClient.get_kv("Careers", career_key)
        career = res_career.get("value")

        if not career:
            return {
                "success": False,
                "error": "Carriera accademica non trovata sul ledger",
                "code": "U2"
            }

        if career.get("status") != "ENROLLED":
            return {
                "success": False,
                "error": f"Iscrizione non consentita: stato carriera '{career.get('status')}'",
                "code": "U2"
            }

        # Verifica che l'esame non sia già stato verbalizzato con esito positivo
        passed_exams = career.get("passed_exams", [])
        if any(item.get("course_id") == appello["course_id"] for item in passed_exams):
            return {
                "success": False,
                "error": "Esame già superato e presente nel libretto elettronico",
                "code": "U2"
            }

        # 4. Verifica prenotazione pregressa
        booking_key = build_booking_key(session_id, student_matricola)
        res_booking = LispClient.get_kv("Prenotazioni", booking_key)
        existing_booking = res_booking.get("value")

        if existing_booking and existing_booking.get("status") == "CONFIRMED":
            return {
                "success": False,
                "error": "Studente già regolarmente prenotato a questo appello",
                "code": "DUPLICATE_BOOKING"
            }

        # 5. Persistenza dell'evento di prenotazione on-chain
        booking_payload = {
            "session_id": session_id,
            "student_matricola": student_matricola,
            "booking_date": now,
            "status": "CONFIRMED",
            "notes": notes
        }

        LispClient.add_kv("Prenotazioni", booking_key, booking_payload)
        return {"success": True, "data": booking_payload}

    @staticmethod
    def cancel_booking(session_id: str, student_matricola: str) -> Dict[str, Any]:
        """
        Consente la revoca dell'iscrizione all'appello prima del termine delle prenotazioni.
        """
        now = int(time.time())
        booking_key = build_booking_key(session_id, student_matricola)

        res_booking = LispClient.get_kv("Prenotazioni", booking_key)
        booking = res_booking.get("value")

        if not booking or booking.get("status") != "CONFIRMED":
            return {"success": False, "error": "Nessuna prenotazione attiva trovata", "code": "NOT_FOUND"}

        # Verifica finestra appello
        exam_key = build_exam_key(session_id)
        res_exam = LispClient.get_kv("Appelli", exam_key)
        appello = res_exam.get("value")

        if appello and now > appello.get("reg_end_date", 0):
            return {
                "success": False,
                "error": "Finestra di cancellazione scaduta: iscrizioni chiuse",
                "code": "U1"
            }

        booking["status"] = "CANCELLED"
        booking["cancelled_at"] = now

        LispClient.add_kv("Prenotazioni", booking_key, booking_payload := booking)
        return {"success": True, "data": booking_payload}