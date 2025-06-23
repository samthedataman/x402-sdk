"""Facilitator service integration for x402 payments"""

import asyncio
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
import httpx

from .analytics import get_analytics, AnalyticsEvent


class PaymentStatus(str, Enum):
    """Payment status in facilitator"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


@dataclass
class FacilitatorConfig:
    """Configuration for facilitator service"""
    api_url: str = "https://facilitator.x402.io/v1"
    api_key: Optional[str] = None
    webhook_url: Optional[str] = None
    timeout: int = 30
    retry_attempts: int = 3
    cache_ttl: int = 300  # 5 minutes


class FacilitatorClient:
    """Client for interacting with x402 facilitator service"""
    
    def __init__(self, config: FacilitatorConfig):
        self.config = config
        self.analytics = get_analytics()
        self._payment_cache: Dict[str, Dict[str, Any]] = {}
        
    async def submit_payment(self, 
                           payment_data: Dict[str, Any],
                           provider_address: str,
                           metadata: Optional[Dict[str, Any]] = None) -> str:
        """Submit a payment to the facilitator for processing"""
        
        # Track facilitator usage
        if self.analytics:
            await self.analytics.track_event(
                AnalyticsEvent.FACILITATOR_VERIFICATION,
                wallet_address=payment_data.get("from_address"),
                provider_address=provider_address,
                amount=float(payment_data.get("value", 0)) / 1e6,
                metadata={"action": "submit"}
            )
        
        # Prepare request
        request_data = {
            "payment": payment_data,
            "provider": provider_address,
            "metadata": metadata or {},
            "webhook_url": self.config.webhook_url,
            "timestamp": time.time(),
        }
        
        # Submit to facilitator
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            headers = {}
            if self.config.api_key:
                headers["X-API-Key"] = self.config.api_key
                
            response = await client.post(
                f"{self.config.api_url}/payments",
                json=request_data,
                headers=headers,
            )
            response.raise_for_status()
            
            result = response.json()
            payment_id = result["payment_id"]
            
            # Cache the payment
            self._payment_cache[payment_id] = {
                "status": PaymentStatus.PENDING,
                "submitted_at": time.time(),
                "data": result,
            }
            
            return payment_id
    
    async def check_payment_status(self, payment_id: str) -> Dict[str, Any]:
        """Check the status of a payment in the facilitator"""
        
        # Check cache first
        if payment_id in self._payment_cache:
            cached = self._payment_cache[payment_id]
            if time.time() - cached["submitted_at"] < self.config.cache_ttl:
                return cached["data"]
        
        # Query facilitator
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            headers = {}
            if self.config.api_key:
                headers["X-API-Key"] = self.config.api_key
                
            response = await client.get(
                f"{self.config.api_url}/payments/{payment_id}",
                headers=headers,
            )
            response.raise_for_status()
            
            result = response.json()
            
            # Update cache
            self._payment_cache[payment_id] = {
                "status": result["status"],
                "submitted_at": time.time(),
                "data": result,
            }
            
            return result
    
    async def wait_for_payment(self, 
                             payment_id: str,
                             timeout: Optional[int] = None) -> Dict[str, Any]:
        """Wait for a payment to complete"""
        
        timeout = timeout or self.config.timeout
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status = await self.check_payment_status(payment_id)
            
            if status["status"] in [PaymentStatus.COMPLETED, PaymentStatus.FAILED]:
                return status
                
            await asyncio.sleep(1)  # Poll every second
        
        raise TimeoutError(f"Payment {payment_id} did not complete within {timeout}s")
    
    async def batch_submit_payments(self, 
                                  payments: List[Dict[str, Any]]) -> List[str]:
        """Submit multiple payments in a batch"""
        
        # Premium feature - check limit
        if self.analytics:
            can_use = await self.analytics.check_premium_limit(
                "batch_payments",
                payments[0].get("from_address", "unknown"),
                limit=100
            )
            if not can_use:
                raise ValueError("Batch payment limit reached")
        
        payment_ids = []
        
        # Submit payments concurrently
        tasks = []
        for payment in payments:
            task = self.submit_payment(
                payment["payment_data"],
                payment["provider_address"],
                payment.get("metadata")
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, str):
                payment_ids.append(result)
            else:
                payment_ids.append(None)
        
        return payment_ids
    
    async def get_payment_history(self,
                                wallet_address: Optional[str] = None,
                                provider_address: Optional[str] = None,
                                limit: int = 100) -> List[Dict[str, Any]]:
        """Get payment history from facilitator"""
        
        params = {"limit": limit}
        if wallet_address:
            params["wallet"] = wallet_address
        if provider_address:
            params["provider"] = provider_address
        
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            headers = {}
            if self.config.api_key:
                headers["X-API-Key"] = self.config.api_key
                
            response = await client.get(
                f"{self.config.api_url}/payments",
                params=params,
                headers=headers,
            )
            response.raise_for_status()
            
            return response.json()["payments"]
    
    async def register_provider(self,
                              provider_address: str,
                              metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Register a provider with the facilitator"""
        
        request_data = {
            "address": provider_address,
            "metadata": metadata,
            "registered_at": time.time(),
        }
        
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            headers = {}
            if self.config.api_key:
                headers["X-API-Key"] = self.config.api_key
                
            response = await client.post(
                f"{self.config.api_url}/providers",
                json=request_data,
                headers=headers,
            )
            response.raise_for_status()
            
            return response.json()
    
    async def get_provider_stats(self, provider_address: str) -> Dict[str, Any]:
        """Get provider statistics from facilitator"""
        
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            headers = {}
            if self.config.api_key:
                headers["X-API-Key"] = self.config.api_key
                
            response = await client.get(
                f"{self.config.api_url}/providers/{provider_address}/stats",
                headers=headers,
            )
            response.raise_for_status()
            
            return response.json()


