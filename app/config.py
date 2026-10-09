"""Configuracion de la aplicacion Flask.

Se definen distintas clases de configuracion que permiten separar el entorno
de desarrollo del de produccion. La clave secreta se toma de la variable de
entorno ``SECRET_KEY`` cuando existe, de lo contrario se usa un valor por
defecto apto solo para desarrollo.
"""

import os

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


class Config:
    """Configuracion base compartida por todos los entornos."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:///" + os.path.join(BASE_DIR, "merpago.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Cookies de sesion mas seguras (evita envio en peticiones cruzadas).
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    WTF_CSRF_ENABLED = True


class DevelopmentConfig(Config):
    """Configuracion usada durante el desarrollo."""

    DEBUG = True


class TestingConfig(Config):
    """Configuracion usada por las pruebas automatizadas."""

    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


class ProductionConfig(Config):
    """Configuracion recomendada para produccion."""

    DEBUG = False


CONFIG_MAP = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
