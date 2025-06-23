"""Shared analytics backend for x402 SDKs"""

import time
import json
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from collections import defaultdict
from enum import Enum
import httpx


class AnalyticsEvent(str, Enum):
    """Types of analytics events"""
    PAYMENT_REQUESTED = "payment_requested"
    PAYMENT_COMPLETED = "payment_completed"
    PAYMENT_FAILED = "payment_failed"
    WALLET_CREATED = "wallet_created"
    SPENDING_LIMIT_REACHED = "spending_limit_reached"
    API_CALL = "api_call"
    FACILITATOR_VERIFICATION = "facilitator_verification"
    

class AnalyticsBackend:
    """Centralized analytics for tracking usage and monetization"""
    
    def __init__(self, 
                 api_key: Optional[str] = None,
                 endpoint: Optional[str] = None,
                 batch_size: int = 100,
                 flush_interval: int = 60):
        
        self.api_key = api_key
        self.endpoint = endpoint or "https://analytics.x402.io/v1/events"
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        
        # In-memory storage
        self.events_queue: List[Dict[str, Any]] = []
        self.metrics = {
            "total_payments": 0,
            "total_revenue": 0.0,
            "failed_payments": 0,
            "unique_wallets": set(),
            "unique_providers": set(),
            "revenue_by_provider": defaultdict(float),
            "revenue_by_wallet": defaultdict(float),
            "payments_by_hour": defaultdict(int),
            "api_calls_by_endpoint": defaultdict(int),
        }
        
        # Premium features tracking
        self.premium_usage = {
            "facilitator_verifications": 0,
            "analytics_api_calls": 0,
            "bulk_payment_requests": 0,
            "custom_rate_limits": 0,
        }
        
        # Start background task for flushing events
        self._flush_task = None
        
    async def start(self):
        """Start the analytics backend"""
        self._flush_task = asyncio.create_task(self._periodic_flush())
        
    async def stop(self):
        """Stop the analytics backend and flush remaining events"""
        if self._flush_task:
            self._flush_task.cancel()
        await self.flush()
        
    async def track_event(self, 
                         event_type: AnalyticsEvent,
                         wallet_address: Optional[str] = None,
                         provider_address: Optional[str] = None,
                         amount: Optional[float] = None,
                         metadata: Optional[Dict[str, Any]] = None):
        """Track an analytics event"""
        
        event = {
            "type": event_type.value,
            "timestamp": time.time(),
            "wallet_address": wallet_address,
            "provider_address": provider_address,
            "amount": amount,
            "metadata": metadata or {},
        }
        
        self.events_queue.append(event)
        
        # Update real-time metrics
        self._update_metrics(event)
        
        # Check if we should flush
        if len(self.events_queue) >= self.batch_size:
            await self.flush()
            
    def _update_metrics(self, event: Dict[str, Any]):
        """Update in-memory metrics"""
        
        event_type = event["type"]
        
        if event_type == AnalyticsEvent.PAYMENT_COMPLETED.value:
            # Convert amount to float if it's a string
            amount = event.get("amount", 0)
            if isinstance(amount, str):
                try:
                    amount = float(amount)
                except (ValueError, TypeError):
                    amount = 0.0
            
            self.metrics["total_payments"] += 1
            self.metrics["total_revenue"] += amount
            
            if event.get("wallet_address"):
                self.metrics["unique_wallets"].add(event["wallet_address"])
                self.metrics["revenue_by_wallet"][event["wallet_address"]] += amount
                
            if event.get("provider_address"):
                self.metrics["unique_providers"].add(event["provider_address"])
                self.metrics["revenue_by_provider"][event["provider_address"]] += amount
                
            # Track hourly patterns
            hour = datetime.fromtimestamp(event["timestamp"]).hour
            self.metrics["payments_by_hour"][hour] += 1
            
        elif event_type == AnalyticsEvent.PAYMENT_FAILED.value:
            self.metrics["failed_payments"] += 1
            
        elif event_type == AnalyticsEvent.API_CALL.value:
            endpoint = event.get("metadata", {}).get("endpoint", "unknown")
            self.metrics["api_calls_by_endpoint"][endpoint] += 1
            
        elif event_type == AnalyticsEvent.FACILITATOR_VERIFICATION.value:
            self.premium_usage["facilitator_verifications"] += 1
            
    async def flush(self):
        """Flush events to remote analytics service"""
        
        if not self.events_queue:
            return
            
        events_to_send = self.events_queue[:self.batch_size]
        self.events_queue = self.events_queue[self.batch_size:]
        
        if self.api_key and self.endpoint:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        self.endpoint,
                        json={"events": events_to_send},
                        headers={"X-API-Key": self.api_key},
                        timeout=10.0,
                    )
                    response.raise_for_status()
            except Exception as e:
                # In production, implement retry logic
                print(f"Failed to send analytics: {e}")
                # Re-add events to queue
                self.events_queue = events_to_send + self.events_queue
                
    async def _periodic_flush(self):
        """Periodically flush events"""
        
        while True:
            await asyncio.sleep(self.flush_interval)
            await self.flush()
            
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics"""
        
        return {
            "total_payments": self.metrics["total_payments"],
            "total_revenue": self.metrics["total_revenue"],
            "failed_payments": self.metrics["failed_payments"],
            "unique_wallets": len(self.metrics["unique_wallets"]),
            "unique_providers": len(self.metrics["unique_providers"]),
            "success_rate": (
                self.metrics["total_payments"] / 
                (self.metrics["total_payments"] + self.metrics["failed_payments"])
                if self.metrics["total_payments"] + self.metrics["failed_payments"] > 0
                else 0
            ),
            "average_payment": (
                self.metrics["total_revenue"] / self.metrics["total_payments"]
                if self.metrics["total_payments"] > 0
                else 0
            ),
            "top_providers": sorted(
                self.metrics["revenue_by_provider"].items(),
                key=lambda x: x[1],
                reverse=True
            )[:10],
            "top_wallets": sorted(
                self.metrics["revenue_by_wallet"].items(), 
                key=lambda x: x[1],
                reverse=True
            )[:10],
            "hourly_distribution": dict(self.metrics["payments_by_hour"]),
            "premium_usage": dict(self.premium_usage),
        }
        
    def get_wallet_metrics(self, wallet_address: str) -> Dict[str, Any]:
        """Get metrics for a specific wallet"""
        
        return {
            "total_spent": self.metrics["revenue_by_wallet"].get(wallet_address, 0),
            "is_active": wallet_address in self.metrics["unique_wallets"],
        }
        
    def get_provider_metrics(self, provider_address: str) -> Dict[str, Any]:
        """Get metrics for a specific provider"""
        
        return {
            "total_revenue": self.metrics["revenue_by_provider"].get(provider_address, 0),
            "is_active": provider_address in self.metrics["unique_providers"],
        }
        
    async def check_premium_limit(self, 
                                 feature: str,
                                 wallet_address: str,
                                 limit: int = 1000) -> bool:
        """Check if wallet has reached premium feature limit"""
        
        # In production, check against database
        # For now, simple in-memory check
        
        usage_key = f"{feature}:{wallet_address}"
        current_usage = self.premium_usage.get(usage_key, 0)
        
        if current_usage >= limit:
            await self.track_event(
                AnalyticsEvent.SPENDING_LIMIT_REACHED,
                wallet_address=wallet_address,
                metadata={"feature": feature, "limit": limit}
            )
            return False
            
        self.premium_usage[usage_key] = current_usage + 1
        return True
        
    def export_metrics(self, format: str = "json") -> str:
        """Export metrics in various formats"""
        
        metrics = self.get_metrics()
        
        if format == "json":
            return json.dumps(metrics, indent=2, default=str)
        elif format == "csv":
            # Simple CSV export
            lines = ["metric,value"]
            for key, value in metrics.items():
                if not isinstance(value, (list, dict)):
                    lines.append(f"{key},{value}")
            return "\n".join(lines)
        else:
            raise ValueError(f"Unsupported format: {format}")


# Global analytics instance
_analytics = None


def get_analytics() -> AnalyticsBackend:
    """Get the global analytics instance"""
    global _analytics
    if _analytics is None:
        _analytics = AnalyticsBackend()
    return _analytics


async def init_analytics(api_key: Optional[str] = None, 
                        endpoint: Optional[str] = None):
    """Initialize the global analytics instance"""
    global _analytics
    _analytics = AnalyticsBackend(api_key=api_key, endpoint=endpoint)
    await _analytics.start()
    return _analytics