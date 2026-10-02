"""
services/exam_service.py
Livello 3: Business Logic & Chain-of-Events Engine per Appelli e Prenotazioni.
Gestisce vincoli temporali, propedeuticità (Anomalia U2), quote appelli e persistenza on-chain.
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
        academic_year: str,
        session_period: str,
        session_type: str,
        exam_date: int,
        reg_start_date: int,
        reg_end_date: int,
        max_seats: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Data Path 3.2: Crea una nuova sessione d'esame nel World State (classe Appelli).
        Verifica:
        - Coerenza cronologica delle date: reg_start_date < reg_end_date <= exam_date (Anomalia U1).
        - Quota massima: max 2 appelli ordinari e max 1 straordinario per sessione.
        """
        now = int(time.time())

        # 1. Verifica coerenza delle finestre temporali (Anomalia U1)
        if not (reg_start_date < reg_end_date <= exam_date):
            return {
                "success": False,
                "error": "Incongruenza temporale: reg_start_date < reg_end_date <= exam_date",
                "code": "U1"
            }

        # 2. Controllo Quota Appelli per Sessione (Max 2 Ordinari, Max 1 Straordinario)
        res_keys = LispClient.execute("GetKeys", "Appelli")
        appelli_keys = res_keys.get("keys", []) if isinstance(res_keys, dict) else []

        count_ordinari = 0
        count_straordinari = 0

        for key in appelli_keys:
            res_exam = LispClient.get_kv("Appelli", key)
            val = res_exam.get("value") if isinstance(res_exam, dict) else res_exam

            # Consideriamo solo appelli validi ed escludiamo quelli cancellati
            if val and isinstance(val, dict) and val.get("status") != "CANCELLED":
                if (val.get("course_id") == course_id and 
                    val.get("academic_year") == academic_year and 
                    val.get("session_period") == session_period):
                    
                    if val.get("session_type") == "ORDINARIO":
                        count_ordinari += 1
                    elif val.get("session_type") == "STRAORDINARIO":
                        count_straordinari += 1

        if session_type == "ORDINARIO" and count_ordinari >= 2:
            return {
                "success": False,
                "error": f"Superato il limite di 2 appelli ordinari per la sessione {session_period} {academic_year}",
                "code": "MAX_ORDINARY_EXCEEDED"
            }

        if session_type == "STRAORDINARIO" and count_straordinari >= 1:
            return {
                "success": False,
                "error": f"Superato il limite di 1 appello straordinario per la sessione {session_period} {academic_year}",
                "code": "MAX_EXTRAORDINARY_EXCEEDED"
            }

        # 3. Generazione identificativo univoco sessione e chiave World State
        session_id = f"SES-{course_id}-{uuid.uuid4().hex[:8].upper()}"
        exam_key = build_exam_key(session_id)

        # 4. Composizione del record da consolidare on-chain
        appello_payload = {
            "session_id": session_id,
            "course_id": course_id,
            "docente_matricola": docente_matricola,
            "academic_year": academic_year,
            "session_period": session_period,
            "session_type": session_type,
            "exam_date": exam_date,
            "reg_start_date": reg_start_date,
            "reg_end_date": reg_end_date,
            "max_seats": max_seats,
            "status": "OPEN",
            "cancelled_at": None,
            "created_at": now
        }

        # 5. Scrittura on-chain tramite il connettore Fabric
        res = LispClient.add_kv("Appelli", exam_key, appello_payload)
        if res.get("status") == "ERROR":
            return {
                "success": False, 
                "error": res.get("message", "Errore persistenza Fabric"), 
                "code": "FABRIC_ERR"
            }

        return {"success": True, "data": appello_payload}

    @staticmethod
    def cancel_exam_session(session_id: str, docente_matricola: str) -> Dict[str, Any]:
        """
        Data Path 3.3: Cancellazione o revoca di un appello d'esame.
        Verifica esclusività cattedra (Anomalia U3), stato e coerenza temporale (Anomalia U1).
        Invalida a cascata tutte le prenotazioni confermate.
        """
        now = int(time.time())
        exam_key = build_exam_key(session_id)

        # 1. Recupero appello dal World State
        res_exam = LispClient.get_kv("Appelli", exam_key)
        appello = res_exam.get("value") if isinstance(res_exam, dict) and "value" in res_exam else res_exam

        if not appello:
            return {"success": False, "error": "Appello d'esame inesistente", "code": "NOT_FOUND"}

        # 2. Verifica esclusività della cattedra (Anomalia U3)
        if appello.get("docente_matricola") != docente_matricola:
            return {
                "success": False,
                "error": "Violazione cattedra: non sei il docente titolare dell'insegnamento",
                "code": "U3"
            }

        # 3. Verifica stato operativo (solo appelli OPEN sono revocabili)
        if appello.get("status") != "OPEN":
            return {
                "success": False,
                "error": f"Impossibile cancellare un appello in stato '{appello.get('status')}'",
                "code": "INVALID_STATUS"
            }

        # 4. Verifica coerenza temporale: non cancellabile se l'esame è già avvenuto (Anomalia U1)
        if now > appello.get("exam_date", 0):
            return {
                "success": False,
                "error": "Impossibile cancellare un appello con data d'esame già trascorsa",
                "code": "U1"
            }

        # 5. Invalidazione a cascata di tutte le prenotazioni attive
        res_keys = LispClient.execute("GetKeys", "Prenotazioni")
        booking_keys = res_keys.get("keys", []) if isinstance(res_keys, dict) else []
        prefix = f"prenotazione:{session_id}:"

        for b_key in booking_keys:
            if b_key.startswith(prefix):
                b_res = LispClient.get_kv("Prenotazioni", b_key)
                b_data = b_res.get("value") if isinstance(b_res, dict) and "value" in b_res else b_res
                if b_data and isinstance(b_data, dict) and b_data.get("status") == "CONFIRMED":
                    b_data["status"] = "CANCELLED"
                    b_data["cancelled_reason"] = "EXAM_SESSION_CANCELLED_BY_TEACHER"
                    b_data["cancelled_at"] = now
                    LispClient.add_kv("Prenotazioni", b_key, b_data)

        # 6. Aggiornamento dello stato dell'appello sul World State
        appello["status"] = "CANCELLED"
        appello["cancelled_at"] = now
        res_add = LispClient.add_kv("Appelli", exam_key, appello)

        if res_add.get("status") == "ERROR":
            return {
                "success": False,
                "error": res_add.get("message", "Errore persistenza Fabric"),
                "code": "FABRIC_ERR"
            }

        return {"success": True, "data": appello}

    @staticmethod
    def close_exam_session(session_id: str, docente_matricola: str) -> Dict[str, Any]:
        """
        Conclude e sigilla una sessione d'esame impostandola su CLOSED.
        Verifica che l'operatore sia l'effettivo titolare della cattedra (Anomalia U3).
        """
        exam_key = build_exam_key(session_id)
        res = LispClient.get_kv("Appelli", exam_key)
        appello = res.get("value") if isinstance(res, dict) and "value" in res else res

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
        tetto posti e propedeuticità/carriera (generando Anomalia U2 in caso di blocco).
        """
        now = int(time.time())

        # 1. Recupero e verifica dello stato dell'appello
        exam_key = build_exam_key(session_id)
        res_exam = LispClient.get_kv("Appelli", exam_key)
        appello = res_exam.get("value") if isinstance(res_exam, dict) and "value" in res_exam else res_exam

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

        # 3. Controllo capienza massima (max_seats)
        max_seats = appello.get("max_seats")
        if max_seats is not None:
            res_keys = LispClient.execute("GetKeys", "Prenotazioni")
            all_b_keys = res_keys.get("keys", []) if isinstance(res_keys, dict) else []
            prefix = f"prenotazione:{session_id}:"
            confirmed_count = 0

            for b_key in all_b_keys:
                if b_key.startswith(prefix):
                    b_res = LispClient.get_kv("Prenotazioni", b_key)
                    b_val = b_res.get("value") if isinstance(b_res, dict) and "value" in b_res else b_res
                    if b_val and isinstance(b_val, dict) and b_val.get("status") == "CONFIRMED":
                        confirmed_count += 1

            if confirmed_count >= max_seats:
                return {
                    "success": False,
                    "error": f"Posti disponibili esauriti per questo appello (limite: {max_seats})",
                    "code": "SEATS_FULL"
                }

        # 4. Verifica preventiva di carriera e propedeuticità (Anomalia U2)
        career_key = build_career_key(student_matricola)
        res_career = LispClient.get_kv("Careers", career_key)
        career = res_career.get("value") if isinstance(res_career, dict) and "value" in res_career else res_career

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

        # 5. Verifica prenotazione pregressa
        booking_key = build_booking_key(session_id, student_matricola)
        res_booking = LispClient.get_kv("Prenotazioni", booking_key)
        existing_booking = res_booking.get("value") if isinstance(res_booking, dict) and "value" in res_booking else res_booking

        if existing_booking and existing_booking.get("status") == "CONFIRMED":
            return {
                "success": False,
                "error": "Studente già regolarmente prenotato a questo appello",
                "code": "DUPLICATE_BOOKING"
            }

        # 6. Persistenza dell'evento di prenotazione on-chain
        booking_payload = {
            "session_id": session_id,
            "student_matricola": student_matricola,
            "booking_date": now,
            "status": "CONFIRMED",
            "cancelled_reason": None,
            "cancelled_at": None,
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
        booking = res_booking.get("value") if isinstance(res_booking, dict) and "value" in res_booking else res_booking

        if not booking or booking.get("status") != "CONFIRMED":
            return {"success": False, "error": "Nessuna prenotazione attiva trovata", "code": "NOT_FOUND"}

        # Verifica finestra appello
        exam_key = build_exam_key(session_id)
        res_exam = LispClient.get_kv("Appelli", exam_key)
        appello = res_exam.get("value") if isinstance(res_exam, dict) and "value" in res_exam else res_exam

        if appello and now > appello.get("reg_end_date", 0):
            return {
                "success": False,
                "error": "Finestra di cancellazione scaduta: iscrizioni chiuse",
                "code": "U1"
            }

        booking["status"] = "CANCELLED"
        booking["cancelled_at"] = now
        booking["cancelled_reason"] = "STUDENT_SELF_CANCELLATION"

        LispClient.add_kv("Prenotazioni", booking_key, booking)
        return {"success": True, "data": booking}