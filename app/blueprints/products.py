"""Rutas de gestion de productos (listar, crear, editar y eliminar).

Cada usuario solo puede modificar los productos que le pertenecen.
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
from ..forms import ProductForm
from ..models import Product

products_bp = Blueprint("products", __name__, template_folder="../templates/products")


def _get_owned_product_or_404(product_id: int) -> Product:
    """Recupera un producto verificando que pertenece al usuario actual."""
    product = db.session.get(Product, product_id)
    if product is None:
        abort(404)
    if product.owner_id != current_user.id:
        abort(403)
    return product


@products_bp.route("/")
@login_required
def list_products():
    """Lista los productos del usuario actual."""
    products = (
        Product.query.filter_by(owner_id=current_user.id)
        .order_by(Product.created_at.desc())
        .all()
    )
    return render_template("products/list.html", products=products)


@products_bp.route("/new", methods=["GET", "POST"])
@login_required
def create_product():
    """Crea un producto nuevo para el usuario actual."""
    form = ProductForm()
    if form.validate_on_submit():
        product = Product(
            name=form.name.data.strip(),
            description=(form.description.data or "").strip(),
            price=form.price.data,
            stock=form.stock.data,
            owner_id=current_user.id,
        )
        db.session.add(product)
        db.session.commit()
        flash("Producto creado correctamente.", "success")
        return redirect(url_for("products.list_products"))
    return render_template("products/form.html", form=form, title="Nuevo producto")


@products_bp.route("/<int:product_id>/edit", methods=["GET", "POST"])
@login_required
def edit_product(product_id: int):
    """Edita un producto existente del usuario actual."""
    product = _get_owned_product_or_404(product_id)
    form = ProductForm(obj=product)
    if form.validate_on_submit():
        product.name = form.name.data.strip()
        product.description = (form.description.data or "").strip()
        product.price = form.price.data
        product.stock = form.stock.data
        db.session.commit()
        flash("Producto actualizado.", "success")
        return redirect(url_for("products.list_products"))
    return render_template("products/form.html", form=form, title="Editar producto")


@products_bp.route("/<int:product_id>/delete", methods=["POST"])
@login_required
def delete_product(product_id: int):
    """Elimina un producto del usuario actual."""
    product = _get_owned_product_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash("Producto eliminado.", "info")
    return redirect(url_for("products.list_products"))
