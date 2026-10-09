"""Logica de negocio del simulador de pago/cobro.

Este modulo concentra la simulacion del procesamiento de pagos, de modo que
las vistas permanezcan delgadas y la logica sea facil de probar de forma
aislada.
"""

import uuid
from dataclasses import dataclass

from .models import PaymentStatus


@dataclass
class SimulationResult:
    """Resultado de una simulacion de pago."""

    status: str
    message: str


def luhn_check(card_number: str) -> bool:
    """Valida un numero de tarjeta con el algoritmo de Luhn.

    Devuelve ``True`` si el numero (solo digitos) supera la verificacion.
    """
    digits = [int(d) for d in card_number if d.isdigit()]
    if not digits:
        return False
    checksum = 0
    reverse = digits[::-1]
    for index, digit in enumerate(reverse):
        if index % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit
    return checksum % 10 == 0


def generate_reference(prefix: str = "PAY") -> str:
    """Genera una referencia unica y legible para pagos y pedidos."""
    return f"{prefix}-{uuid.uuid4().hex[:10].upper()}"


def _simulate_card(card_number: str) -> SimulationResult:
    """Simula el comportamiento de una pasarela con tarjeta.

    Reglas de simulacion (comodas para una demostracion):

    * Un numero que empieza por ``4000`` se rechaza siempre.
    * Un numero que empieza por ``4444`` queda pendiente de confirmacion.
    * Cualquier otro numero que pase Luhn se aprueba.
    """
    digits = "".join(c for c in card_number if c.isdigit())
    if not digits:
        return SimulationResult(
            PaymentStatus.REJECTED, "Debe indicar el numero de tarjeta."
        )
    if not luhn_check(digits):
        return SimulationResult(
            PaymentStatus.REJECTED, "Numero de tarjeta invalido (no supera Luhn)."
        )
    if digits.startswith("4000"):
        return SimulationResult(
            PaymentStatus.REJECTED, "Tarjeta rechazada por el banco emisor."
        )
    if digits.startswith("4444"):
        return SimulationResult(
            PaymentStatus.PENDING, "Pago en revision (confirmacion manual)."
        )
    return SimulationResult(PaymentStatus.APPROVED, "Pago aprobado correctamente.")


def simulate_payment(form, amount: float) -> SimulationResult:
    """Ejecuta la simulacion segun el metodo y las reglas definidas.

    :param form: formulario :class:`~app.forms.PaymentForm` ya validado.
    :param amount: importe a procesar.
    :return: instancia de :class:`SimulationResult`.
    """
    if amount <= 0:
        return SimulationResult(PaymentStatus.REJECTED, "El importe debe ser mayor que cero.")

    method = form.method.data

    if method == "tarjeta":
        result = _simulate_card(form.card_number.data or "")
    elif method == "transferencia":
        result = SimulationResult(
            PaymentStatus.APPROVED, "Transferencia registrada correctamente."
        )
    else:
        result = SimulationResult(
            PaymentStatus.APPROVED, "Pago en efectivo registrado."
        )

    # El usuario puede forzar el resultado para demostraciones.
    if form.force_result.data == "approve":
        result = SimulationResult(PaymentStatus.APPROVED, "Pago forzado como aprobado.")
    elif form.force_result.data == "reject":
        result = SimulationResult(PaymentStatus.REJECTED, "Pago forzado como rechazado.")

    return result


def card_last4(card_number: str) -> str:
    """Devuelve los ultimos cuatro digitos de un numero de tarjeta."""
    digits = "".join(c for c in (card_number or "") if c.isdigit())
    return digits[-4:] if len(digits) >= 4 else ""
