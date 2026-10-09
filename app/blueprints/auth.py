"""Rutas de autenticacion: registro, inicio y cierre de sesion.

Se apoya en Flask-Login para gestionar la sesion del usuario.
Documentacion: https://flask-login.readthedocs.io/en/latest/
"""

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from ..extensions import db
from ..forms import LoginForm, RegistrationForm
from ..models import User

auth_bp = Blueprint("auth", __name__, template_folder="../templates/auth")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """Registra un usuario nuevo y lo deja con la sesion iniciada."""
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(name=form.name.data.strip(), email=form.email.data.lower().strip())
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash("Cuenta creada correctamente. Bienvenido.", "success")
        return redirect(url_for("main.dashboard"))

    return render_template("auth/register.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Inicia sesion de un usuario existente."""
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower().strip()).first()
        if user is None or not user.check_password(form.password.data):
            flash("Credenciales incorrectas.", "danger")
            return render_template("auth/login.html", form=form), 401

        login_user(user, remember=form.remember.data)
        flash("Sesion iniciada correctamente.", "success")

        # Redireccion segura: solo a rutas internas.
        next_page = request.args.get("next")
        if next_page and next_page.startswith("/"):
            return redirect(next_page)
        return redirect(url_for("main.dashboard"))

    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    """Cierra la sesion del usuario actual."""
    logout_user()
    flash("Ha cerrado sesion.", "info")
    return redirect(url_for("auth.login"))
