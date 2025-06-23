"""FastAPI dependencies for x402 payments"""

from typing import Optional, Annotated
from fastapi import Header, HTTPException, Depends, Request
import json

from .models import PaymentData, PaymentVerification
from .exceptions import PaymentRequiredError


class X402Dependency:
    """Dependency for requiring x402 payment on specific endpoints"""
    
    def __init__(self, amount: str, token: Optional[str] = None, scheme: str = "exact"):
        self.amount = amount
        self.token = token
        self.scheme = scheme
    
    async def __call__(
        self,
        request: Request,
        x_payment: Annotated[Optional[str], Header()] = None,
    ) -> PaymentData:
        """Validate payment for this endpoint"""
        
        if not x_payment:
            raise HTTPException(
                status_code=402,
                detail="Payment required",
                headers={"X-Payment-Required": "true"},
            )
        
        # Check if middleware already verified this payment
        if hasattr(request.state, "x402_payment"):
            return request.state.x402_payment
        
        try:
            # Parse payment data
            payment_data = PaymentData.model_validate_json(x_payment)
            return payment_data
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid payment data: {str(e)}",
            )


async def get_x402_payment(request: Request) -> Optional[PaymentData]:
    """Get x402 payment from request if available"""
    if hasattr(request.state, "x402_payment"):
        return request.state.x402_payment
    return None


async def get_x402_verification(request: Request) -> Optional[PaymentVerification]:
    """Get x402 payment verification from request if available"""
    if hasattr(request.state, "x402_verification"):
        return request.state.x402_verification
    return None


# Convenience functions for common amounts
def require_payment(amount: str, token: Optional[str] = None) -> X402Dependency:
    """Create a payment requirement dependency"""
    return X402Dependency(amount, token)


# Pre-configured dependencies for common amounts
Payment1Cent = X402Dependency("0.01")
Payment10Cents = X402Dependency("0.10")
Payment1Dollar = X402Dependency("1.00")