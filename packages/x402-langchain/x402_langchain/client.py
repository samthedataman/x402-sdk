"""x402 client for making payments"""

import asyncio
import time
from typing import Dict, Optional, Any, Union
from urllib.parse import urlparse
import re

import httpx
from eth_account import Account
from eth_account.messages import encode_typed_data
from web3 import Web3

from .config import X402Config
from .models import PaymentRequirement, PaymentAuthorization, PaymentResult
from .exceptions import (
    PaymentError,
    SpendingLimitError,
    DomainNotAllowedError,
    PaymentDeniedError,
    InvalidPaymentRequirementError,
    PaymentTimeoutError,
)
from .logger import logger


class X402Client:
    """Client for making x402 payments"""
    
    def __init__(self, config: X402Config):
        self.config = config
        self.account = Account.from_key(config.private_key)
        self.config.wallet_address = self.account.address
        self.spent_today = 0.0
        self.spent_hour = 0.0
        self.last_hour_reset = time.time()
        self.last_day_reset = time.time()
        
    async def fetch_with_payment(
        self,
        url: str,
        max_amount: float = None,
        method: str = "GET",
        **kwargs
    ) -> PaymentResult:
        """Fetch a URL, automatically handling x402 payments"""
        
        # Check domain restrictions
        domain = urlparse(url).netloc
        if self.config.allowed_domains and domain not in self.config.allowed_domains:
            raise DomainNotAllowedError(f"Domain {domain} not in allowed list")
        if domain in self.config.blocked_domains:
            raise DomainNotAllowedError(f"Domain {domain} is blocked")
        
        # First request without payment
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.request(method, url, **kwargs)
            
            # If not 402, return the response
            if response.status_code != 402:
                return PaymentResult(
                    success=True,
                    url=url,
                    amount="0",
                    token="",
                    data=response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text,
                )
            
            # Parse payment requirement
            try:
                requirement = PaymentRequirement(**response.json())
            except Exception as e:
                raise InvalidPaymentRequirementError(f"Invalid payment requirement: {e}")
            
            # Check amount limits
            amount = float(requirement.amount)
            if max_amount and amount > max_amount:
                raise SpendingLimitError(f"Required amount {amount} exceeds max {max_amount}")
            
            # Check spending limits
            if not self._check_spending_limits(amount):
                if self.analytics and AnalyticsEvent:
                    asyncio.create_task(self.analytics.track_event(
                        AnalyticsEvent.SPENDING_LIMIT_REACHED,
                        wallet_address=self.account.address,
                        amount=amount,
                        metadata={"url": url}
                    ))
                raise SpendingLimitError(f"Payment would exceed spending limits")
            
            # Get approval if needed
            if not await self._get_approval(url, amount):
                raise PaymentDeniedError(f"Payment denied for {url}")
            
            # Create and sign payment
            payment_auth = self._create_payment_authorization(requirement)
            
            # Retry with payment
            headers = kwargs.get("headers", {})
            headers["X-Payment"] = payment_auth.to_header()
            kwargs["headers"] = headers
            
            try:
                payment_response = await client.request(method, url, **kwargs)
                
                if payment_response.status_code == 200:
                    # Update spending tracking
                    self._update_spending(amount)
                    
                    # Log payment if enabled
                    if self.config.log_payments:
                        await self._log_payment(url, amount, requirement.token, True)
                    
                    return PaymentResult(
                        success=True,
                        url=url,
                        amount=requirement.amount,
                        token=requirement.token,
                        transaction_hash=payment_response.headers.get("X-Payment-Confirmation"),
                        data=payment_response.json() if payment_response.headers.get("content-type", "").startswith("application/json") else payment_response.text,
                    )
                else:
                    error = f"Payment failed: {payment_response.status_code} {payment_response.text}"
                    if self.config.log_payments:
                        await self._log_payment(url, amount, requirement.token, False, error)
                    
                    return PaymentResult(
                        success=False,
                        url=url,
                        amount=requirement.amount,
                        token=requirement.token,
                        error=error,
                    )
                    
            except httpx.TimeoutException:
                raise PaymentTimeoutError(f"Payment request timed out for {url}")
    
    def _create_payment_authorization(self, requirement: PaymentRequirement) -> PaymentAuthorization:
        """Create and sign payment authorization"""
        
        # Convert amount to token units (USDC has 6 decimals)
        value_wei = Web3.to_wei(float(requirement.amount), "mwei")
        
        # Create EIP-712 message
        message = {
            "types": {
                "EIP712Domain": [
                    {"name": "name", "type": "string"},
                    {"name": "version", "type": "string"},
                    {"name": "chainId", "type": "uint256"},
                    {"name": "verifyingContract", "type": "address"},
                ],
                "TransferWithAuthorization": [
                    {"name": "from", "type": "address"},
                    {"name": "to", "type": "address"},
                    {"name": "value", "type": "uint256"},
                    {"name": "validBefore", "type": "uint256"},
                    {"name": "nonce", "type": "bytes32"},
                ],
            },
            "primaryType": "TransferWithAuthorization",
            "domain": {
                "name": "USDC",
                "version": "2",
                "chainId": requirement.chain_id,
                "verifyingContract": requirement.token,
            },
            "message": {
                "from": self.account.address,
                "to": requirement.recipient,
                "value": value_wei,
                "validBefore": requirement.expires_at,
                "nonce": requirement.nonce,
            },
        }
        
        # Sign the message
        encoded_message = encode_typed_data(message)
        signed = self.account.sign_message(encoded_message)
        
        return PaymentAuthorization(
            from_address=self.account.address,
            to=requirement.recipient,
            value=str(value_wei),
            token=requirement.token,
            chain_id=requirement.chain_id,
            nonce=requirement.nonce,
            valid_before=requirement.expires_at,
            signature=signed.signature.hex(),
        )
    
    def _check_spending_limits(self, amount: float) -> bool:
        """Check if payment is within spending limits"""
        
        # Reset hourly/daily counters if needed
        current_time = time.time()
        if current_time - self.last_hour_reset > 3600:
            self.spent_hour = 0.0
            self.last_hour_reset = current_time
        if current_time - self.last_day_reset > 86400:
            self.spent_today = 0.0
            self.last_day_reset = current_time
        
        limits = self.config.spending_limits
        
        # Check per-request limit
        if amount > limits.per_request:
            return False
        
        # Check hourly limit
        if self.spent_hour + amount > limits.per_hour:
            return False
        
        # Check daily limit
        if self.spent_today + amount > limits.per_day:
            return False
        
        return True
    
    async def _get_approval(self, url: str, amount: float) -> bool:
        """Get approval for payment"""
        
        # Auto-approve if configured
        if self.config.auto_approve:
            return True
        
        # Use approval callback if provided
        if self.config.approval_callback:
            if asyncio.iscoroutinefunction(self.config.approval_callback):
                return await self.config.approval_callback(url, amount)
            else:
                return self.config.approval_callback(url, amount)
        
        # Default to approved if no callback
        return True
    
    def _update_spending(self, amount: float):
        """Update spending trackers"""
        self.spent_hour += amount
        self.spent_today += amount
    
    async def _log_payment(
        self, 
        url: str, 
        amount: float, 
        token: str, 
        success: bool,
        error: Optional[str] = None
    ):
        """Log payment attempt"""
        # In production, this would write to a database or file
        print(f"Payment {'succeeded' if success else 'failed'}: {url} - ${amount}")
        
        # Send webhook if configured
        if self.config.webhook_url:
            try:
                async with httpx.AsyncClient() as client:
                    await client.post(
                        self.config.webhook_url,
                        json={
                            "type": "payment_attempt",
                            "url": url,
                            "amount": amount,
                            "token": token,
                            "success": success,
                            "error": error,
                            "wallet": self.account.address,
                            "timestamp": time.time(),
                        },
                        timeout=5.0,
                    )
            except:
                pass  # Don't fail on webhook errors
    
    def get_spending_status(self) -> Dict[str, Any]:
        """Get current spending status"""
        return {
            "wallet_address": self.account.address,
            "spent_today": self.spent_today,
            "spent_hour": self.spent_hour,
            "limits": {
                "per_request": self.config.spending_limits.per_request,
                "per_hour": self.config.spending_limits.per_hour,
                "per_day": self.config.spending_limits.per_day,
            },
            "remaining": {
                "hour": self.config.spending_limits.per_hour - self.spent_hour,
                "day": self.config.spending_limits.per_day - self.spent_today,
            },
        }