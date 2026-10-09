"""Rutas del simulador de pago/cobro.

Permite procesar un pago sobre un pedido, registrar el intento con su resultado
y actualizar el estado del pedido cuando el pago se aprueba.
"""

from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    url_for,
)
from flask_login import current_user, login_required

from ..extensions import db
from ..forms import PaymentForm
from ..models import Order, OrderStatus, Payment, PaymentStatus
from ..services import card_last4, generate_reference, simulate_payment

payments_bp = Blueprint("payments", __name__, template_folder="../templates/payments")


def _get_owned_order_or_404(order_id: int) -> Order:
    """Recupera un pedido verificando que pertenece al usuario actual."""
    order = db.session.get(Order, order_id)
    if order is None:
        abort(404)
    if order.user_id != current_user.id:
        abort(403)
    return order


@payments_bp.route("/")
@login_required
def list_payments():
    """Lista todos los pagos/cobros del usuario actual."""
    payments = (
        Payment.query.join(Order)
        .filter(Order.user_id == current_user.id)
        .order_by(Payment.created_at.desc())
        .all()
    )
    return render_template("payments/list.html", payments=payments)


@payments_bp.route("/checkout/<int:order_id>", methods=["GET", "POST"])
@login_required
def checkout(order_id: int):
    """Muestra y procesa el simulador de pago para un pedido."""
    order = _get_owned_order_or_404(order_id)

    if order.status == OrderStatus.CANCELLED:
        flash("No se puede pagar un pedido cancelado.", "warning")
        return redirect(url_for("orders.order_detail", order_id=order.id))

    form = PaymentForm()
    if not form.is_submitted():
        # Valores por defecto al abrir el formulario.
        form.order_id.data = order.id
        form.amount.data = order.total

    if form.validate_on_submit():
        if int(form.order_id.data) != order.id:
            abort(400)

        amount = float(form.amount.data)
        result = simulate_payment(form, amount)

        payment = Payment(
            order_id=order.id,
            amount=amount,
            method=form.method.data,
            status=result.status,
            reference=generate_reference("PAY"),
            card_last4=card_last4(form.card_number.data) if form.method.data == "tarjeta" else None,
            message=result.message,
        )
        db.session.add(payment)

        # Actualiza el estado del pedido segun el resultado del pago.
        if result.status == PaymentStatus.APPROVED:
            order.status = OrderStatus.PAID
        elif result.status == PaymentStatus.REJECTED:
            order.status = OrderStatus.FAILED

        db.session.commit()

        if result.status == PaymentStatus.APPROVED:
            flash("Pago aprobado correctamente.", "success")
        elif result.status == PaymentStatus.PENDING:
            flash("El pago quedo pendiente de confirmacion.", "warning")
        else:
            flash("El pago fue rechazado.", "danger")

        return redirect(url_for("payments.receipt", payment_id=payment.id))

    return render_template("payments/checkout.html", form=form, order=order)


@payments_bp.route("/receipt/<int:payment_id>")
@login_required
def receipt(payment_id: int):
    """Muestra el comprobante de un pago."""
    payment = db.session.get(Payment, payment_id)
    if payment is None:
        abort(404)
    if payment.order.user_id != current_user.id:
        abort(403)
    return render_template("payments/receipt.html", payment=payment)
