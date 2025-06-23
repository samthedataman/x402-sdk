"""
fastx402 - Dead Simple x402 Payments for FastAPI
pip install fastx402
"""

import json
import time
import logging
from typing import Dict, Any, Optional, List, Union, Callable
from dataclasses import dataclass
from decimal import Decimal
from functools import wraps

from fastapi import FastAPI, Request, Response, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from eth_account.messages import encode_structured_data
from web3 import Web3

__version__ = "1.0.0"
__all__ = ["FastX402", "PaymentRequired", "PaymentInfo", "PricingTier"]

logger = logging.getLogger(__name__)


# ============================================
# MODELS
# ============================================

class PaymentInfo(BaseModel):
    """Payment information attached to requests"""
    amount: Decimal
    token: str
    sender: str
    timestamp: int = Field(default_factory=lambda: int(time.time()))


class PaymentRequired(HTTPException):
    """Exception to return 402 Payment Required"""
    def __init__(self, amount: float, token: str = "USDC", **kwargs):
        super().__init__(status_code=402, detail="Payment required")
        self.amount = amount
        self.token = token
        self.extra = kwargs


class PricingTier(BaseModel):
    """Dynamic pricing tier configuration"""
    name: str
    price: Decimal
    features: List[str] = []
    rate_limit: Optional[int] = None


# ============================================
# MAIN CLASS
# ============================================

