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

# Enhanced features
try:
    from .enhanced_provider import EnhancedX402Provider, create_provider
    from .network import Network, NetworkConfig, SmartNetworkSelector
    from .development import DevelopmentMode, TestScenarios
    from .dashboard import X402Dashboard, enable_dashboard
    _enhanced_available = True
except ImportError:
    _enhanced_available = False

__version__ = "1.1.0"

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

# Add enhanced exports if available
if _enhanced_available:
    __all__.extend([
        "EnhancedX402Provider",
        "create_provider",
        "Network",
        "NetworkConfig",
        "SmartNetworkSelector",
        "DevelopmentMode",
        "TestScenarios",
        "X402Dashboard",
        "enable_dashboard",
    ])