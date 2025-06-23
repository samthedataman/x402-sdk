"""Example of a pay-per-use API with x402 and premium tiers"""

import os
import sys
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional
import asyncio

from fast_x402 import X402Provider, X402Config, X402Middleware
from fast_x402.models import PaymentData
try:
    from fast_x402.shared.analytics import get_analytics, init_analytics, AnalyticsEvent
    from fast_x402.shared.facilitator import FacilitatorClient, FacilitatorConfig, PremiumFacilitator
except ImportError:
    # If running from source, try parent path
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
    from shared.analytics import get_analytics, init_analytics, AnalyticsEvent
    from shared.facilitator import FacilitatorClient, FacilitatorConfig, PremiumFacilitator


# Initialize FastAPI app
app = FastAPI(title="Premium Data API", version="1.0.0")

# Initialize x402 provider with auto-wallet creation
config = X402Config(
    # No wallet_address - will auto-create
    chain_id=8453,  # Base
    accepted_tokens=["0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"],  # USDC
    cache_enabled=True,
)

provider = X402Provider(config)

# Initialize facilitator for premium features
facilitator_config = FacilitatorConfig(
    api_url=os.getenv("FACILITATOR_URL", "https://facilitator.x402.io/v1"),
    api_key=os.getenv("FACILITATOR_API_KEY"),
)
facilitator = PremiumFacilitator(facilitator_config)

# Initialize analytics
analytics = None

