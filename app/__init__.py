"""Fabrica de la aplicacion Flask.

``create_app`` construye la aplicacion, carga la configuracion, inicializa las
extensiones, registra los blueprints y configura el manejo de errores. Este
patron facilita el uso de distintos entornos y las pruebas automatizadas.
"""

import os

from flask import Flask, render_template

from .config import CONFIG_MAP
from .extensions import csrf, db, login_manager


def create_app(config_name: str | None = None) -> Flask:
    """Crea y devuelve una instancia configurada de la aplicacion Flask.

    :param config_name: ``development``, ``testing`` o ``production``. Si no se
        indica se toma de la variable de entorno ``FLASK_ENV``.
    """
    config_name = config_name or os.environ.get("FLASK_ENV", "default")

    app = Flask(__name__)
    app.config.from_object(CONFIG_MAP.get(config_name, CONFIG_MAP["default"]))

    # Inicializacion de extensiones.
    db.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Debe iniciar sesion para acceder a esta pagina."
    login_manager.login_message_category = "warning"

    # Registro de blueprints.
    from .blueprints.auth import auth_bp
    from .blueprints.main import main_bp
    from .blueprints.orders import orders_bp
    from .blueprints.payments import payments_bp
    from .blueprints.products import products_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(products_bp, url_prefix="/products")
    app.register_blueprint(orders_bp, url_prefix="/orders")
    app.register_blueprint(payments_bp, url_prefix="/payments")

    register_error_handlers(app)

    # La base de datos se crea automaticamente si no existe (comodo en dev).
    with app.app_context():
        db.create_all()

    return app


def register_error_handlers(app: Flask) -> None:
    """Registra paginas de error personalizadas."""

    @app.errorhandler(403)
    def forbidden(error):  # pragma: no cover - renderizado simple
        return render_template("errors/error.html", code=403,
                               message="No tiene permiso para acceder a este recurso."), 403

    @app.errorhandler(404)
    def not_found(error):
        return render_template("errors/error.html", code=404,
                               message="La pagina solicitada no existe."), 404

    @app.errorhandler(500)
    def server_error(error):  # pragma: no cover
        return render_template("errors/error.html", code=500,
                               message="Ocurrio un error interno."), 500
