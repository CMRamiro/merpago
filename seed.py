"""Script opcional para poblar la base de datos con datos de ejemplo.

Uso:

    python seed.py

Crea un usuario de demostracion (demo@merpago.com / demo1234) con varios
productos y un pedido de ejemplo listo para probar el simulador de pago.
"""

from app import create_app
from app.extensions import db
from app.models import Order, OrderItem, OrderStatus, Product, User
from app.services import generate_reference

DEMO_EMAIL = "demo@merpago.com"
DEMO_PASSWORD = "demo1234"


def seed() -> None:
    """Crea los datos de ejemplo si el usuario demo no existe."""
    app = create_app()
    with app.app_context():
        db.create_all()

        if User.query.filter_by(email=DEMO_EMAIL).first():
            print("El usuario demo ya existe. No se hace nada.")
            return

        user = User(name="Usuario Demo", email=DEMO_EMAIL)
        user.set_password(DEMO_PASSWORD)
        db.session.add(user)
        db.session.flush()

        products = [
            Product(name="Plan Basico", description="Suscripcion mensual basica",
                    price=19.99, stock=100, owner_id=user.id),
            Product(name="Plan Pro", description="Suscripcion mensual profesional",
                    price=49.99, stock=50, owner_id=user.id),
            Product(name="Servicio de consultoria", description="Hora de asesoria",
                    price=75.00, stock=20, owner_id=user.id),
        ]
        db.session.add_all(products)
        db.session.flush()

        order = Order(
            reference=generate_reference("ORD"),
            customer_name="Cliente de Ejemplo",
            order_type="cobro",
            status=OrderStatus.PENDING,
            notes="Pedido generado por el script de ejemplo.",
            user_id=user.id,
        )
        db.session.add(order)
        db.session.flush()

        db.session.add(
            OrderItem(order_id=order.id, product_id=products[1].id,
                      quantity=2, unit_price=products[1].price)
        )
        db.session.add(
            OrderItem(order_id=order.id, product_id=products[2].id,
                      quantity=1, unit_price=products[2].price)
        )

        db.session.commit()
        print("Datos de ejemplo creados.")
        print(f"  Usuario: {DEMO_EMAIL}")
        print(f"  Contrasena: {DEMO_PASSWORD}")


if __name__ == "__main__":
    seed()
