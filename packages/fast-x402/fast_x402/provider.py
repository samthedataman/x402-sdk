"""Core X402Provider implementation"""

import asyncio
import secrets
import time
from typing import Dict, Optional, List, Callable, Any, Tuple
from datetime import datetime
from collections import defaultdict
import sys
import os

import httpx
from web3 import Web3

from .models import (
    X402Config,
    PaymentRequirement,
    PaymentData,
    PaymentVerification,
    X402Analytics,
    PayerStats,
)
from .exceptions import X402Error, InvalidPaymentError, InvalidSignatureError
from .verification import verify_eip712_signature, verify_payment_requirements
from .logger import logger

try:
    from .shared.wallet import WalletManager, generate_wallet
    from .shared.analytics import get_analytics, AnalyticsEvent
except ImportError:
    # Fallback if shared module not available
    WalletManager = None
    get_analytics = None
    AnalyticsEvent = None


class X402Provider:
    """Main provider class for x402 payment processing"""
    
    def __init__(self, config: X402Config):
        self.config = config
        
        # Initialize wallet if not provided
        if not config.wallet_address and WalletManager:
            self.wallet_manager = WalletManager()
            wallet_data, created = self.wallet_manager.create_or_load_wallet("provider")
            config.wallet_address = wallet_data["address"]
            if created:
                logger.info(f"Created new provider wallet: {config.wallet_address}")
                logger.warning(f"IMPORTANT: Save your private key securely!")
                logger.warning(f"Private key: {wallet_data['private_key']}")
                logger.warning(f"Mnemonic: {wallet_data['mnemonic']}")
        else:
            self.wallet_manager = None
        
        # Initialize shared analytics
        self.analytics = get_analytics() if get_analytics else None
        
        # Local analytics data
        self.analytics_data = {
            "requests": 0,
            "paid": 0,
            "revenue": defaultdict(int),
            "payers": defaultdict(lambda: {"total": 0, "count": 0, "last": None}),
            "endpoints": defaultdict(lambda: defaultdict(int)),
        }
        self.payment_cache: Dict[str, PaymentVerification] = {}
        self._cache_lock = asyncio.Lock()
        
        logger.info(f"Initializing X402Provider with wallet {config.wallet_address[:8]}...")
        logger.debug(f"Chain ID: {config.chain_id}, Accepted tokens: {len(config.accepted_tokens)}")
        
        # Start cache cleanup task if caching is enabled
        if self.config.cache_enabled:
            asyncio.create_task(self._cache_cleanup_task())
            logger.debug("Cache cleanup task started")
    
    def create_payment_requirement(
        self,
        amount: str,
        endpoint: Optional[str] = None,
        token: Optional[str] = None,
        scheme: str = "exact",
    ) -> PaymentRequirement:
        """Create a payment requirement for HTTP 402 response"""
        
        self.analytics_data["requests"] += 1
        
        if endpoint and endpoint not in self.analytics_data["endpoints"]:
            self.analytics_data["endpoints"][endpoint] = defaultdict(int)
        
        # Track payment request in shared analytics
        if self.analytics and AnalyticsEvent:
            asyncio.create_task(self.analytics.track_event(
                AnalyticsEvent.PAYMENT_REQUESTED,
                provider_address=self.config.wallet_address,
                amount=float(amount),
                metadata={
                    "endpoint": endpoint,
                    "token": token or self.config.accepted_tokens[0],
                    "scheme": scheme,
                }
            ))
        
        nonce = "0x" + secrets.token_hex(32)
        expires_at = int(time.time()) + 300  # 5 minutes
        
        return PaymentRequirement(
            amount=amount,
            token=token or self.config.accepted_tokens[0],
            recipient=self.config.wallet_address,
            chain_id=self.config.chain_id,
            nonce=nonce,
            expires_at=expires_at,
            scheme=scheme,
        )
    
    async def verify_payment(
        self,
        payment_data: PaymentData,
        requirement: PaymentRequirement,
        endpoint: Optional[str] = None,
    ) -> PaymentVerification:
        """Verify a payment against requirements"""
        
        try:
            # Check cache first
            cache_key = f"{payment_data.signature}-{payment_data.nonce}"
            if self.config.cache_enabled:
                async with self._cache_lock:
                    if cache_key in self.payment_cache:
                        return self.payment_cache[cache_key]
            
            # Verify payment requirements
            verify_payment_requirements(
                payment_data,
                requirement.amount,
                requirement.token,
                requirement.recipient,
                requirement.chain_id,
                requirement.scheme,
            )
            
            # Verify signature
            if not verify_eip712_signature(payment_data):
                raise InvalidSignatureError("Invalid payment signature")
            
            # Custom validation if provided
            if self.config.custom_validation:
                custom_result = await self._run_custom_validation(payment_data)
                if not custom_result:
                    raise InvalidPaymentError("Custom validation failed", "CUSTOM_VALIDATION_FAILED")
            
            # Update analytics
            await self._update_analytics(payment_data, endpoint)
            
            # Track successful payment in shared analytics
            if self.analytics and AnalyticsEvent:
                await self.analytics.track_event(
                    AnalyticsEvent.PAYMENT_COMPLETED,
                    wallet_address=payment_data.from_address,
                    provider_address=self.config.wallet_address,
                    amount=float(payment_data.value) / 1e6,  # Convert from USDC units
                    metadata={
                        "token": payment_data.token,
                        "chain_id": payment_data.chain_id,
                        "endpoint": endpoint,
                    }
                )
            
            # Create verification result
            verification = PaymentVerification(
                valid=True,
                transaction_hash="0x" + secrets.token_hex(32),  # Mock for now
            )
            
            # Cache the result
            if self.config.cache_enabled:
                async with self._cache_lock:
                    self.payment_cache[cache_key] = verification
            
            # Send webhook if configured
            if self.config.analytics_webhook:
                asyncio.create_task(self._send_webhook(payment_data, endpoint))
            
            return verification
            
        except X402Error as e:
            # Track failed payment in shared analytics
            if self.analytics and AnalyticsEvent:
                await self.analytics.track_event(
                    AnalyticsEvent.PAYMENT_FAILED,
                    wallet_address=payment_data.from_address if payment_data else None,
                    provider_address=self.config.wallet_address,
                    metadata={"reason": str(e), "endpoint": endpoint}
                )
            raise
        except Exception as e:
            # Track failed payment in shared analytics
            if self.analytics and AnalyticsEvent:
                await self.analytics.track_event(
                    AnalyticsEvent.PAYMENT_FAILED,
                    wallet_address=payment_data.from_address if payment_data else None,
                    provider_address=self.config.wallet_address,
                    metadata={"reason": str(e), "endpoint": endpoint}
                )
            raise InvalidPaymentError(f"Payment verification failed: {str(e)}")
    
    async def _run_custom_validation(self, payment_data: PaymentData) -> bool:
        """Run custom validation if it's async, otherwise run it sync"""
        if asyncio.iscoroutinefunction(self.config.custom_validation):
            return await self.config.custom_validation(payment_data)
        else:
            return self.config.custom_validation(payment_data)
    
    async def _update_analytics(self, payment_data: PaymentData, endpoint: Optional[str] = None):
        """Update analytics data"""
        self.analytics_data["paid"] += 1
        
        # Update revenue
        token = payment_data.token.lower()
        amount = int(payment_data.value)
        self.analytics_data["revenue"][token] += amount
        
        # Update payer stats
        payer = payment_data.from_address.lower()
        payer_data = self.analytics_data["payers"][payer]
        payer_data["total"] += amount
        payer_data["count"] += 1
        payer_data["last"] = datetime.utcnow()
        
        # Update endpoint stats
        if endpoint:
            self.analytics_data["endpoints"][endpoint][token] += amount
    
    def get_analytics(self) -> X402Analytics:
        """Get current analytics data"""
        
        # Calculate conversion rate
        total_requests = self.analytics_data["requests"]
        total_paid = self.analytics_data["paid"]
        conversion_rate = total_paid / total_requests if total_requests > 0 else 0.0
        
        # Get top payers
        top_payers = []
        for address, data in self.analytics_data["payers"].items():
            if data["count"] > 0:
                top_payers.append(
                    PayerStats(
                        address=address,
                        total=str(data["total"]),
                        count=data["count"],
                        last_payment=data["last"] or datetime.utcnow(),
                    )
                )
        
        # Sort by total amount
        top_payers.sort(key=lambda x: int(x.total), reverse=True)
        
        # Convert revenue to strings
        total_revenue = {
            token: str(amount) 
            for token, amount in self.analytics_data["revenue"].items()
        }
        
        # Convert endpoint revenue to strings
        revenue_by_endpoint = {}
        for endpoint, tokens in self.analytics_data["endpoints"].items():
            revenue_by_endpoint[endpoint] = {
                token: str(amount) 
                for token, amount in tokens.items()
            }
        
        return X402Analytics(
            total_requests=total_requests,
            total_paid=total_paid,
            total_revenue=total_revenue,
            conversion_rate=conversion_rate,
            top_payers=top_payers[:10],  # Top 10 payers
            revenue_by_endpoint=revenue_by_endpoint,
        )
    
    async def _cache_cleanup_task(self):
        """Periodically clean up expired cache entries"""
        while True:
            await asyncio.sleep(60)  # Run every minute
            async with self._cache_lock:
                # Simple cleanup - remove oldest entries if cache is too large
                if len(self.payment_cache) > 10000:
                    # Remove half of the entries (oldest first)
                    keys_to_remove = list(self.payment_cache.keys())[:5000]
                    for key in keys_to_remove:
                        del self.payment_cache[key]
    
    async def _send_webhook(self, payment_data: PaymentData, endpoint: Optional[str] = None):
        """Send webhook notification"""
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    self.config.analytics_webhook,
                    json={
                        "type": "payment_received",
                        "payment": payment_data.model_dump(),
                        "endpoint": endpoint,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                    timeout=5.0,
                )
        except Exception:
            # Silently fail - don't block payment processing
            pass
    
    def create_wallet(self, name: Optional[str] = None) -> Tuple[str, str]:
        """Create a new wallet for the provider"""
        if not WalletManager:
            raise RuntimeError("Wallet creation not available - install mnemonic package")
        
        wallet_name = name or f"provider_{int(time.time())}"
        manager = WalletManager()
        wallet_data = manager.create_wallet(wallet_name)
        
        # Track wallet creation
        if self.analytics and AnalyticsEvent:
            asyncio.create_task(self.analytics.track_event(
                AnalyticsEvent.WALLET_CREATED,
                wallet_address=wallet_data["address"],
                metadata={"type": "provider", "name": wallet_name}
            ))
        
        return wallet_data["address"], wallet_data["private_key"]
    
    def export_wallet(self, include_private_key: bool = False) -> Dict[str, str]:
        """Export wallet information"""
        if self.wallet_manager:
            return self.wallet_manager.export_wallet("provider", include_private_key)
        else:
            return {"address": self.config.wallet_address}
    
    def get_shared_analytics(self) -> Optional[Dict[str, Any]]:
        """Get metrics from shared analytics backend"""
        if self.analytics:
            return self.analytics.get_provider_metrics(self.config.wallet_address)
        return None