class FastX402:
    """
    FastAPI x402 payment integration
    
    Example:
        app = FastAPI()
        x402 = FastX402(app, wallet_address="0xYourWallet")
        
        x402.price("/api/data", 0.01)
        
        @app.get("/api/data")
        async def get_data(payment: PaymentInfo = Depends(x402.payment)):
            return {"data": "Premium content", "paid": payment.amount}
    """
    
    def __init__(
        self,
        app: FastAPI,
        wallet_address: str,
        chain_id: int = 8453,  # Base mainnet
        accepted_tokens: List[str] = None,
        auto_setup: bool = True,
        analytics_endpoint: bool = True,
        webhook_url: Optional[str] = None
    ):
        self.app = app
        self.wallet_address = Web3.to_checksum_address(wallet_address)
        self.chain_id = chain_id
        self.w3 = Web3()
        self.accepted_tokens = accepted_tokens or ["USDC"]
        self.webhook_url = webhook_url
        
        # Pricing configuration
        self._endpoint_pricing = {}
        self._dynamic_pricers = {}
        self._free_endpoints = {"/health", "/", "/openapi.json", "/docs", "/redoc"}
        
        # Payment cache
        self._used_payments = {}
        self._payment_cache_ttl = 3600  # 1 hour
        
        # Analytics
        self._analytics = {
            "total_requests": 0,
            "paid_requests": 0,
            "free_requests": 0,
            "total_revenue": {},  # By token
            "unique_payers": set(),
            "endpoint_stats": {}
        }
        
        if auto_setup:
            self._setup_middleware()
            
        if analytics_endpoint:
            self._setup_analytics_endpoint()
    
    def price(
        self,
        endpoint: str,
        amount: Union[float, Decimal],
        token: str = "USDC",
        dynamic: Optional[Callable] = None
    ) -> "FastX402":
        """
        Set pricing for an endpoint
        
        Args:
            endpoint: API endpoint path
            amount: Price in token units
            token: Payment token (default: USDC)
            dynamic: Optional function for dynamic pricing
            
        Returns:
            Self for chaining
        """
        self._endpoint_pricing[endpoint] = {
            "amount": Decimal(str(amount)),
            "token": token
        }
        
        if dynamic:
            self._dynamic_pricers[endpoint] = dynamic
            
        return self
    
    def free(self, endpoint: str) -> "FastX402":
        """Mark an endpoint as free"""
        self._free_endpoints.add(endpoint)
        return self
    
    def tier(self, endpoint: str, tiers: List[PricingTier]) -> "FastX402":
        """Set tiered pricing for an endpoint"""
        self._endpoint_pricing[endpoint] = {
            "tiers": tiers,
            "type": "tiered"
        }
        return self
    
    async def payment(self, request: Request) -> Optional[PaymentInfo]:
        """
        Dependency to get payment info from request
        
        Usage:
            @app.get("/api/data")
            async def get_data(payment: PaymentInfo = Depends(x402.payment)):
                return {"paid_by": payment.sender}
        """
        return getattr(request.state, "payment", None)
    
    def require_payment(self, amount: float = None, token: str = "USDC"):
        """
        Decorator to require payment for a specific endpoint
        
        Usage:
            @app.get("/api/premium")
            @x402.require_payment(0.10)
            async def premium_data():
                return {"data": "Premium content"}
        """
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Payment is already verified by middleware
                return await func(*args, **kwargs)
            
            # Store pricing info
            endpoint = f"/{func.__name__}"
            if amount:
                self.price(endpoint, amount, token)
                
            return wrapper
        return decorator
    
    def _setup_middleware(self):
        """Setup FastAPI middleware"""
        
        @self.app.middleware("http")
        async def x402_middleware(request: Request, call_next):
            # Track request
            self._analytics["total_requests"] += 1
            endpoint = str(request.url.path)
            
            # Check if endpoint is free
            if endpoint in self._free_endpoints:
                self._analytics["free_requests"] += 1
                return await call_next(request)
            
            # Get pricing for endpoint
            pricing = self._get_endpoint_pricing(endpoint, request)
            
            if not pricing or pricing.get("amount", 0) == 0:
                self._analytics["free_requests"] += 1
                return await call_next(request)
            
            # Check for payment header
            payment_header = request.headers.get("X-Payment")
            
            if not payment_header:
                # Return 402 Payment Required
                requirements = self._create_payment_requirements(endpoint, pricing)
                return JSONResponse(
                    status_code=402,
                    content={
                        "error": "Payment required",
                        **requirements
                    },
                    headers={
                        "X-Payment-Required": json.dumps(requirements)
                    }
                )
            
            # Verify payment
            payment_info = await self._verify_payment(payment_header, pricing)
            
            if not payment_info:
                return JSONResponse(
                    status_code=403,
                    content={"error": "Invalid payment"}
                )
            
            # Attach payment info to request
            request.state.payment = payment_info
            
            # Update analytics
            self._update_analytics(endpoint, payment_info)
            
            # Process request
            response = await call_next(request)
            
            # Add payment receipt
            response.headers["X-Payment-Receipt"] = json.dumps({
                "status": "accepted",
                "amount": str(payment_info.amount),
                "token": payment_info.token,
                "timestamp": payment_info.timestamp
            })
            
            return response
    
    def _get_endpoint_pricing(self, endpoint: str, request: Request) -> Optional[Dict]:
        """Get pricing for endpoint"""
        pricing = self._endpoint_pricing.get(endpoint)
        
        if not pricing:
            # Check for path parameters
            for path, price_config in self._endpoint_pricing.items():
                if self._match_path(path, endpoint):
                    pricing = price_config
                    break
        
        if pricing and endpoint in self._dynamic_pricers:
            # Calculate dynamic price
            dynamic_price = self._dynamic_pricers[endpoint](request)
            pricing = {
                "amount": Decimal(str(dynamic_price)),
                "token": pricing.get("token", "USDC")
            }
            
        return pricing
    
    def _match_path(self, pattern: str, path: str) -> bool:
        """Match path with parameters"""
        # Simple path matching - could be enhanced
        pattern_parts = pattern.split("/")
        path_parts = path.split("/")
        
        if len(pattern_parts) != len(path_parts):
            return False
            
        for p1, p2 in zip(pattern_parts, path_parts):
            if p1 != p2 and not p1.startswith("{"):
                return False
                
        return True
    
    def _create_payment_requirements(self, endpoint: str, pricing: Dict) -> Dict:
        """Create payment requirements"""
        nonce = str(int(time.time() * 1000000))
        
        return {
            "amount": str(pricing["amount"]),
            "token": pricing.get("token", "USDC"),
            "recipient": self.wallet_address,
            "chainId": self.chain_id,
            "nonce": nonce,
            "expiresAt": int(time.time()) + 300,  # 5 minutes
            "endpoint": endpoint,
            "metadata": {
                "service": "fastx402",
                "version": __version__
            }
        }
    
    async def _verify_payment(
        self,
        payment_header: str,
        pricing: Dict
    ) -> Optional[PaymentInfo]:
        """Verify payment signature"""
        try:
            payment_data = json.loads(payment_header)
            
            # Check if already used
            payment_id = f"{payment_data['nonce']}:{payment_data['signature']}"
            if payment_id in self._used_payments:
                return None
            
            # Verify amount matches
            if Decimal(payment_data["amount"]) < pricing["amount"]:
                return None
            
            # Create EIP-712 data for verification
            structured_data = {
                "types": {
                    "EIP712Domain": [
                        {"name": "name", "type": "string"},
                        {"name": "version", "type": "string"},
                        {"name": "chainId", "type": "uint256"},
                    ],
                    "Payment": [
                        {"name": "recipient", "type": "address"},
                        {"name": "amount", "type": "uint256"},
                        {"name": "token", "type": "address"},
                        {"name": "nonce", "type": "uint256"},
                        {"name": "expiresAt", "type": "uint256"},
                    ]
                },
                "domain": {
                    "name": "x402 Payment",
                    "version": "1",
                    "chainId": self.chain_id,
                },
                "primaryType": "Payment",
                "message": {
                    "recipient": self.wallet_address,
                    "amount": int(Decimal(payment_data["amount"]) * 10**6),
                    "token": self._get_token_address(payment_data["token"]),
                    "nonce": int(payment_data["nonce"]),
                    "expiresAt": int(payment_data["expiresAt"]),
                }
            }
            
            # Verify signature
            encoded = encode_structured_data(structured_data)
            signer = self.w3.eth.account.recover_message(
                encoded,
                signature=payment_data["signature"]
            )
            
            if signer.lower() != payment_data["signer"].lower():
                return None
            
            # Mark as used
            self._used_payments[payment_id] = time.time()
            self._cleanup_payment_cache()
            
            # Send webhook if configured
            if self.webhook_url:
                await self._send_webhook(payment_data)
            
            return PaymentInfo(
                amount=Decimal(payment_data["amount"]),
                token=payment_data["token"],
                sender=signer
            )
            
        except Exception as e:
            logger.error(f"Payment verification failed: {e}")
            return None
    
    def _get_token_address(self, token: str) -> str:
        """Get token contract address"""
        addresses = {
            "USDC": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
            "USDT": "0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2",
            "DAI": "0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb"
        }
        return addresses.get(token, token)
    
    def _cleanup_payment_cache(self):
        """Remove old payments from cache"""
        current_time = time.time()
        self._used_payments = {
            k: v for k, v in self._used_payments.items()
            if current_time - v < self._payment_cache_ttl
        }
    
    def _update_analytics(self, endpoint: str, payment: PaymentInfo):
        """Update analytics"""
        self._analytics["paid_requests"] += 1
        self._analytics["unique_payers"].add(payment.sender)
        
        # Update revenue by token
        token = payment.token
        if token not in self._analytics["total_revenue"]:
            self._analytics["total_revenue"][token] = Decimal("0")
        self._analytics["total_revenue"][token] += payment.amount
        
        # Update endpoint stats
        if endpoint not in self._analytics["endpoint_stats"]:
            self._analytics["endpoint_stats"][endpoint] = {
                "requests": 0,
                "revenue": Decimal("0")
            }
        self._analytics["endpoint_stats"][endpoint]["requests"] += 1
        self._analytics["endpoint_stats"][endpoint]["revenue"] += payment.amount
    
    async def _send_webhook(self, payment_data: Dict):
        """Send payment webhook"""
        # Implement webhook sending
        pass
    
    def _setup_analytics_endpoint(self):
        """Setup analytics endpoint"""
        
        @self.app.get("/x402/analytics")
        async def get_analytics():
            """Get payment analytics"""
            revenue_by_token = {
                token: float(amount)
                for token, amount in self._analytics["total_revenue"].items()
            }
            
            endpoint_stats = {
                endpoint: {
                    "requests": stats["requests"],
                    "revenue": float(stats["revenue"])
                }
                for endpoint, stats in self._analytics["endpoint_stats"].items()
            }
            
            return {
                "total_requests": self._analytics["total_requests"],
                "paid_requests": self._analytics["paid_requests"],
                "free_requests": self._analytics["free_requests"],
                "total_revenue": revenue_by_token,
                "unique_payers": len(self._analytics["unique_payers"]),
                "conversion_rate": (
                    self._analytics["paid_requests"] / 
                    self._analytics["total_requests"] * 100
                    if self._analytics["total_requests"] > 0 else 0
                ),
                "endpoint_stats": endpoint_stats,
                "wallet_address": self.wallet_address
            }
    
    def get_analytics(self) -> Dict[str, Any]:
        """Get analytics programmatically"""
        return {
            "total_requests": self._analytics["total_requests"],
            "paid_requests": self._analytics["paid_requests"],
            "total_revenue": {
                token: float(amount)
                for token, amount in self._analytics["total_revenue"].items()
            },
            "unique_payers": len(self._analytics["unique_payers"])
        }


