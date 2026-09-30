"""
services/admin_service.py
Livello 3: Business Logic & Chain-of-Events Engine per la Segreteria Studenti.
Gestisce stato utenze, passaggi di corso, rinunce e proclamazione di laurea (Anomalia U6).
"""

import time
from typing import Any, Dict, Optional

from fabric.lisp_client import LispClient
from schemas.user_schema import build_user_key
from schemas.grade_schema import build_career_key


class AdminService:

    @staticmethod
    def update_user_status(matricola: str, new_status: str) -> Dict[str, Any]:
        """
        Aggiorna lo stato operativo di un account utente (ACTIVE | SUSPENDED).
        """
        now = int(time.time())
        user_key = build_user_key(matricola)

        user_res = LispClient.get_kv("Users", user_key)
        user_record = user_res.get("value")

        if not user_record:
            return {"success": False, "error": f"Utente {matricola} non trovato", "code": "NOT_FOUND"}

        user_record["status"] = new_status
        user_record["updated_at"] = now

        res = LispClient.add_kv("Users", user_key, user_record)
        if res.get("status") == "ERROR":
            return {"success": False, "error": res.get("message", "Errore Fabric"), "code": "FABRIC_ERR"}

        return {"success": True, "data": user_record}

    @staticmethod
    def approve_course_transfer(
        matricola: str,
        new_degree_id: str,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Convalida il passaggio di corso di uno studente verso un nuovo ordinamento didattico.
        """
        now = int(time.time())
        career_key = build_career_key(matricola)

        career_res = LispClient.get_kv("Careers", career_key)
        career = career_res.get("value")

        if not career:
            return {"success": False, "error": f"Carriera per la matricola {matricola} non trovata", "code": "NOT_FOUND"}

        if career.get("status") in ["WITHDRAWN", "GRADUATED"]:
            return {
                "success": False,
                "error": f"Impossibile trasferire una carriera chiusa (stato: {career.get('status')})",
                "code": "U6"
            }

        career["degree_id"] = new_degree_id
        career["status"] = "ENROLLED"
        career["last_updated"] = now
        if notes:
            career["transfer_notes"] = notes

        LispClient.add_kv("Careers", career_key, career)
        return {"success": True, "data": career}

    @staticmethod
    def approve_withdrawal(matricola: str, reason: str) -> Dict[str, Any]:
        """
        Formalizza la rinuncia agli studi: imposta la carriera su WITHDRAWN
        e contestualmente disattiva l'utenza (status: SUSPENDED) per precludere nuove operazioni.
        """
        now = int(time.time())
        career_key = build_career_key(matricola)
        user_key = build_user_key(matricola)

        career_res = LispClient.get_kv("Careers", career_key)
        career = career_res.get("value")

        if not career:
            return {"success": False, "error": f"Carriera per la matricola {matricola} non trovata", "code": "NOT_FOUND"}

        if career.get("status") in ["WITHDRAWN", "GRADUATED"]:
            return {
                "success": False,
                "error": f"La carriera risulta già conclusa (stato: {career.get('status')})",
                "code": "INVALID_STATE"
            }

        # 1. Aggiornamento stato carriera on-chain
        career["status"] = "WITHDRAWN"
        career["withdrawal_reason"] = reason
        career["last_updated"] = now
        LispClient.add_kv("Careers", career_key, career)

        # 2. Sospensione utenza collegata per precludere accessi futuri
        user_res = LispClient.get_kv("Users", user_key)
        user_record = user_res.get("value")
        if user_record:
            user_record["status"] = "SUSPENDED"
            user_record["updated_at"] = now
            LispClient.add_kv("Users", user_key, user_record)

        return {"success": True, "data": career}

    @staticmethod
    def approve_graduation(
        matricola: str,
        final_grade: int,
        has_honors: bool
    ) -> Dict[str, Any]:
        """
        Valida i requisiti di carriera e proclama la laurea dello studente.
        Se i CFU o gli esami non risultano completati, solleva l'Anomalia U6.
        """
        now = int(time.time())
        career_key = build_career_key(matricola)

        career_res = LispClient.get_kv("Careers", career_key)
        career = career_res.get("value")

        if not career:
            return {"success": False, "error": f"Carriera per la matricola {matricola} non trovata", "code": "NOT_FOUND"}

        if career.get("status") == "GRADUATED":
            return {"success": False, "error": "Studente già laureato", "code": "ALREADY_GRADUATED"}

        if career.get("status") == "WITHDRAWN":
            return {"success": False, "error": "Impossibile laureare uno studente rinunciatario", "code": "U6"}

        # ----------------------------------------------------------------------
        # Controllo Determinismo Accademico: Integrità dei CFU (Anomalia U6)
        # ----------------------------------------------------------------------
        cfu_total_required = career.get("cfu_total", 180)
        passed_exams = career.get("passed_exams", [])

        # Stima crediti: per convenzione o conteggio esami superati
        # Calcolo CFU effettivi: ogni esame verbalizzato corrisponde a CFU (o campo cfu_acquired)
        cfu_acquired = career.get("cfu_acquired")
        if cfu_acquired is None:
            # Fallback se non esplicitato: ogni esame vale tipicamente 6 CFU o si conta la lista
            cfu_acquired = len(passed_exams) * 6

        if cfu_acquired < cfu_total_required:
            return {
                "success": False,
                "error": f"Incongruenza di carriera: acquisiti {cfu_acquired}/{cfu_total_required} CFU necessari",
                "code": "U6"
            }

        # Consolidamento Proclamazione di Laurea on-chain
        career["status"] = "GRADUATED"
        career["final_grade"] = final_grade
        career["has_honors"] = has_honors
        career["graduated_at"] = now
        career["last_updated"] = now

        LispClient.add_kv("Careers", career_key, career)
        return {"success": True, "data": career}