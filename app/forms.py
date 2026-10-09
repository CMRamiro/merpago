"""Formularios de la aplicacion construidos con Flask-WTF.

Cada formulario declara sus campos y validadores. Flask-WTF se encarga de
generar el token CSRF y de validar los datos enviados por el usuario.
"""

from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    DecimalField,
    HiddenField,
    IntegerField,
    PasswordField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import (
    DataRequired,
    Email,
    EqualTo,
    Length,
    NumberRange,
    Optional,
    ValidationError,
)

from .models import User


class RegistrationForm(FlaskForm):
    """Formulario para crear una cuenta nueva."""

    name = StringField("Nombre completo", validators=[DataRequired(), Length(max=120)])
    email = StringField(
        "Correo electronico", validators=[DataRequired(), Email(), Length(max=255)]
    )
    password = PasswordField(
        "Contrasena",
        validators=[DataRequired(), Length(min=6, message="Minimo 6 caracteres.")],
    )
    confirm_password = PasswordField(
        "Confirmar contrasena",
        validators=[DataRequired(), EqualTo("password", message="Las contrasenas no coinciden.")],
    )
    submit = SubmitField("Crear cuenta")

    def validate_email(self, field):
        """Impide registrar dos usuarios con el mismo correo."""
        if User.query.filter_by(email=field.data.lower().strip()).first():
            raise ValidationError("Ya existe una cuenta con este correo.")


class LoginForm(FlaskForm):
    """Formulario de inicio de sesion."""

    email = StringField(
        "Correo electronico", validators=[DataRequired(), Email(), Length(max=255)]
    )
    password = PasswordField("Contrasena", validators=[DataRequired()])
    remember = BooleanField("Recordarme")
    submit = SubmitField("Entrar")


class ProductForm(FlaskForm):
    """Formulario para crear o editar un producto."""

    name = StringField("Nombre del producto", validators=[DataRequired(), Length(max=150)])
    description = TextAreaField("Descripcion", validators=[Optional(), Length(max=2000)])
    price = DecimalField(
        "Precio unitario",
        places=2,
        validators=[DataRequired(), NumberRange(min=0.01, message="El precio debe ser mayor que cero.")],
    )
    stock = IntegerField(
        "Stock disponible",
        validators=[DataRequired(), NumberRange(min=0, message="El stock no puede ser negativo.")],
    )
    submit = SubmitField("Guardar producto")


class OrderForm(FlaskForm):
    """Formulario para crear un pedido o cobro."""

    customer_name = StringField(
        "Nombre del cliente", validators=[DataRequired(), Length(max=150)]
    )
    order_type = SelectField(
        "Tipo de operacion",
        choices=[("pago", "Pago (el cliente paga)"), ("cobro", "Cobro (generar cobro)")],
        validators=[DataRequired()],
    )
    notes = TextAreaField("Notas", validators=[Optional(), Length(max=2000)])
    submit = SubmitField("Crear pedido")


class PaymentForm(FlaskForm):
    """Formulario del simulador de pago/cobro."""

    order_id = HiddenField(validators=[DataRequired()])
    amount = DecimalField(
        "Importe a procesar",
        places=2,
        validators=[DataRequired(), NumberRange(min=0.01, message="El importe debe ser mayor que cero.")],
    )
    method = SelectField(
        "Metodo de pago",
        choices=[
            ("tarjeta", "Tarjeta de credito/debito"),
            ("transferencia", "Transferencia bancaria"),
            ("efectivo", "Efectivo"),
        ],
        validators=[DataRequired()],
    )
    # Datos de tarjeta (solo se simulan, nunca se persisten completos).
    card_number = StringField("Numero de tarjeta", validators=[Optional(), Length(max=19)])
    card_holder = StringField("Titular de la tarjeta", validators=[Optional(), Length(max=120)])
    card_expiry = StringField("Expiracion (MM/AA)", validators=[Optional(), Length(max=5)])
    card_cvv = StringField("CVV", validators=[Optional(), Length(max=4)])
    force_result = SelectField(
        "Resultado a simular",
        choices=[
            ("auto", "Automatico (segun reglas)"),
            ("approve", "Forzar aprobado"),
            ("reject", "Forzar rechazado"),
        ],
        default="auto",
    )
    submit = SubmitField("Procesar pago")
