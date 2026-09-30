"""
routes package
Livello 5: RESTful API Controllers & Routing Layer per UniChain.
Registra centralmente tutti i Blueprint dell'applicazione Flask.
"""

from flask import Flask
from routes.auth_routes import auth_bp
from routes.student_routes import student_bp
from routes.docente_routes import docente_bp
from routes.admin_routes import admin_bp


def register_routes(app: Flask) -> None:
    """Registra tutti i Blueprint dei controller nel server Flask."""
    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(docente_bp)
    app.register_blueprint(admin_bp)


__all__ = [
    "auth_bp",
    "student_bp",
    "docente_bp",
    "admin_bp",
    "register_routes",
]