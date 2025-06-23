"""fast-x402: Lightning-fast x402 payment integration for FastAPI"""

from .provider import X402Provider
from .middleware import x402_middleware
from .dependencies import X402Dependency, get_x402_payment
from .exceptions import X402Error, PaymentRequiredError, InvalidPaymentError
from .models import (
    PaymentRequirement,
    PaymentData,
    PaymentVerification,
    X402Config,
    X402Analytics,
)

__version__ = "1.0.0"

__all__ = [
    "X402Provider",
    "x402_middleware",
    "X402Dependency",
    "get_x402_payment",
    "X402Error",
    "PaymentRequiredError",
    "InvalidPaymentError",
    "PaymentRequirement",
    "PaymentData",
    "PaymentVerification",
    "X402Config",
    "X402Analytics",
]