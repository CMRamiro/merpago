"""Punto de entrada de la aplicacion.

Ejecuta el servidor de desarrollo de Flask:

    python run.py

Para produccion se recomienda usar un servidor WSGI como gunicorn o waitress.
"""

import os

from app import create_app

app = create_app(os.environ.get("FLASK_ENV", "development"))

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