class PremiumFacilitator(FacilitatorClient):
    """Premium facilitator with additional features"""
    
    async def instant_settlement(self,
                               payment_id: str,
                               settlement_address: str) -> Dict[str, Any]:
        """Request instant settlement for a payment (premium feature)"""
        
        # Check premium limit
        if self.analytics:
            payment = await self.check_payment_status(payment_id)
            can_use = await self.analytics.check_premium_limit(
                "instant_settlement",
                payment["payment"]["from_address"],
                limit=10
            )
            if not can_use:
                raise ValueError("Instant settlement limit reached")
        
        request_data = {
            "payment_id": payment_id,
            "settlement_address": settlement_address,
            "requested_at": time.time(),
        }
        
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            headers = {"X-API-Key": self.config.api_key}
            
            response = await client.post(
                f"{self.config.api_url}/settlements/instant",
                json=request_data,
                headers=headers,
            )
            response.raise_for_status()
            
            return response.json()
    
    async def create_payment_link(self,
                                amount: str,
                                provider_address: str,
                                description: str,
                                expires_in: int = 3600) -> Dict[str, Any]:
        """Create a payment link (premium feature)"""
        
        request_data = {
            "amount": amount,
            "provider": provider_address,
            "description": description,
            "expires_at": time.time() + expires_in,
        }
        
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            headers = {"X-API-Key": self.config.api_key}
            
            response = await client.post(
                f"{self.config.api_url}/payment-links",
                json=request_data,
                headers=headers,
            )
            response.raise_for_status()
            
            return response.json()
    
    async def bulk_verification(self,
                              payment_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """Verify multiple payments in bulk (premium feature)"""
        
        request_data = {"payment_ids": payment_ids}
        
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            headers = {"X-API-Key": self.config.api_key}
            
            response = await client.post(
                f"{self.config.api_url}/verify/bulk",
                json=request_data,
                headers=headers,
            )
            response.raise_for_status()
            
            return response.json()["results"]