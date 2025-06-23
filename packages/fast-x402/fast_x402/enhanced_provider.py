"""Enhanced X402Provider with all convenience features"""

import os
import json
from typing import Dict, Any, Optional, List, Union
from pathlib import Path

from .provider import X402Provider as BaseProvider
from .models import X402Config, PaymentData, PaymentVerification
from .network import SmartNetworkSelector, Network
from .development import DevelopmentMode
from .dashboard import X402Dashboard, enable_dashboard
from .logger import logger


class EnhancedX402Provider(BaseProvider):
    """X402Provider with all convenience features enabled"""
    
    def __init__(self, 
                 config: Optional[X402Config] = None,
                 mode: str = "auto",
                 enable_dashboard: bool = True):
        """
        Initialize enhanced provider with smart defaults
        
        Args:
            config: Optional configuration (auto-loads if not provided)
            mode: "auto", "development", "production"
            enable_dashboard: Enable real-time dashboard
        """
        
        # Auto-load configuration
        if not config:
            config = self._auto_load_config()
        
        # Ensure wallet address is set
        if not config.wallet_address:
            config.wallet_address = "0x742d35Cc6634C0532925a3b844Bc9e7595f5b899"
        
        # Set mode
        self.mode = self._determine_mode(mode)
        
        # Initialize development mode if needed
        self.dev_mode = None
        if self.mode == "development":
            self.dev_mode = DevelopmentMode()
            logger.info("🎮 Development mode enabled - Using mock blockchain")
        
        # Set mode on config
        config.mode = self.mode
        
        # Initialize base provider
        super().__init__(config)
        
        # Initialize dashboard
        self.dashboard = None
        if enable_dashboard:
            self.dashboard = X402Dashboard(self)
        
        # Token presets
        self.token_presets = self._load_token_presets()
        
        # Error message improvements
        self._setup_error_handlers()
        
        logger.info(f"✨ Enhanced X402Provider initialized in {self.mode} mode")
        
    def _auto_load_config(self) -> X402Config:
        """Auto-load configuration from various sources"""
        
        # 1. Check for .x402.config.json
        config_path = Path(".x402.config.json")
        if config_path.exists():
            with open(config_path) as f:
                config_data = json.load(f)
                logger.info("📁 Loaded configuration from .x402.config.json")
                return X402Config(**config_data)
        
        # 2. Check environment variables
        if os.getenv("X402_WALLET_ADDRESS"):
            logger.info("🔧 Loaded configuration from environment variables")
            return X402Config(
                wallet_address=os.getenv("X402_WALLET_ADDRESS"),
                chain_id=int(os.getenv("X402_CHAIN_ID", "84532")),
                accepted_tokens=os.getenv("X402_ACCEPTED_TOKENS", "").split(",") or None,
            )
        
        # 3. Use smart network detection
        try:
            network_selector = SmartNetworkSelector()
            network_config = network_selector.to_config_dict()
            
            logger.info(f"🌐 Auto-detected network: {network_config['network']}")
            
            # Create config with auto-generated wallet (will be created by base provider)
            config = X402Config(
                wallet_address=None,  # Will be auto-generated
                chain_id=network_config["chain_id"],
                accepted_tokens=list(network_config["tokens"].keys()) if network_config.get("tokens") else ["0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"],
            )
        except Exception as e:
            logger.warning(f"Network detection failed: {e}, using defaults")
            # Fallback to Base Sepolia defaults
            config = X402Config(
                wallet_address=None,
                chain_id=84532,
                accepted_tokens=["0x036CbD53842c5426634e7929541eC2318f3dCF7e"],
            )
            network_config = {
                "network": "base-sepolia",
                "facilitator_url": "https://api.coinbase.com/rpc/v1/base-sepolia/x402"
            }
        
        # Save for next time
        self._save_config(config, network_config)
        
        return config
    
    def _determine_mode(self, mode: str) -> str:
        """Determine the operating mode"""
        
        if mode != "auto":
            return mode
        
        # Auto-detect mode
        if os.getenv("NODE_ENV") == "development":
            return "development"
        elif os.getenv("NODE_ENV") == "production":
            return "production"
        elif os.path.exists(".git"):
            return "development"
        else:
            return "production"
    
    def _save_config(self, config: X402Config, network_config: Dict[str, Any]):
        """Save configuration for future use"""
        
        config_data = {
            "chain_id": config.chain_id,
            "accepted_tokens": config.accepted_tokens or [],
            "network": network_config.get("network", "base-sepolia"),
            "facilitator_url": network_config.get("facilitator_url", "https://api.coinbase.com/rpc/v1/base-sepolia/x402"),
        }
        
        # Only save wallet_address if it's been set
        if config.wallet_address:
            config_data["wallet_address"] = config.wallet_address
        
        with open(".x402.config.json", "w") as f:
            json.dump(config_data, f, indent=2)
        
        logger.info("💾 Saved configuration to .x402.config.json")
    
    def _load_token_presets(self) -> Dict[str, Dict[str, Any]]:
        """Load token presets for easy configuration"""
        
        return {
            "USDC": {
                "symbol": "USDC",
                "name": "USD Coin",
                "decimals": 6,
            },
            "USDT": {
                "symbol": "USDT", 
                "name": "Tether USD",
                "decimals": 6,
            },
            "DAI": {
                "symbol": "DAI",
                "name": "Dai Stablecoin",
                "decimals": 18,
            },
            "WETH": {
                "symbol": "WETH",
                "name": "Wrapped Ether",
                "decimals": 18,
            },
        }
    
    def _setup_error_handlers(self):
        """Setup developer-friendly error messages"""
        
        self._error_mappings = {
            "EIP712Domain hash mismatch": {
                "message": "Wrong network detected",
                "fix": "Check your chain_id configuration. Expected: {expected}, Got: {actual}",
            },
            "Insufficient allowance": {
                "message": "Token spending not approved",
                "fix": "The payer needs to approve USDC spending first",
            },
            "Invalid signature": {
                "message": "Payment signature verification failed", 
                "fix": "Ensure the payment was signed with the correct private key",
            },
            "Nonce already used": {
                "message": "Payment already processed",
                "fix": "Each payment must have a unique nonce",
            },
        }
    
    async def verify_payment(self, 
                           payment_data: PaymentData,
                           requirement: Any,
                           endpoint: Optional[str] = None) -> PaymentVerification:
        """Verify payment with enhanced error handling"""
        
        try:
            # Use mock verification in development mode
            if self.dev_mode:
                return await self.dev_mode.simulate_payment_flow(requirement)
            
            # Normal verification
            result = await super().verify_payment(payment_data, requirement, endpoint)
            
            # Track in dashboard
            if self.dashboard:
                await self.dashboard.track_payment({
                    "from_address": payment_data.from_address,
                    "amount": float(payment_data.value) / 1e6,
                    "token": payment_data.token,
                    "endpoint": endpoint,
                    "status": "completed" if result.valid else "failed",
                    "tx_hash": result.transaction_hash,
                })
            
            return result
            
        except Exception as e:
            # Enhance error message
            error_msg = str(e)
            for pattern, enhancement in self._error_mappings.items():
                if pattern in error_msg:
                    enhanced_msg = f"❌ {enhancement['message']}\n"
                    enhanced_msg += f"   Fix: {enhancement['fix']}"
                    raise type(e)(enhanced_msg) from e
            raise
    
    def accept_tokens(self, tokens: List[str]):
        """Accept tokens by name using presets"""
        
        token_addresses = []
        
        for token in tokens:
            if token in self.token_presets:
                # Get token address for current network
                try:
                    network_selector = SmartNetworkSelector()
                    token_config = network_selector.get_token_config(token)
                    if token_config and "address" in token_config:
                        token_addresses.append(token_config["address"])
                        logger.info(f"✅ Added {token} support")
                    else:
                        logger.warning(f"⚠️ Token {token} not found on current network")
                except Exception as e:
                    logger.warning(f"⚠️ Could not get token config for {token}: {e}")
                    # Fallback to default USDC address
                    if token == "USDC":
                        token_addresses.append("0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913")
            else:
                # Assume it's already an address
                token_addresses.append(token)
        
        if token_addresses:
            self.config.accepted_tokens = token_addresses
    
    def add_custom_token(self, 
                        symbol: str,
                        address: str,
                        decimals: int,
                        name: Optional[str] = None):
        """Add a custom token"""
        
        self.token_presets[symbol] = {
            "symbol": symbol,
            "name": name or symbol,
            "decimals": decimals,
            "address": address,
        }
        
        if address not in self.config.accepted_tokens:
            self.config.accepted_tokens.append(address)
        
        logger.info(f"✅ Added custom token: {symbol}")
    
    def enable_dashboard_ui(self, app=None, port: int = 3001):
        """Enable the real-time dashboard"""
        
        if not self.dashboard:
            self.dashboard = X402Dashboard(self)
        
        return enable_dashboard(self, app, port)
    
    def get_test_stats(self) -> Dict[str, Any]:
        """Get test statistics in development mode"""
        
        if self.dev_mode:
            return self.dev_mode.get_test_stats()
        else:
            return {"mode": self.mode, "message": "Not in development mode"}
    
    def create_test_scenario(self, scenario: str = "mixed"):
        """Create test scenarios for development"""
        
        if not self.dev_mode:
            raise RuntimeError("Test scenarios only available in development mode")
        
        from .development import TestScenarios
        scenarios = TestScenarios(self.dev_mode)
        
        if scenario == "aggressive":
            return scenarios.aggressive_agent
        elif scenario == "budget":
            return scenarios.budget_conscious_agent  
        elif scenario == "failing":
            return scenarios.failing_payments
        else:
            # Mixed scenario
            async def mixed():
                await scenarios.aggressive_agent(self.config.wallet_address)
                await scenarios.budget_conscious_agent(self.config.wallet_address)
            return mixed
    
    def generate_docs(self, output_dir: str = "docs"):
        """Generate API documentation with x402 integration"""
        
        Path(output_dir).mkdir(exist_ok=True)
        
        # Generate pricing table
        pricing_md = """# API Pricing

| Endpoint | Price | Description |
|----------|-------|-------------|
| `/api/weather/*` | $0.01 | Basic weather data |
| `/api/analyze/*` | $0.05 | Data analysis |
| `/api/premium/*` | $0.10 | Premium features |

## Integration

```python
# Install the SDK
pip install fast-x402

# Initialize in your app
from fast_x402 import EnhancedX402Provider

provider = EnhancedX402Provider()
```

## Testing

Use our test credentials:
- Network: Base Sepolia
- Test USDC: Available from faucet
- Dashboard: http://localhost:3001
"""
        
        with open(f"{output_dir}/pricing.md", "w") as f:
            f.write(pricing_md)
        
        # Generate Postman collection
        postman_collection = {
            "info": {
                "name": "x402 API",
                "description": "API with x402 micropayments",
            },
            "item": [
                {
                    "name": "Weather API",
                    "request": {
                        "method": "GET",
                        "header": [
                            {
                                "key": "X-Payment",
                                "value": "{{payment_header}}",
                                "description": "x402 payment authorization"
                            }
                        ],
                        "url": "{{base_url}}/api/weather/NYC"
                    }
                }
            ]
        }
        
        with open(f"{output_dir}/x402-api.postman.json", "w") as f:
            json.dump(postman_collection, f, indent=2)
        
        logger.info(f"📚 Generated documentation in {output_dir}/")
    
    def require_payment(self, amount: float, token: str = "USDC"):
        """Decorator to require payment for an endpoint"""
        
        def decorator(func):
            # Use FastAPI dependency injection instead of wrapper
            from fastapi import Depends, HTTPException, Request
            
            async def payment_dependency(request: Request):
                # Check for payment headers
                payment_signature = request.headers.get("X-Payment-Signature")
                payment_amount = request.headers.get("X-Payment-Amount")
                
                if not payment_signature or not payment_amount:
                    # No payment provided - return 402
                    raise HTTPException(status_code=402, detail={
                        "error": "Payment required",
                        "amount": str(amount),
                        "token": token
                    })
                
                # In development mode, accept any payment headers
                if self.mode == "development":
                    logger.debug(f"🎮 Dev mode: Accepting payment ${payment_amount}")
                    return True
                
                # TODO: Implement actual payment verification for production
                return True
            
            # Add the dependency to the function's metadata
            if not hasattr(func, '__annotations__'):
                func.__annotations__ = {}
            
            # Inject payment dependency
            original_annotations = func.__annotations__.copy()
            func.__annotations__['_payment_check'] = Depends(payment_dependency)
            
            return func
        return decorator
    
    def __repr__(self):
        return f"<EnhancedX402Provider mode={self.mode} wallet={self.config.wallet_address[:10]}...>"


def create_provider(**kwargs) -> EnhancedX402Provider:
    """Convenience function to create enhanced provider"""
    return EnhancedX402Provider(**kwargs)