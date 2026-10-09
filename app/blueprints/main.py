"""Rutas generales: pagina de inicio y panel de control (dashboard)."""

from flask import Blueprint, render_template
from flask_login import current_user, login_required

from ..models import Order, OrderStatus, Payment

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    """Pagina publica de bienvenida."""
    return render_template("index.html")


@main_bp.route("/dashboard")
@login_required
def dashboard():
    """Panel con un resumen de la actividad del usuario actual."""
    orders = (
        Order.query.filter_by(user_id=current_user.id)
        .order_by(Order.created_at.desc())
        .all()
    )
    total_orders = len(orders)
    total_amount = round(sum(o.total for o in orders), 2)
    paid_orders = sum(1 for o in orders if o.status == OrderStatus.PAID)
    pending_orders = sum(1 for o in orders if o.status == OrderStatus.PENDING)

    recent_payments = (
        Payment.query.join(Order)
        .filter(Order.user_id == current_user.id)
        .order_by(Payment.created_at.desc())
        .limit(5)
        .all()
    )

    return render_template(
        "dashboard.html",
        orders=orders[:5],
        total_orders=total_orders,
        total_amount=total_amount,
        paid_orders=paid_orders,
        pending_orders=pending_orders,
        recent_payments=recent_payments,
    )
