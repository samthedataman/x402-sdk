"""Data models for fast-x402"""

from typing import Dict, List, Optional, Any, Callable
from pydantic import BaseModel, Field
from datetime import datetime


class PaymentRequirement(BaseModel):
    """Payment requirement details for HTTP 402 response"""
    amount: str = Field(..., description="Payment amount in token units")
    token: str = Field(..., description="Token contract address")
    recipient: str = Field(..., description="Recipient wallet address")
    chain_id: int = Field(..., description="Blockchain chain ID")
    nonce: str = Field(..., description="Unique payment nonce")
    expires_at: int = Field(..., description="Unix timestamp when payment expires")
    scheme: str = Field(default="exact", description="Payment scheme: exact or upto")
    
    class Config:
        json_schema_extra = {
            "example": {
                "amount": "0.10",
                "token": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
                "recipient": "0x742d35Cc6634C0532925a3b844Bc9e7595f6E123",
                "chain_id": 8453,
                "nonce": "0x1234567890abcdef",
                "expires_at": 1704067200,
                "scheme": "exact"
            }
        }


class PaymentData(BaseModel):
    """Signed payment data from client"""
    from_address: str = Field(..., alias="from", description="Sender address")
    to: str = Field(..., description="Recipient address")
    value: str = Field(..., description="Payment amount")
    token: str = Field(..., description="Token contract address")
    chain_id: int = Field(..., description="Blockchain chain ID")
    nonce: str = Field(..., description="Payment nonce")
    valid_before: int = Field(..., description="Validity timestamp")
    signature: str = Field(..., description="EIP-712 signature")
    
    class Config:
        populate_by_name = True


class PaymentVerification(BaseModel):
    """Payment verification result"""
    valid: bool
    transaction_hash: Optional[str] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class RouteConfig(BaseModel):
    """Configuration for a specific route"""
    amount: str
    token: Optional[str] = None
    scheme: str = "exact"
    custom_validation: Optional[Any] = None  # Callable in runtime


class X402Config(BaseModel):
    """Main configuration for X402Provider"""
    wallet_address: Optional[str] = None
    chain_id: int = 8453  # Base mainnet
    accepted_tokens: List[str] = Field(
        default_factory=lambda: ["0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"]  # USDC
    )
    settlement_address: Optional[str] = None
    cache_enabled: bool = True
    cache_ttl: int = 300  # 5 minutes
    analytics_enabled: bool = True
    analytics_webhook: Optional[str] = None
    custom_validation: Optional[Any] = None  # Callable in runtime
    mode: str = Field(default="production", description="Operating mode: production, development, or testing")
    
    class Config:
        arbitrary_types_allowed = True


class PayerStats(BaseModel):
    """Statistics for a single payer"""
    address: str
    total: str
    count: int
    last_payment: datetime


class X402Analytics(BaseModel):
    """Analytics data for X402 payments"""
    total_requests: int = 0
    total_paid: int = 0
    total_revenue: Dict[str, str] = Field(default_factory=dict)
    conversion_rate: float = 0.0
    top_payers: List[PayerStats] = Field(default_factory=list)
    revenue_by_endpoint: Dict[str, Dict[str, str]] = Field(default_factory=dict)
    
    def to_dashboard_dict(self) -> Dict[str, Any]:
        """Convert to dictionary suitable for dashboard display"""
        return {
            "summary": {
                "total_requests": self.total_requests,
                "total_paid": self.total_paid,
                "conversion_rate": f"{self.conversion_rate:.2%}",
                "unique_payers": len(self.top_payers)
            },
            "revenue": {
                "by_token": self.total_revenue,
                "by_endpoint": self.revenue_by_endpoint
            },
            "top_payers": [
                {
                    "address": f"{p.address[:6]}...{p.address[-4:]}",
                    "total": p.total,
                    "payments": p.count
                }
                for p in self.top_payers[:10]
            ]
        }