#!/usr/bin/env bash

curl -X POST http://160.80.216.209:8100/api/v1/users/register \
  -H "Content-Type: application/json" \
  -d '{
    "matricola": "0386587",
    "name": "Mario",
    "surname": "Rossi",
    "email": "mario.rossi@unichain.it",
    "password": "PasswordSicura123!",
    "role": "STUDENTE"
  }'