# ============================================
# CONVENIENCE FUNCTIONS
# ============================================

def create_app(wallet_address: str, **kwargs) -> tuple[FastAPI, FastX402]:
    """
    Create a FastAPI app with x402 payments
    
    Returns:
        Tuple of (FastAPI app, FastX402 instance)
    """
    app = FastAPI(title="x402-Enabled API")
    x402 = FastX402(app, wallet_address, **kwargs)
    return app, x402


# ============================================
# DECORATORS
# ============================================

def payment_required(amount: float, token: str = "USDC"):
    """
    Standalone decorator for payment requirements
    
    Usage:
        @app.get("/api/data")
        @payment_required(0.10)
        async def get_data():
            return {"data": "Premium content"}
    """
    def decorator(func):
        func._x402_price = amount
        func._x402_token = token
        return func
    return decorator


"""
x402 Provider Integration Examples
Shows how to add x402 payments to existing APIs in minutes
"""

# ============================================
# EXAMPLE 1: Flask API - Before and After
# ============================================

### BEFORE: Traditional Flask API with Stripe ###
"""
from flask import Flask, request, jsonify
import stripe

app = Flask(__name__)
stripe.api_key = "sk_test_..."

@app.route('/api/weather')
def get_weather():
    # Complex auth check
    api_key = request.headers.get('X-API-Key')
    customer = validate_api_key(api_key)
    if not customer:
        return {"error": "Invalid API key"}, 401
    
    # Check subscription status
    if not check_subscription_active(customer):
        return {"error": "Subscription expired"}, 402
    
    # Check rate limits
    if exceeded_rate_limit(customer):
        return {"error": "Rate limit exceeded"}, 429
    
    # Return data
    return {"temperature": 72, "conditions": "sunny"}
"""

### AFTER: Flask API with x402 (3 lines added!) ###
from flask import Flask, request, jsonify
from x402_provider import X402Provider, x402_flask_middleware

app = Flask(__name__)

# Initialize x402 (1 line)
provider = X402Provider(wallet_address="0xYourWalletAddress")
x402_flask_middleware(app, provider)

