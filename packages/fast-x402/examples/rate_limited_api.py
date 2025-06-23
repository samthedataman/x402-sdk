"""Example of rate-limited API with x402 payments"""

from fastapi import FastAPI, Depends, HTTPException
from fast_x402 import X402Provider, X402Config, get_x402_payment
from fast_x402.security import RateLimiter
import asyncio
from datetime import datetime

app = FastAPI(title="Rate-Limited x402 API")

# Configure provider
provider = X402Provider(
    X402Config(
        wallet_address="0x742d35Cc6634C0532925a3b844Bc9e7595f6E123",
        analytics_enabled=True,
    )
)

# Rate limiters for different tiers
free_limiter = RateLimiter(max_requests=10, window_seconds=3600)  # 10/hour
paid_limiter = RateLimiter(max_requests=1000, window_seconds=3600)  # 1000/hour


@app.get("/api/free/data")
async def free_data(client_ip: str = "127.0.0.1"):
    """Free tier with strict rate limits"""
    if not free_limiter.is_allowed(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Upgrade to paid tier for higher limits."
        )
    
    return {
        "data": "Limited free data",
        "tier": "free",
        "remaining_requests": 10 - free_limiter.requests.get(client_ip, {}).get('count', 0)
    }


@app.post("/api/paid/data")
async def paid_data(payment = Depends(get_x402_payment), client_ip: str = "127.0.0.1"):
    """Paid tier with generous rate limits"""
    # Payment already verified by dependency
    payer = payment.from_address if payment else client_ip
    
    if not paid_limiter.is_allowed(payer):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded even for paid tier. Please wait."
        )
    
    # Simulate expensive computation
    await asyncio.sleep(0.1)
    
    return {
        "data": {
            "timestamp": datetime.utcnow().isoformat(),
            "premium_insights": ["insight1", "insight2", "insight3"],
            "advanced_metrics": {
                "score": 0.95,
                "confidence": 0.87,
                "recommendations": ["action1", "action2"]
            }
        },
        "tier": "paid",
        "payer": payer[:10] + "...",
        "remaining_requests": 1000 - paid_limiter.requests.get(payer, {}).get('count', 0)
    }


@app.get("/api/pricing")
async def pricing_info():
    """Show pricing tiers"""
    return {
        "tiers": {
            "free": {
                "cost": "$0.00",
                "rate_limit": "10 requests/hour",
                "features": ["Basic data access", "Limited API calls"]
            },
            "paid": {
                "cost": "$0.01 per request",
                "rate_limit": "1000 requests/hour",
                "features": [
                    "Premium data access",
                    "Advanced analytics",
                    "Real-time insights",
                    "Priority support"
                ]
            }
        },
        "payment_info": {
            "accepted_tokens": ["USDC"],
            "chain": "Base",
            "settlement_time": "~2 seconds"
        }
    }


# Add x402 middleware for paid endpoints
from fast_x402 import x402_middleware

app.add_middleware(
    x402_middleware,
    wallet_address=provider.config.wallet_address,
    routes={
        "/api/paid/*": "0.01",  # $0.01 per request
    }
)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)