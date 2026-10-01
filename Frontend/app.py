from flask import Flask, render_template, request, redirect, url_for, flash
import requests

app = Flask(__name__)
app.secret_key = "unichain_secret_key"  # Necessaria se userete i messaggi flash di Flask

# ==========================================
# CONFIGURAZIONE ENDPOINT BLOCKCHAIN
# ==========================================
# Questo è l'indirizzo del server API attivato tramite Docker (riga 59 del README)
BLOCKCHAIN_URL = "http://localhost:9999/api"


# ==========================================
# FUNZIONI DI INTERAZIONE CON LA BLOCKCHAIN
# ==========================================

def invia_a_blockchain(comando, classe, chiave, valore=None):
    """
    Funzione di utilità per inviare comandi alla blockchain del professore.
    Mappa i comandi visti nel README (GetKeys, AddKV, ecc.)
    """
    # Prepariamo il payload JSON standard richiesto dal server
    payload = {
        "cmd": comando,
        "class": classe,
        "key": chiave if isinstance(chiave, list) else [chiave]
    }
    
    # Se il comando richiede l'inserimento di un valore (es. AddKV), lo aggiungiamo
    if valore is not None:
        payload["val"] = valore

    try:
        # Inviamo la richiesta POST HTTP al server sulla porta 9999
        response = requests.post(BLOCKCHAIN_URL, json=payload)
        
        # Se la risposta è corretta (status 200), restituiamo il JSON
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Errore del server Blockchain: {response.status_code}")
            return None
    except requests.exceptions.ConnectionError:
        print("Errore: Impossibile connettersi al server API della Blockchain. È attivo?")
        return None


# ==========================================
# ROTTE DI FLASK (FRONT-END)
# ==========================================

@app.route("/")
def home():
    return render_template("dashboard.html")


@app.route("/login")
def login():
    return render_template("login.html")


@app.route("/universita")
def universita():
    return render_template("universita.html")


# ------------------------------------------
# ESEMPIO: Rotta per registrare uno studente (Azione della Segreteria)
# ------------------------------------------
@app.route("/segreteria/registra_studente", methods=["POST"])
def registra_studente():
    # 1. Recuperiamo i dati inviati dal form HTML
    matricola = request.form.get("matricola")
    nome_cognome = request.form.get("nome")
    
    # 2. Prepariamo i dati da salvare nel "Value" della blockchain
    dati_studente = {
        "nominativo": nome_cognome,
        "stato_carriera": "Attivo"
    }
    
    # 3. Chiamiamo la funzione che scrive sulla Blockchain (AddKV)
    # Usiamo "UTENTE" come classe e la matricola come chiave (es. ["0386587"])
    risultato = invia_a_blockchain(
        comando="AddKV", 
        classe="UTENTE", 
        chiave=[matricola], 
        valore=dati_studente
    )
    
    if risultato:
        return "Studente registrato con successo sulla Blockchain!"
    else:
        return "Errore durante la registrazione sulla Blockchain", 500
    
@app.route('/homepage-studente')
def home_studente():
    # Questo dice a Flask di prendere il file homepagestudente.html dentro la cartella 'templates'
    return render_template('homepagestudente.html')

@app.route('/homepage-studente/esami')
def visualizza_esami():
    # Carica la nuova pagina degli esami che abbiamo appena creato
    return render_template('esami.html')

@app.route('/homepage-studente/prenotazioni')
def pagina_prenotazioni():
    # Dice a Flask di mostrare la pagina appena creata con l'elenco degli esami dummy
    return render_template('prenota_esame.html')



# EAVVIO SERVER FLASK
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)