import time
import bcrypt
import json
from fabric.lisp_client import LispClient

def bootstrap():
    print("=" * 60)
    print("⏳ TENTATIVO DI SCRITTURA SULLA BLOCKCHAIN (AddKV)...")
    print("=" * 60)

    # 1. Calcolo hash bcrypt per la password della Segreteria
    password_in_chiaro = "AdminSegreta2026!"
    salt = bcrypt.gensalt()
    pwd_hash = bcrypt.hashpw(password_in_chiaro.encode("utf-8"), salt).decode("utf-8")

    now = int(time.time())

    # 2. Struttura del record utente Segreteria
    admin_payload = {
        "matricola": "0000001",
        "roles": ["SEGRETERIA"],
        "name": "Responsabile",
        "surname": "Segreteria",
        "email": "segreteria@unichain.it",
        "password_hash": pwd_hash,
        "status": "ACTIVE",
        "created_at": now,
        "updated_at": now
    }

    # 3. Invio AddKV alla blockchain tramite LispClient
    try:
        print("-> Invio comando AddKV per user:0000001...")
        risposta_scrittura = LispClient.add_kv("Users", "user:0000001", admin_payload)
        print("-> Risposta grezza dal server:", json.dumps(risposta_scrittura, indent=2))

        # 4. Verifica immediata con GetKV
        print("\n-> Eseguo GetKV per verificare la persistenza...")
        utente_letto = LispClient.get_kv("Users", "user:0000001")
        print("-> Dato recuperato:", json.dumps(utente_letto, indent=2))

        if utente_letto and utente_letto.get("matricola") == "0000001":
            print("\n🎉 SUCCESSO! L'utente Segreteria esiste sulla blockchain!")
            print("Credenziali attive:")
            print("  Matricola: 0000001")
            print("  Password:  AdminSegreta2026!")
        else:
            print("\n❌ Errore: il record non è stato trovato o è vuoto.")

    except Exception as e:
        print(f"\n❌ ERRORE DI CONNESSIONE: {e}")

if __name__ == "__main__":
    bootstrap()