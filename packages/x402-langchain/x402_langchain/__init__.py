"""x402-langchain: Enable autonomous AI agent payments"""

from .tools import X402PaymentTool, create_x402_tool
from .agent import X402Agent, create_x402_agent
from .client import X402Client
from .config import X402Config, SpendingLimits
from .exceptions import X402Error, PaymentError, InsufficientFundsError

# Enhanced features
try:
    from .enhanced_client import EnhancedX402Client, create_smart_agent, SmartApprovalRules
    from .mocking import APIMockingEngine, CostDiscoveryTool
    _enhanced_available = True
except ImportError:
    _enhanced_available = False

__version__ = "1.1.0"

__all__ = [
    "X402PaymentTool",
    "create_x402_tool",
    "X402Agent",
    "create_x402_agent",
    "X402Client",
    "X402Config",
    "SpendingLimits",
    "X402Error",
    "PaymentError",
    "InsufficientFundsError",
]

# Add enhanced exports if available
if _enhanced_available:
    __all__.extend([
        "EnhancedX402Client",
        "create_smart_agent",
        "SmartApprovalRules",
        "APIMockingEngine",
        "CostDiscoveryTool",
    ])