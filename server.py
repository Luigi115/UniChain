import os
import sys

# Aggiunge la cartella Backend al path di ricerca dei moduli
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "Backend"))

from Backend.app import create_app

# Istanzia l'applicazione Flask
app = create_app()

if __name__ == "__main__":
    print("🚀 Avvio del Security Gateway UniChain...")
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)