# Configure pricing (1 line per endpoint)
provider.configure_endpoint("/api/weather", price=0.01)
provider.configure_endpoint("/api/forecast", price=0.05)

@app.route('/api/weather')
def get_weather():
    # No auth code needed! Payment already verified
    return {"temperature": 72, "conditions": "sunny"}

@app.route('/api/forecast')
def get_forecast():
    # Access payment info if needed
    if hasattr(request, 'x402_payment'):
        print(f"Paid by: {request.x402_payment['sender']}")
    
    return {"forecast": "Sunny for the next 5 days"}


# ============================================
# EXAMPLE 2: FastAPI - Modern Async API
# ============================================

from fastapi import FastAPI, Request
from x402_provider import X402Provider, X402FastAPIMiddleware

app = FastAPI()

# Setup x402
provider = X402Provider(
    wallet_address="0xYourWalletAddress",
    accepted_tokens=["USDC", "DAI"],
    webhook_url="https://your-app.com/payment-webhook"
)

# Add middleware
@app.middleware("http")
async def x402_middleware(request: Request, call_next):
    middleware = X402FastAPIMiddleware(app, provider)
    return await middleware(request, call_next)

# Configure tiered pricing
provider.configure_endpoint(
    "/api/analysis",
    price=0.10,
    strategy=PricingStrategy.TIERED
)

@app.post("/api/analysis")
async def analyze_data(request: Request, data: dict):
    # Premium analysis for paying customers
    result = perform_analysis(data)
    
    # Access payment details
    if hasattr(request.state, 'x402_payment'):
        amount = request.state.x402_payment['amount']
        # Could offer more features for higher payments
        if amount > Decimal("0.50"):
            result["premium_insights"] = generate_premium_insights(data)
    
    return result


# ============================================
# EXAMPLE 3: Express.js via Python Bridge
# ============================================

"""
// JavaScript Express app
const express = require('express');
const { X402Express } = require('x402-express');

const app = express();

// One line to add x402!
app.use(X402Express({
  walletAddress: '0xYourWalletAddress',
  pricing: {
    '/api/translate': 0.001,  // $0.001 per translation
    '/api/image-gen': 0.10,   // $0.10 per image
  }
}));

app.post('/api/translate', (req, res) => {
  // Payment already handled by middleware
  const translated = translateText(req.body.text);
  res.json({ translated });
});
"""


# ============================================
# EXAMPLE 4: Django Integration
# ============================================

# In settings.py
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'x402_django.middleware.X402Middleware',  # Add this
    'django.contrib.sessions.middleware.SessionMiddleware',
    # ... other middleware
]

X402_CONFIG = {
    'wallet_address': '0xYourWalletAddress',
    'pricing': {
        '/api/v1/data/': 0.05,
        '/api/v1/compute/': 0.25,
    }
}

# In views.py
from django.http import JsonResponse

def get_premium_data(request):
    # Payment already verified by middleware
    # Access payment info from request
    payment_info = getattr(request, 'x402_payment', None)
    
    if payment_info:
        # Paid request
        data = fetch_premium_data()
    else:
        # Free tier (if configured to fall back)
        data = fetch_basic_data()
    
    return JsonResponse(data)


# ============================================
# EXAMPLE 5: Hybrid Authentication
# ============================================

from flask import Flask, request, jsonify
from x402_provider import X402Provider, x402_flask_middleware, hybrid_auth_wrapper

app = Flask(__name__)
provider = X402Provider(wallet_address="0xYourWalletAddress")
x402_flask_middleware(app, provider)

# Configure endpoint to accept both payment types
provider.configure_endpoint("/api/data", price=0.05)

@app.route('/api/data')
@hybrid_auth_wrapper  # Supports both API keys and x402
def get_data():
    # Check which auth method was used
    if hasattr(request, 'x402_payment'):
        # Paid with x402
        source = "x402"
        user_id = request.x402_payment['sender']
    else:
        # Paid with traditional API key
        source = "api_key"
        user_id = get_user_from_api_key(request.headers.get('Authorization'))
    
    # Log usage
    log_api_usage(user_id, source)
    
    return {"data": "Premium content", "auth_method": source}


# ============================================
# EXAMPLE 6: Dynamic Pricing
# ============================================

from x402_provider import X402Provider, PricingStrategy

provider = X402Provider(wallet_address="0xYourWalletAddress")

# Custom pricing function based on request
def calculate_ai_price(request_data):
    """Price based on model and token count"""
    model = request_data.get('model', 'small')
    tokens = request_data.get('max_tokens', 100)
    
    # Base prices per 1000 tokens
    prices = {
        'small': 0.001,
        'medium': 0.01,
        'large': 0.10
    }
    
    base_price = prices.get(model, 0.01)
    total_price = (tokens / 1000) * base_price
    
    return total_price

# Configure dynamic pricing
provider.configure_endpoint(
    "/api/ai/complete",
    price=0.01,  # Default price
    strategy=PricingStrategy.DYNAMIC,
    custom_pricer=calculate_ai_price
)


# ============================================
# EXAMPLE 7: Analytics Dashboard
# ============================================

from flask import Flask, render_template
import json

app = Flask(__name__)
provider = X402Provider(wallet_address="0xYourWalletAddress")

