"""Instancias de las extensiones Flask.

Se crean aqui (sin asociarlas a una app) para evitar dependencias circulares
y poder inicializarlas con el patron de fabrica de aplicaciones.
"""

from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect

#: Maneja el acceso a la base de datos mediante el ORM SQLAlchemy.
db = SQLAlchemy()

#: Gestiona las sesiones de usuario (login/logout) y el usuario actual.
login_manager = LoginManager()

#: Protege todos los formularios WTForms contra ataques CSRF.
csrf = CSRFProtect()
