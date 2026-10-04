#!/usr/bin/env bash

# Coordinate di rete richieste
HOST="160.80.216.209"
PORT="8100"

# Numero di processi worker raccomandato: (2 * CPU_CORES) + 1
WORKERS=${GUNICORN_WORKERS:-4}
TIMEOUT=${GUNICORN_TIMEOUT:-120}

echo "🚀 Avvio del Security Gateway UniChain con Gunicorn su http://${HOST}:${PORT}..."

# Esegue Gunicorn puntando all'oggetto app definito in run.py
exec gunicorn \
    --bind "${HOST}:${PORT}" \
    --workers "${WORKERS}" \
    --timeout "${TIMEOUT}" \
    --access-logfile - \
    --error-logfile - \
    "run:app"