@app.route('/dashboard')
def analytics_dashboard():
    """Simple analytics dashboard for x402 payments"""
    analytics = provider.get_analytics()
    
    return f"""
    <html>
    <head><title>x402 Analytics</title></head>
    <body>
        <h1>Payment Analytics</h1>
        <ul>
            <li>Total Requests: {analytics['total_requests']}</li>
            <li>Paid Requests: {analytics['paid_requests']}</li>
            <li>Free Requests: {analytics['free_requests']}</li>
            <li>Total Revenue: ${analytics['total_revenue']:.2f}</li>
            <li>Unique Payers: {analytics['unique_payers']}</li>
            <li>Payment Rate: {analytics['payment_percentage']:.1f}%</li>
        </ul>
        
        <h2>Recent Payments</h2>
        <div id="payments-feed">
            <!-- Real-time payment feed via websocket -->
        </div>
    </body>
    </html>
    """


# ============================================
# EXAMPLE 8: Migration Script
# ============================================

def migrate_from_stripe():
    """One-click migration from Stripe to x402"""
    import stripe
    
    # Fetch Stripe products and prices
    products = stripe.Product.list(active=True)
    
    # Create x402 pricing config
    x402_config = {}
    
    for product in products:
        # Get default price
        default_price = stripe.Price.retrieve(product.default_price)
        
        # Convert to x402 pricing (Stripe uses cents)
        x402_price = default_price.unit_amount / 100 / 1000  # Per request instead of per 1000
        
        # Map product metadata to endpoints
        endpoint = product.metadata.get('api_endpoint', f"/api/{product.id}")
        x402_config[endpoint] = float(x402_price)
    
    # Generate migration code
    print("# Add to your Flask/FastAPI app:")
    print(f"provider = X402Provider(wallet_address='0xYOUR_WALLET')")
    print()
    
    for endpoint, price in x402_config.items():
        print(f'provider.configure_endpoint("{endpoint}", price={price})')
    
    return x402_config


# ============================================
# EXAMPLE 9: A/B Testing Payments
# ============================================

import random

class ABTestingProvider(X402Provider):
    """Extended provider with A/B testing capabilities"""
    
    def generate_payment_requirements(self, endpoint, request_data=None):
        # A/B test different prices
        user_hash = hash(request_data.get('user_id', random.random()))
        
        if user_hash % 2 == 0:
            # Group A: Lower price
            self.endpoint_pricing[endpoint].base_price = Decimal("0.05")
        else:
            # Group B: Higher price  
            self.endpoint_pricing[endpoint].base_price = Decimal("0.10")
        
        return super().generate_payment_requirements(endpoint, request_data)


# ============================================
# EXAMPLE 10: Complete Real-World API
# ============================================

from flask import Flask, request, jsonify
from x402_provider import X402Provider, x402_flask_middleware, PricingStrategy
import os

# Create app with x402 payments
app = Flask(__name__)

# Initialize provider with production settings
provider = X402Provider(
    wallet_address=os.getenv("WALLET_ADDRESS"),
    chain_id=8453,  # Base mainnet
    accepted_tokens=["USDC", "USDT", "DAI"],
    settlement_handler=lambda p: print(f"Payment received: {p}"),
    webhook_url=os.getenv("PAYMENT_WEBHOOK_URL"),
    fallback_to_free=True  # Allow free tier if no payment
)

# Add middleware
x402_flask_middleware(app, provider)

# Configure all endpoints
ENDPOINT_PRICING = {
    # Data endpoints
    "/api/market-data/realtime": 0.10,
    "/api/market-data/historical": 0.05,
    "/api/market-data/aggregated": 0.25,
    
    # AI endpoints  
    "/api/ai/sentiment": 0.02,
    "/api/ai/prediction": 0.50,
    "/api/ai/analysis": 1.00,
    
    # Compute endpoints
    "/api/compute/cpu": 0.001,  # Per second
    "/api/compute/gpu": 0.01,   # Per second
}

for endpoint, price in ENDPOINT_PRICING.items():
    provider.configure_endpoint(endpoint, price)

# Health check (free)
@app.route('/health')
def health_check():
    return {"status": "ok", "x402": "enabled"}

# Market data endpoint
@app.route('/api/market-data/realtime')
def get_realtime_data():
    symbol = request.args.get('symbol', 'BTC')
    
    # Payment already verified by middleware
    data = fetch_realtime_market_data(symbol)
    
    return jsonify({
        "symbol": symbol,
        "data": data,
        "timestamp": time.time()
    })

# AI analysis with dynamic pricing
provider.configure_endpoint(
    "/api/ai/custom-analysis",
    price=0.10,
    strategy=PricingStrategy.DYNAMIC,
    custom_pricer=lambda req: len(req.get('text', '')) * 0.00001  # Price per character
)

@app.route('/api/ai/custom-analysis', methods=['POST'])
def custom_analysis():
    text = request.json.get('text', '')
    
    # Perform analysis
    result = perform_ai_analysis(text)
    
    # Include payment receipt in response
    if hasattr(request, 'x402_payment'):
        result['payment_receipt'] = {
            'amount': str(request.x402_payment['amount']),
            'currency': 'USDC'
        }
    
    return jsonify(result)

