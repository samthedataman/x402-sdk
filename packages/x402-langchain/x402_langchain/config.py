"""Configuration for x402-langchain"""

from typing import Dict, List, Optional, Any, Callable
from pydantic import BaseModel, Field
from datetime import timedelta


class SpendingLimits(BaseModel):
    """Spending limits for AI agents"""
    per_request: float = Field(default=1.0, description="Max amount per request in USD")
    per_hour: float = Field(default=10.0, description="Max amount per hour in USD")
    per_day: float = Field(default=100.0, description="Max amount per day in USD")
    
    def validate_request(self, amount: float) -> bool:
        """Check if request amount is within limits"""
        return amount <= self.per_request


class X402Config(BaseModel):
    """Configuration for x402 AI agent payments"""
    
    # Wallet configuration
    private_key: str = Field(..., description="Agent's private key for signing payments")
    wallet_address: Optional[str] = Field(None, description="Derived from private key if not provided")
    
    # Network configuration
    chain_id: int = Field(default=8453, description="Blockchain chain ID (8453 = Base)")
    rpc_url: Optional[str] = Field(None, description="Custom RPC URL if needed")
    
    # Payment configuration
    default_token: str = Field(
        default="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        description="Default payment token (USDC)"
    )
    gas_buffer: float = Field(default=1.2, description="Gas estimate buffer multiplier")
    
    # Spending controls
    spending_limits: SpendingLimits = Field(default_factory=SpendingLimits)
    allowed_domains: Optional[List[str]] = Field(None, description="Restrict payments to these domains")
    blocked_domains: List[str] = Field(default_factory=list, description="Never pay these domains")
    
    # Behavior configuration
    auto_approve: bool = Field(default=False, description="Auto-approve payments within limits")
    approval_callback: Optional[Any] = Field(None, description="Callback for payment approval")
    max_retries: int = Field(default=3, description="Max retries for failed payments")
    timeout: float = Field(default=30.0, description="Request timeout in seconds")
    
    # Monitoring
    log_payments: bool = Field(default=True, description="Log all payment attempts")
    webhook_url: Optional[str] = Field(None, description="Webhook for payment notifications")
    
    class Config:
        arbitrary_types_allowed = True
        json_schema_extra = {
            "example": {
                "private_key": "0x...",
                "spending_limits": {
                    "per_request": 0.50,
                    "per_hour": 5.00,
                    "per_day": 50.00
                },
                "allowed_domains": ["api.example.com", "data.provider.com"],
                "auto_approve": True
            }
        }