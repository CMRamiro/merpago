"""Rutas del sistema de pedidos y cobros.

Un pedido se compone de una o varias lineas (:class:`OrderItem`) seleccionadas
a partir de los productos del usuario. El estado del pedido se actualiza mas
tarde desde el simulador de pago/cobro.
"""

from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required

from ..extensions import db
from ..forms import OrderForm
from ..models import Order, OrderItem, OrderStatus, Product
from ..services import generate_reference

orders_bp = Blueprint("orders", __name__, template_folder="../templates/orders")


def _get_owned_order_or_404(order_id: int) -> Order:
    """Recupera un pedido verificando que pertenece al usuario actual."""
    order = db.session.get(Order, order_id)
    if order is None:
        abort(404)
    if order.user_id != current_user.id:
        abort(403)
    return order


@orders_bp.route("/")
@login_required
def list_orders():
    """Lista los pedidos del usuario actual."""
    orders = (
        Order.query.filter_by(user_id=current_user.id)
        .order_by(Order.created_at.desc())
        .all()
    )
    return render_template("orders/list.html", orders=orders)


@orders_bp.route("/new", methods=["GET", "POST"])
@login_required
def create_order():
    """Crea un pedido a partir de los productos seleccionados."""
    form = OrderForm()
    products = (
        Product.query.filter_by(owner_id=current_user.id)
        .order_by(Product.name.asc())
        .all()
    )

    if form.validate_on_submit():
        selected = []
        # Las lineas se envian como qty_<product_id> para cada producto marcado.
        for product in products:
            raw_qty = request.form.get(f"qty_{product.id}", "").strip()
            if not raw_qty:
                continue
            try:
                quantity = int(raw_qty)
            except ValueError:
                continue
            if quantity > 0:
                selected.append((product, quantity))

        if not selected:
            flash("Seleccione al menos un producto e indique la cantidad.", "warning")
            return render_template("orders/create.html", form=form, products=products)

        # Validacion de stock.
        for product, quantity in selected:
            if quantity > product.stock:
                flash(
                    f"Stock insuficiente para '{product.name}' "
                    f"(disponible: {product.stock}).",
                    "danger",
                )
                return render_template("orders/create.html", form=form, products=products)

        order = Order(
            reference=generate_reference("ORD"),
            customer_name=form.customer_name.data.strip(),
            order_type=form.order_type.data,
            notes=(form.notes.data or "").strip(),
            status=OrderStatus.PENDING,
            user_id=current_user.id,
        )
        db.session.add(order)
        db.session.flush()  # asigna order.id para las lineas

        for product, quantity in selected:
            db.session.add(
                OrderItem(
                    order_id=order.id,
                    product_id=product.id,
                    quantity=quantity,
                    unit_price=product.price,
                )
            )

        db.session.commit()
        flash("Pedido creado correctamente.", "success")
        return redirect(url_for("orders.order_detail", order_id=order.id))

    return render_template("orders/create.html", form=form, products=products)


@orders_bp.route("/<int:order_id>")
@login_required
def order_detail(order_id: int):
    """Muestra el detalle de un pedido y sus pagos."""
    order = _get_owned_order_or_404(order_id)
    return render_template("orders/detail.html", order=order)


@orders_bp.route("/<int:order_id>/cancel", methods=["POST"])
@login_required
def cancel_order(order_id: int):
    """Cancela un pedido que aun este pendiente."""
    order = _get_owned_order_or_404(order_id)
    if order.status != OrderStatus.PENDING:
        flash("Solo se pueden cancelar pedidos pendientes.", "warning")
    else:
        order.status = OrderStatus.CANCELLED
        db.session.commit()
        flash("Pedido cancelado.", "info")
    return redirect(url_for("orders.order_detail", order_id=order.id))