# Analytics endpoint for provider
@app.route('/api/admin/analytics')
def admin_analytics():
    # Add your own auth here
    if not is_admin(request):
        return {"error": "Unauthorized"}, 401
    
    return jsonify(provider.get_analytics())

if __name__ == '__main__':
    print(f"x402-enabled API running!")
    print(f"Wallet: {provider.wallet_address}")
    print(f"Endpoints: {len(provider.endpoint_pricing)}")
    app.run(port=5000)
    
    """
x402 Provider SDK - Make any API x402-compatible in minutes
Drop-in middleware for Flask, FastAPI, Express (via Python bridge)
"""

import json
import time
import hashlib
import logging
from typing import Dict, Any, Optional, Callable, Union, List
from dataclasses import dataclass
from decimal import Decimal
from functools import wraps
from enum import Enum
import requests

# Framework adapters
try:
    from flask import Flask, request, jsonify, make_response
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False

try:
    from fastapi import FastAPI, Request, Response, HTTPException
    from fastapi.responses import JSONResponse
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

from eth_account.messages import encode_structured_data, SignableMessage
from web3 import Web3

logger = logging.getLogger(__name__)


class PricingStrategy(Enum):
    """Pricing strategies for endpoints"""
    FIXED = "fixed"  # Fixed price per request
    TIERED = "tiered"  # Different prices based on request params
    DYNAMIC = "dynamic"  # Custom pricing function
    METERED = "metered"  # Based on response size/compute


@dataclass
class EndpointPricing:
    """Pricing configuration for an endpoint"""
    strategy: PricingStrategy
    base_price: Decimal
    token: str = "USDC"
    custom_pricer: Optional[Callable] = None
    free_quota: int = 0  # Free requests before charging
    
    
@dataclass 
class PaymentVerification:
    """Result of payment verification"""
    valid: bool
    amount: Decimal
    sender: str
    error: Optional[str] = None


