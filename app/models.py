"""Modelos de datos de la aplicacion.

Se definen las entidades principales del simulador de pago/cobro y sus
relaciones usando SQLAlchemy:

* :class:`User`      -> usuarios registrados (vendedores/compradores).
* :class:`Product`   -> articulos que un usuario pone a la venta.
* :class:`Order`     -> pedido formado por uno o varios productos.
* :class:`OrderItem` -> linea de un pedido (producto + cantidad).
* :class:`Payment`   -> intento de pago/cobro asociado a un pedido.

Un usuario tiene varios pedidos; un pedido tiene varias lineas y varios pagos.
"""

from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db, login_manager


def utcnow() -> datetime:
    """Devuelve la fecha/hora actual en UTC (con zona horaria)."""
    return datetime.now(timezone.utc)


class TimestampMixin:
    """Anade marcas de tiempo de creacion y ultima modificacion."""

    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=utcnow, onupdate=utcnow, nullable=False
    )


class User(UserMixin, db.Model):
    """Usuario de la aplicacion.

    Implementa ``UserMixin`` para integrarse con Flask-Login. La contrasena
    nunca se almacena en texto plano: se guarda su hash mediante Werkzeug.
    """

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    # Relaciones
    products = db.relationship(
        "Product", back_populates="owner", cascade="all, delete-orphan"
    )
    orders = db.relationship("Order", back_populates="user")

    def set_password(self, password: str) -> None:
        """Guarda el hash seguro de ``password``."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Devuelve ``True`` si ``password`` coincide con el hash guardado."""
        return check_password_hash(self.password_hash, password)

    def __repr__(self) -> str:  # pragma: no cover - solo para depuracion
        return f"<User {self.email}>"


@login_manager.user_loader
def load_user(user_id: str):
    """Callback que usa Flask-Login para recuperar el usuario de la sesion."""
    return db.session.get(User, int(user_id))


class Product(TimestampMixin, db.Model):
    """Producto que un usuario pone a disposicion para la venta/cobro."""

    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, default="")
    price = db.Column(db.Numeric(10, 2), nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=0)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    owner = db.relationship("User", back_populates="products")

    @property
    def price_float(self) -> float:
        """Devuelve el precio como ``float`` para los formularios."""
        return float(self.price) if self.price is not None else 0.0

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Product {self.name}>"


class OrderStatus:
    """Estados posibles de un pedido."""

    PENDING = "pendiente"
    PAID = "pagado"
    FAILED = "fallido"
    CANCELLED = "cancelado"

    ALL = (PENDING, PAID, FAILED, CANCELLED)


class Order(TimestampMixin, db.Model):
    """Pedido o cobro asociado a un usuario.

    ``order_type`` distingue entre un pago (el usuario paga) y un cobro
    (el usuario genera un cobro a un cliente). El estado se actualiza cuando
    el simulador procesa el pago.
    """

    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(40), unique=True, nullable=False, index=True)
    customer_name = db.Column(db.String(150), nullable=False)
    order_type = db.Column(db.String(10), nullable=False, default="pago")
    status = db.Column(db.String(20), nullable=False, default=OrderStatus.PENDING)
    notes = db.Column(db.Text, default="")
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    user = db.relationship("User", back_populates="orders")
    items = db.relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
    )
    payments = db.relationship(
        "Payment", back_populates="order", cascade="all, delete-orphan"
    )

    @property
    def total(self) -> float:
        """Importe total del pedido sumando todas sus lineas."""
        return round(sum(item.subtotal for item in self.items), 2)

    @property
    def amount_paid(self) -> float:
        """Suma de los pagos aprobados asociados al pedido."""
        return round(
            sum(
                float(p.amount)
                for p in self.payments
                if p.status == PaymentStatus.APPROVED
            ),
            2,
        )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Order {self.reference} {self.status}>"


class OrderItem(db.Model):
    """Linea de pedido: un producto con su cantidad y precio congelado."""

    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)

    order = db.relationship("Order", back_populates="items")
    product = db.relationship("Product")

    @property
    def subtotal(self) -> float:
        """Importe de la linea (precio unitario por cantidad)."""
        return round(float(self.unit_price) * self.quantity, 2)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<OrderItem {self.product_id} x{self.quantity}>"


class PaymentStatus:
    """Estados posibles de un pago."""

    APPROVED = "aprobado"
    REJECTED = "rechazado"
    PENDING = "pendiente"

    ALL = (APPROVED, REJECTED, PENDING)


class Payment(db.Model):
    """Intento de pago/cobro sobre un pedido.

    Guarda el metodo usado, el resultado de la simulacion y datos no sensibles
    de la tarjeta (solo los ultimos cuatro digitos, nunca el numero completo).
    """

    __tablename__ = "payments"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    method = db.Column(db.String(20), nullable=False, default="tarjeta")
    status = db.Column(db.String(20), nullable=False, default=PaymentStatus.PENDING)
    reference = db.Column(db.String(40), nullable=False, index=True)
    card_last4 = db.Column(db.String(4))
    message = db.Column(db.String(255), default="")
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    order = db.relationship("Order", back_populates="payments")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Payment {self.reference} {self.status}>"
