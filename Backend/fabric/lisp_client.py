import json
import socket
from typing import Any, Dict, Optional

# Configurazione del "telefono" verso il Client Lisp nella Restricted Zone
LISP_HOST = "160.80.216.209"  # L'IP pubblico del server indicato dal collega
LISP_PORT = 9999              # La porta di ascolto (verifica col collega se è 9999 o un'altra!)

class LispClient:
    """
    Adapter di Livello 1 per dialogare con il Client Lisp.
    Il suo unico scopo è creare la 'busta' (envelope) e spedirla.
    """

    @staticmethod
    def _esegui_comando(cmd: str, class_name: str, key: Optional[str] = None, value: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        # 1. Costruiamo l'envelope JSON richiesto dal Client Lisp
        envelope = {
            "cmd": cmd,
            "class": class_name
        }
        if key is not None:
            envelope["key"] = key
        if value is not None:
            envelope["value"] = value

        payload = json.dumps(envelope)

        # 2. Apriamo la comunicazione TCP (il socket)
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5.0)  # Mettiamo un limite di tempo per evitare blocchi
                s.connect((LISP_HOST, LISP_PORT))
                s.sendall(payload.encode("utf-8"))
                
                # 3. Riceviamo e traduciamo la risposta
                raw_response = s.recv(8192)
                if not raw_response:
                    return {"status": "ERROR", "message": "Nessuna risposta ricevuta dal ledger."}
                
                return json.loads(raw_response.decode("utf-8"))
                
        except Exception as e:
            # Se la blockchain è irraggiungibile, gestiamo l'errore in modo pulito
            return {"status": "ERROR", "message": f"Errore di comunicazione Fabric: {str(e)}"}

    # --- Implementazione delle 4 Primitive Architetturali ---

    @classmethod
    def add_kv(cls, class_name: str, key: str, value: Dict[str, Any]) -> Dict[str, Any]:
        """Scrive o sovrascrive un record sul World State."""
        return cls._esegui_comando("AddKV", class_name, key=key, value=value)

    @classmethod
    def get_kv(cls, class_name: str, key: str) -> Optional[Dict[str, Any]]:
        """Recupera lo stato corrente di un record."""
        res = cls._esegui_comando("GetKV", class_name, key=key)
        if res.get("status") == "SUCCESS" and "value" in res:
            return res["value"]
        return None

    @classmethod
    def get_key_history(cls, class_name: str, key: str) -> Dict[str, Any]:
        """Estrae la catena storica immutabile delle transazioni di una chiave."""
        return cls._esegui_comando("GetKeyHistory", class_name, key=key)

    @classmethod
    def del_kv(cls, class_name: str, key: str) -> Dict[str, Any]:
        """Applica una cancellazione logica (tombstone) sul record."""
        return cls._esegui_comando("DelKV", class_name, key=key)
    '''
    # --- BLOCCO DI TEST ---
if __name__ == "__main__":
    print(f"Tentativo di connessione al Client Lisp su {LISP_HOST}:{LISP_PORT}...")
    
    # Invia un comando innocuo: prova a leggere una chiave che (probabilmente) non esiste
    risposta = LispClient.get_kv(class_name="TestConn", key="ping_123")
    
    print("\nRisposta ricevuta:")
    print(json.dumps(risposta, indent=2))
    '''