@app.on_event("startup")
async def startup_event():
    global analytics
    analytics = await init_analytics(
        api_key=os.getenv("ANALYTICS_API_KEY"),
        endpoint=os.getenv("ANALYTICS_ENDPOINT")
    )
    print(f"🚀 API started with wallet: {provider.config.wallet_address}")
    
    # Register provider with facilitator
    try:
        await facilitator.register_provider(
            provider.config.wallet_address,
            {
                "name": "Premium Data API",
                "description": "High-quality data feeds with x402 payments",
                "endpoints": [
                    "/api/weather",
                    "/api/market-data", 
                    "/api/predictions"
                ]
            }
        )
        print("✅ Registered with facilitator service")
    except Exception as e:
        print(f"⚠️  Facilitator registration failed: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    if analytics:
        await analytics.stop()


# Pricing tiers
PRICING_TIERS = {
    "weather": {
        "basic": 0.01,      # Basic weather data
        "premium": 0.05,    # Detailed forecast
        "enterprise": 0.10, # Historical + ML predictions
    },
    "market": {
        "delayed": 0.02,    # 15-min delayed
        "realtime": 0.10,   # Real-time data
        "analytics": 0.25,  # With technical analysis
    },
    "predictions": {
        "simple": 0.05,     # Basic ML model
        "advanced": 0.20,   # Advanced ensemble
        "custom": 0.50,     # Custom model
    }
}


def get_tier_from_payment(amount: float, endpoint: str) -> str:
    """Determine tier based on payment amount"""
    tiers = PRICING_TIERS.get(endpoint, {})
    
    # Find the highest tier the payment covers
    selected_tier = "basic"
    for tier, price in sorted(tiers.items(), key=lambda x: x[1]):
        if amount >= price:
            selected_tier = tier
    
    return selected_tier


# Add x402 middleware for automatic payment handling
app.add_middleware(
    X402Middleware,
    provider=provider,
    paths={
        "/api/weather/*": lambda req: provider.create_payment_requirement(
            amount=str(PRICING_TIERS["weather"]["basic"]),
            endpoint="/api/weather"
        ),
        "/api/market-data/*": lambda req: provider.create_payment_requirement(
            amount=str(PRICING_TIERS["market"]["delayed"]),
            endpoint="/api/market-data"
        ),
        "/api/predictions/*": lambda req: provider.create_payment_requirement(
            amount=str(PRICING_TIERS["predictions"]["simple"]),
            endpoint="/api/predictions"
        ),
    }
)


# Free endpoint - no payment required
@app.get("/")
async def root():
    return {
        "message": "Welcome to Premium Data API",
        "wallet": provider.config.wallet_address,
        "pricing": PRICING_TIERS,
        "docs": "/docs",
    }


# Weather endpoint with tiered access
@app.get("/api/weather/{location}")
async def get_weather(location: str, request: Request):
    # Get payment info from middleware
    payment_data: Optional[PaymentData] = getattr(request.state, "payment_data", None)
    
    if not payment_data:
        # Should not happen with middleware
        raise HTTPException(402, "Payment required")
    
    # Determine tier based on payment amount
    amount = float(payment_data.value) / 1e6  # Convert from USDC units
    tier = get_tier_from_payment(amount, "weather")
    
    # Track API usage
    if analytics:
        await analytics.track_event(
            AnalyticsEvent.API_CALL,
            wallet_address=payment_data.from_address,
            provider_address=provider.config.wallet_address,
            metadata={
                "endpoint": "/api/weather",
                "tier": tier,
                "location": location,
            }
        )
    
    # Return data based on tier
    base_data = {
        "location": location,
        "temperature": 72,
        "conditions": "Partly cloudy",
        "tier": tier,
    }
    
    if tier == "premium" or tier == "enterprise":
        base_data.update({
            "humidity": 65,
            "wind_speed": 12,
            "precipitation": 0.1,
            "forecast": [
                {"day": "Tomorrow", "high": 75, "low": 60},
                {"day": "Day 2", "high": 78, "low": 62},
                {"day": "Day 3", "high": 80, "low": 65},
            ]
        })
    
    if tier == "enterprise":
        base_data.update({
            "historical": {
                "avg_temp_30d": 70,
                "precipitation_30d": 2.5,
            },
            "ml_prediction": {
                "7_day_trend": "warming",
                "precipitation_probability": 0.15,
                "confidence": 0.85,
            }
        })
    
    return base_data


# Market data endpoint
@app.get("/api/market-data/{symbol}")
async def get_market_data(symbol: str, request: Request):
    payment_data: Optional[PaymentData] = getattr(request.state, "payment_data", None)
    
    if not payment_data:
        raise HTTPException(402, "Payment required")
    
    amount = float(payment_data.value) / 1e6
    tier = get_tier_from_payment(amount, "market")
    
    # Submit to facilitator for verification (premium feature)
    if tier in ["realtime", "analytics"]:
        try:
            payment_id = await facilitator.submit_payment(
                payment_data.model_dump(),
                provider.config.wallet_address,
                {"endpoint": "/api/market-data", "symbol": symbol}
            )
            
            # Wait for verification
            result = await facilitator.wait_for_payment(payment_id, timeout=10)
            if result["status"] != "completed":
                raise HTTPException(402, "Payment verification failed")
                
        except Exception as e:
            print(f"Facilitator error: {e}")
            # Continue anyway for demo
    
    base_data = {
        "symbol": symbol,
        "price": 150.25,
        "volume": 1_234_567,
        "tier": tier,
        "timestamp": "2024-01-15T10:30:00Z",
    }
    
    if tier == "realtime" or tier == "analytics":
        base_data.update({
            "bid": 150.20,
            "ask": 150.30,
            "high_24h": 152.50,
            "low_24h": 148.00,
            "change_24h": 1.25,
            "change_percent_24h": 0.84,
        })
    
    if tier == "analytics":
        base_data.update({
            "technical_indicators": {
                "rsi": 65,
                "macd": {"value": 0.5, "signal": 0.3, "histogram": 0.2},
                "moving_averages": {
                    "sma_20": 148.50,
                    "sma_50": 145.00,
                    "ema_12": 149.80,
                },
            },
            "sentiment": {
                "score": 0.72,
                "mentions": 1523,
                "positive_ratio": 0.68,
            }
        })
    
    return base_data


# ML predictions endpoint
@app.get("/api/predictions/{model}")
async def get_predictions(model: str, request: Request, params: Dict[str, Any] = {}):
    payment_data: Optional[PaymentData] = getattr(request.state, "payment_data", None)
    
    if not payment_data:
        raise HTTPException(402, "Payment required")
    
    amount = float(payment_data.value) / 1e6
    tier = get_tier_from_payment(amount, "predictions")
    
    base_data = {
        "model": model,
        "tier": tier,
        "timestamp": "2024-01-15T10:30:00Z",
    }
    
    if tier == "simple":
        base_data["prediction"] = {
            "value": 0.75,
            "confidence": 0.60,
            "model_version": "v1.0",
        }
    elif tier == "advanced":
        base_data["prediction"] = {
            "ensemble_result": 0.78,
            "models": [
                {"name": "rf", "value": 0.76, "weight": 0.3},
                {"name": "xgb", "value": 0.79, "weight": 0.4},
                {"name": "nn", "value": 0.78, "weight": 0.3},
            ],
            "confidence": 0.82,
            "confidence_interval": [0.72, 0.84],
            "model_version": "v2.5",
        }
    elif tier == "custom":
        base_data["prediction"] = {
            "custom_model_result": 0.81,
            "feature_importance": {
                "feature_1": 0.25,
                "feature_2": 0.18,
                "feature_3": 0.15,
            },
            "shap_values": [0.12, -0.08, 0.15],
            "confidence": 0.88,
            "confidence_interval": [0.76, 0.86],
            "model_version": "custom-v1",
            "training_metrics": {
                "accuracy": 0.92,
                "f1_score": 0.89,
                "auc_roc": 0.94,
            }
        }
    
    return base_data


# Analytics endpoint (for providers)
@app.get("/api/analytics")
async def get_analytics_data():
    """Get provider analytics"""
    
    local_analytics = provider.get_analytics()
    
    # Get shared analytics
    shared_analytics = None
    if analytics:
        shared_analytics = analytics.get_provider_metrics(provider.config.wallet_address)
    
    # Get facilitator stats
    facilitator_stats = None
    try:
        facilitator_stats = await facilitator.get_provider_stats(provider.config.wallet_address)
    except:
        pass
    
    return {
        "provider_wallet": provider.config.wallet_address,
        "local_analytics": local_analytics,
        "shared_analytics": shared_analytics,
        "facilitator_stats": facilitator_stats,
        "pricing_tiers": PRICING_TIERS,
    }


# Premium feature: Create payment links
@app.post("/api/payment-links")
async def create_payment_link(
    amount: float,
    description: str,
    expires_in: int = 3600
):
    """Create a payment link (premium feature)"""
    
    try:
        result = await facilitator.create_payment_link(
            amount=str(amount),
            provider_address=provider.config.wallet_address,
            description=description,
            expires_in=expires_in
        )
        
        return {
            "success": True,
            "payment_link": result["url"],
            "expires_at": result["expires_at"],
        }
    except Exception as e:
        raise HTTPException(400, f"Failed to create payment link: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)