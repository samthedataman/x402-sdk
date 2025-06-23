"""Data models for x402-langchain"""

from typing import Dict, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


class PaymentRequirement(BaseModel):
    """Payment requirement from HTTP 402 response"""
    amount: str
    token: str
    recipient: str
    chain_id: int = Field(alias="chainId")
    nonce: str
    expires_at: int = Field(alias="expiresAt")
    scheme: str = "exact"
    
    class Config:
        populate_by_name = True


class PaymentAuthorization(BaseModel):
    """Signed payment authorization"""
    from_address: str = Field(alias="from")
    to: str
    value: str
    token: str
    chain_id: int = Field(alias="chainId")
    nonce: str
    valid_before: int = Field(alias="validBefore")
    signature: str
    
    class Config:
        populate_by_name = True
        
    def to_header(self) -> str:
        """Convert to X-Payment header value"""
        return self.model_dump_json(by_alias=True)


class PaymentResult(BaseModel):
    """Result of a payment attempt"""
    success: bool
    url: str
    amount: str
    token: str
    transaction_hash: Optional[str] = None
    data: Optional[Any] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    
class PaymentHistory(BaseModel):
    """Payment history entry"""
    url: str
    amount: str
    token: str
    success: bool
    timestamp: datetime
    transaction_hash: Optional[str] = None
    error: Optional[str] = None