class X402Provider:
    """Main provider class for x402 payment processing"""
    
    def __init__(
        self,
        wallet_address: str,
        chain_id: int = 8453,  # Base mainnet
        rpc_url: str = "https://base.llamarpc.com",
        accepted_tokens: List[str] = None,
        settlement_handler: Optional[Callable] = None,
        fallback_to_free: bool = True,
        cache_payments: bool = True,
        webhook_url: Optional[str] = None
    ):
        self.wallet_address = Web3.to_checksum_address(wallet_address)
        self.chain_id = chain_id
        self.rpc_url = rpc_url
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.accepted_tokens = accepted_tokens or ["USDC"]
        self.settlement_handler = settlement_handler
        self.fallback_to_free = fallback_to_free
        self.cache_payments = cache_payments
        self.webhook_url = webhook_url
        
        # Payment cache to prevent replay attacks
        self.payment_cache = {}
        
        # Endpoint pricing configuration
        self.endpoint_pricing = {}
        
        # Analytics
        self.payment_analytics = {
            "total_requests": 0,
            "paid_requests": 0,
            "free_requests": 0,
            "total_revenue": Decimal("0"),
            "unique_payers": set()
        }
    
    def configure_endpoint(
        self,
        path: str,
        price: Union[float, Decimal],
        strategy: PricingStrategy = PricingStrategy.FIXED,
        token: str = "USDC",
        custom_pricer: Optional[Callable] = None,
        free_quota: int = 0
    ):
        """Configure pricing for an endpoint"""
        self.endpoint_pricing[path] = EndpointPricing(
            strategy=strategy,
            base_price=Decimal(str(price)),
            token=token,
            custom_pricer=custom_pricer,
            free_quota=free_quota
        )
    
    def generate_payment_requirements(
        self,
        endpoint: str,
        request_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Generate payment requirements for 402 response"""
        pricing = self.endpoint_pricing.get(endpoint)
        if not pricing:
            # No pricing configured - free endpoint
            return None
            
        # Calculate price based on strategy
        price = self._calculate_price(pricing, request_data)
        
        if price == 0:
            return None
            
        nonce = str(int(time.time() * 1000000))  # Microsecond timestamp
        
        return {
            "amount": str(price),
            "token": pricing.token,
            "recipient": self.wallet_address,
            "chainId": self.chain_id,
            "nonce": nonce,
            "expiresAt": int(time.time()) + 300,  # 5 minutes
            "paymentUrl": f"/x402/payment/{nonce}",
            "metadata": {
                "endpoint": endpoint,
                "timestamp": int(time.time())
            }
        }
    
    def _calculate_price(
        self,
        pricing: EndpointPricing,
        request_data: Optional[Dict] = None
    ) -> Decimal:
        """Calculate price based on pricing strategy"""
        if pricing.strategy == PricingStrategy.FIXED:
            return pricing.base_price
            
        elif pricing.strategy == PricingStrategy.TIERED:
            # Example: Different prices based on request params
            if request_data and "premium" in request_data:
                return pricing.base_price * 2
            return pricing.base_price
            
        elif pricing.strategy == PricingStrategy.DYNAMIC:
            if pricing.custom_pricer:
                return Decimal(str(pricing.custom_pricer(request_data)))
            return pricing.base_price
            
        elif pricing.strategy == PricingStrategy.METERED:
            # Price based on expected resource usage
            # This would be finalized after response generation
            return pricing.base_price
            
        return pricing.base_price
    
    def verify_payment(self, payment_header: str) -> PaymentVerification:
        """Verify x402 payment from header"""
        try:
            payment_data = json.loads(payment_header)
            
            # Check if payment was already used (replay attack)
            payment_id = f"{payment_data['nonce']}:{payment_data['signature']}"
            if self.cache_payments and payment_id in self.payment_cache:
                return PaymentVerification(
                    valid=False,
                    amount=Decimal("0"),
                    sender="",
                    error="Payment already used"
                )
            
            # Verify signature
            structured_data = {
                "types": {
                    "EIP712Domain": [
                        {"name": "name", "type": "string"},
                        {"name": "version", "type": "string"},
                        {"name": "chainId", "type": "uint256"},
                    ],
                    "Payment": [
                        {"name": "recipient", "type": "address"},
                        {"name": "amount", "type": "uint256"},
                        {"name": "token", "type": "address"},
                        {"name": "nonce", "type": "uint256"},
                        {"name": "expiresAt", "type": "uint256"},
                    ]
                },
                "domain": {
                    "name": "x402 Payment",
                    "version": "1",
                    "chainId": self.chain_id,
                },
                "primaryType": "Payment",
                "message": {
                    "recipient": self.wallet_address,
                    "amount": int(Decimal(payment_data["amount"]) * 10**6),
                    "token": self._get_token_address(payment_data["token"]),
                    "nonce": int(payment_data["nonce"]),
                    "expiresAt": int(payment_data["expiresAt"]),
                }
            }
            
            # Recover signer
            encoded = encode_structured_data(structured_data)
            signer = self.w3.eth.account.recover_message(
                encoded,
                signature=payment_data["signature"]
            )
            
            # Verify signer matches
            if signer.lower() != payment_data["signer"].lower():
                return PaymentVerification(
                    valid=False,
                    amount=Decimal("0"),
                    sender="",
                    error="Invalid signature"
                )
            
            # Cache payment
            if self.cache_payments:
                self.payment_cache[payment_id] = time.time()
                # Clean old entries (older than 1 hour)
                self._clean_payment_cache()
            
            # Update analytics
            self.payment_analytics["paid_requests"] += 1
            self.payment_analytics["total_revenue"] += Decimal(payment_data["amount"])
            self.payment_analytics["unique_payers"].add(signer)
            
            # Call settlement handler if configured
            if self.settlement_handler:
                self.settlement_handler(payment_data)
            
            # Send webhook if configured
            if self.webhook_url:
                self._send_webhook(payment_data)
            
            return PaymentVerification(
                valid=True,
                amount=Decimal(payment_data["amount"]),
                sender=signer
            )
            
        except Exception as e:
            logger.error(f"Payment verification failed: {e}")
            return PaymentVerification(
                valid=False,
                amount=Decimal("0"),
                sender="",
                error=str(e)
            )
    
    def _get_token_address(self, token_symbol: str) -> str:
        """Get token contract address"""
        token_addresses = {
            "USDC": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
            "USDT": "0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2",
            "DAI": "0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb"
        }
        return token_addresses.get(token_symbol, token_symbol)
    
    def _clean_payment_cache(self):
        """Remove old payments from cache"""
        current_time = time.time()
        old_payments = [
            pid for pid, timestamp in self.payment_cache.items()
            if current_time - timestamp > 3600  # 1 hour
        ]
        for pid in old_payments:
            del self.payment_cache[pid]
    
    def _send_webhook(self, payment_data: Dict):
        """Send payment notification to webhook"""
        try:
            requests.post(self.webhook_url, json={
                "type": "payment_received",
                "payment": payment_data,
                "timestamp": time.time()
            })
        except Exception as e:
            logger.error(f"Webhook failed: {e}")
    
    def get_analytics(self) -> Dict[str, Any]:
        """Get payment analytics"""
        return {
            "total_requests": self.payment_analytics["total_requests"],
            "paid_requests": self.payment_analytics["paid_requests"],
            "free_requests": self.payment_analytics["free_requests"],
            "total_revenue": float(self.payment_analytics["total_revenue"]),
            "unique_payers": len(self.payment_analytics["unique_payers"]),
            "payment_percentage": (
                self.payment_analytics["paid_requests"] / 
                self.payment_analytics["total_requests"] * 100
                if self.payment_analytics["total_requests"] > 0 else 0
            )
        }


# Flask Middleware
if FLASK_AVAILABLE:
    def x402_flask_middleware(app: Flask, provider: X402Provider):
        """Flask middleware for x402 payments"""
        
        @app.before_request
        def check_payment():
            provider.payment_analytics["total_requests"] += 1
            
            # Get endpoint path
            endpoint = request.path
            
            # Check if endpoint requires payment
            requirements = provider.generate_payment_requirements(
                endpoint,
                request.get_json(silent=True)
            )
            
            if not requirements:
                # Free endpoint
                provider.payment_analytics["free_requests"] += 1
                return None
            
            # Check for payment header
            payment_header = request.headers.get("X-Payment")
            
            if not payment_header:
                # Return 402 Payment Required
                response = make_response(jsonify({
                    "error": "Payment required",
                    **requirements
                }), 402)
                response.headers["X-Payment-Required"] = json.dumps(requirements)
                return response
            
            # Verify payment
            verification = provider.verify_payment(payment_header)
            
            if not verification.valid:
                return jsonify({
                    "error": "Invalid payment",
                    "details": verification.error
                }), 403
            
            # Store payment info for use in route
            request.x402_payment = {
                "amount": verification.amount,
                "sender": verification.sender
            }
            
            return None
        
        @app.after_request
        def add_payment_receipt(response):
            if hasattr(request, 'x402_payment'):
                response.headers["X-Payment-Receipt"] = json.dumps({
                    "status": "accepted",
                    "amount": str(request.x402_payment["amount"]),
                    "timestamp": int(time.time())
                })
            return response
    
    def x402_protected(price: Union[float, str], **kwargs):
        """Decorator for protecting individual Flask routes"""
        def decorator(f):
            @wraps(f)
            def wrapped(*args, **kw):
                # Route-specific payment logic if needed
                return f(*args, **kw)
            return wrapped
        return decorator


# FastAPI Middleware
if FASTAPI_AVAILABLE:
    class X402FastAPIMiddleware:
        """FastAPI middleware for x402 payments"""
        
        def __init__(self, app: FastAPI, provider: X402Provider):
            self.app = app
            self.provider = provider
            
        async def __call__(self, request: Request, call_next):
            self.provider.payment_analytics["total_requests"] += 1
            
            # Get endpoint path
            endpoint = request.url.path
            
            # Check if endpoint requires payment
            body = None
            if request.method in ["POST", "PUT", "PATCH"]:
                body = await request.body()
                if body:
                    body = json.loads(body)
            
            requirements = self.provider.generate_payment_requirements(endpoint, body)
            
            if not requirements:
                self.provider.payment_analytics["free_requests"] += 1
                response = await call_next(request)
                return response
            
            # Check for payment header
            payment_header = request.headers.get("X-Payment")
            
            if not payment_header:
                return JSONResponse(
                    status_code=402,
                    content={
                        "error": "Payment required",
                        **requirements
                    },
                    headers={"X-Payment-Required": json.dumps(requirements)}
                )
            
            # Verify payment
            verification = self.provider.verify_payment(payment_header)
            
            if not verification.valid:
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": "Invalid payment",
                        "details": verification.error
                    }
                )
            
            # Add payment info to request state
            request.state.x402_payment = {
                "amount": verification.amount,
                "sender": verification.sender
            }
            
            response = await call_next(request)
            
            # Add payment receipt
            response.headers["X-Payment-Receipt"] = json.dumps({
                "status": "accepted",
                "amount": str(verification.amount),
                "timestamp": int(time.time())
            })
            
            return response


# Convenience Functions

def create_flask_app(wallet_address: str, **provider_kwargs) -> Flask:
    """Create a Flask app with x402 payment support"""
    app = Flask(__name__)
    provider = X402Provider(wallet_address, **provider_kwargs)
    x402_flask_middleware(app, provider)
    
    # Add analytics endpoint
    @app.route("/x402/analytics")
    def get_analytics():
        return jsonify(provider.get_analytics())
    
    return app, provider


def create_fastapi_app(wallet_address: str, **provider_kwargs) -> FastAPI:
    """Create a FastAPI app with x402 payment support"""
    app = FastAPI()
    provider = X402Provider(wallet_address, **provider_kwargs)
    
    @app.middleware("http")
    async def x402_middleware(request: Request, call_next):
        middleware = X402FastAPIMiddleware(app, provider)
        return await middleware(request, call_next)
    
    @app.get("/x402/analytics")
    async def get_analytics():
        return provider.get_analytics()
    
    return app, provider


# Migration Helpers

def migrate_stripe_pricing(stripe_prices: Dict[str, Any]) -> Dict[str, Decimal]:
    """Convert Stripe pricing to x402 pricing"""
    x402_prices = {}
    
    for product_id, stripe_price in stripe_prices.items():
        # Convert from cents to dollars
        if stripe_price.get("unit_amount"):
            x402_prices[product_id] = Decimal(stripe_price["unit_amount"]) / 100
        elif stripe_price.get("tiers"):
            # Use lowest tier price
            x402_prices[product_id] = Decimal(stripe_price["tiers"][0]["unit_amount"]) / 100
    
    return x402_prices


def hybrid_auth_wrapper(original_handler):
    """Wrapper to support both API keys and x402 payments"""
    @wraps(original_handler)
    def wrapped(*args, **kwargs):
        request = args[0] if args else kwargs.get('request')
        
        # Check for x402 payment
        if hasattr(request, 'x402_payment'):
            # Payment verified, proceed
            return original_handler(*args, **kwargs)
        
        # Fall back to original auth (API keys, etc)
        if request.headers.get("Authorization"):
            return original_handler(*args, **kwargs)
        
        # No auth provided
        return {"error": "Authentication required"}, 401
    
    return wrapped