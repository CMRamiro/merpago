"""Pruebas de integracion del simulador de pago/cobro.

Se ejecutan con la libreria estandar:

    python -m unittest discover -s tests -v
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from app.extensions import db
from app.models import Order, OrderStatus, Payment, PaymentStatus, Product, User
from app.services import luhn_check, simulate_payment


class BaseTestCase(unittest.TestCase):
    """Configura una app de pruebas con base de datos en memoria."""

    def setUp(self):
        self.app = create_app("testing")
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    # Utilidades ---------------------------------------------------------
    def register(self, email="user@example.com", password="secret123"):
        return self.client.post(
            "/auth/register",
            data={
                "name": "Usuario Test",
                "email": email,
                "password": password,
                "confirm_password": password,
            },
            follow_redirects=True,
        )

    def create_product(self, name="Producto", price="10.00", stock="5"):
        return self.client.post(
            "/products/new",
            data={"name": name, "description": "", "price": price, "stock": stock},
            follow_redirects=True,
        )

    def create_order(self, product_id, qty="1"):
        return self.client.post(
            "/orders/new",
            data={
                "customer_name": "Cliente",
                "order_type": "pago",
                "notes": "",
                f"selected_{product_id}": "1",
                f"qty_{product_id}": qty,
            },
            follow_redirects=True,
        )


class AuthTests(BaseTestCase):
    def test_register_and_login(self):
        resp = self.register()
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(User.query.count(), 1)

        self.client.get("/auth/logout")
        resp = self.client.post(
            "/auth/login",
            data={"email": "user@example.com", "password": "secret123"},
            follow_redirects=True,
        )
        self.assertIn(b"Hola", resp.data)

    def test_wrong_password_is_rejected(self):
        self.register()
        self.client.get("/auth/logout")
        resp = self.client.post(
            "/auth/login",
            data={"email": "user@example.com", "password": "incorrecta"},
        )
        self.assertEqual(resp.status_code, 401)

    def test_duplicate_email(self):
        self.register()
        self.client.get("/auth/logout")
        resp = self.client.post(
            "/auth/register",
            data={
                "name": "Otro",
                "email": "user@example.com",
                "password": "secret123",
                "confirm_password": "secret123",
            },
        )
        self.assertIn(b"Ya existe", resp.data)
        self.assertEqual(User.query.count(), 1)


class ProductTests(BaseTestCase):
    def test_crud_product_requires_login(self):
        resp = self.client.get("/products/")
        self.assertEqual(resp.status_code, 302)

        self.register()
        self.create_product(name="Plan A", price="25.00", stock="3")
        self.assertEqual(Product.query.count(), 1)
        product = Product.query.first()
        self.assertEqual(product.name, "Plan A")
        self.assertEqual(product.price_float, 25.0)

    def test_cannot_edit_other_users_product(self):
        self.register(email="a@example.com")
        self.create_product()
        product = Product.query.first()
        self.client.get("/auth/logout")

        self.register(email="b@example.com")
        resp = self.client.get(f"/products/{product.id}/edit")
        self.assertEqual(resp.status_code, 403)


class OrderTests(BaseTestCase):
    def test_create_order_computes_total(self):
        self.register()
        self.create_product(price="10.00", stock="5")
        product = Product.query.first()
        self.create_order(product.id, qty="3")

        order = Order.query.first()
        self.assertIsNotNone(order)
        self.assertEqual(order.total, 30.0)
        self.assertEqual(order.status, OrderStatus.PENDING)


class PaymentSimulationTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.assertTrue(luhn_check("4111111111111111"))
        self.assertFalse(luhn_check("4111111111111112"))

    def _prepare_order(self):
        self.register()
        self.create_product(price="10.00", stock="5")
        product = Product.query.first()
        self.create_order(product.id, qty="1")
        return Order.query.first()

    def test_approved_card_updates_order(self):
        order = self._prepare_order()
        resp = self.client.post(
            f"/payments/checkout/{order.id}",
            data={
                "order_id": str(order.id),
                "amount": "10.00",
                "method": "tarjeta",
                "card_number": "4111111111111111",
                "card_holder": "Test",
                "card_expiry": "12/29",
                "card_cvv": "123",
                "force_result": "auto",
            },
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)
        db.session.refresh(order)
        self.assertEqual(order.status, OrderStatus.PAID)
        payment = Payment.query.first()
        self.assertEqual(payment.status, PaymentStatus.APPROVED)
        self.assertEqual(payment.card_last4, "1111")

    def test_rejected_card_marks_order_failed(self):
        order = self._prepare_order()
        self.client.post(
            f"/payments/checkout/{order.id}",
            data={
                "order_id": str(order.id),
                "amount": "10.00",
                "method": "tarjeta",
                "card_number": "4000000000000002",
                "card_holder": "Test",
                "card_expiry": "12/29",
                "card_cvv": "123",
                "force_result": "auto",
            },
            follow_redirects=True,
        )
        db.session.refresh(order)
        self.assertEqual(order.status, OrderStatus.FAILED)
        self.assertEqual(Payment.query.first().status, PaymentStatus.REJECTED)

    def test_force_approve_transfer(self):
        order = self._prepare_order()
        self.client.post(
            f"/payments/checkout/{order.id}",
            data={
                "order_id": str(order.id),
                "amount": "10.00",
                "method": "transferencia",
                "force_result": "approve",
            },
            follow_redirects=True,
        )
        db.session.refresh(order)
        self.assertEqual(order.status, OrderStatus.PAID)


if __name__ == "__main__":
    unittest.main(verbosity=2)
