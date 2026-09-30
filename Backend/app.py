from flask import Flask
from config import Config
from routes import register_routes
from security import init_audit_middleware

def create_app():
    """Crea e configura l'istanza principale dell'applicazione Flask (Security Gateway)."""
    app = Flask(__name__)

    # 1. Carica le variabili d'ambiente in modo sicuro
    app.config.from_object(Config)

    # 2. Registra tutti gli endpoint REST (Livello 5)
    register_routes(app)

    # 3. Attiva l'intercettore per il logging crittografico (Livello 4)
    init_audit_middleware(app)

    return app