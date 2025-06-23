"""Basic FastAPI example with x402 payments"""

from fastapi import FastAPI, Depends
from fast_x402 import (
    x402_middleware,
    X402Provider,
    X402Config,
    X402Dependency,
    get_x402_payment,
)

# Create FastAPI app
app = FastAPI(title="x402 Payment Example API")

# Add x402 middleware
app.add_middleware(
    x402_middleware,
    wallet_address="0x742d35Cc6634C0532925a3b844Bc9e7595f6E123",
    routes={
        "/api/premium/*": "0.10",  # $0.10 for all premium endpoints
        "/api/data": {"amount": "0.05", "scheme": "exact"},
        "/api/inference": "0.001",  # $0.001 per inference
    },
)

# Or create provider directly for more control
provider = X402Provider(
    X402Config(
        wallet_address="0x742d35Cc6634C0532925a3b844Bc9e7595f6E123",
        analytics_enabled=True,
    )
)


@app.get("/")
async def root():
    """Free endpoint - no payment required"""
    return {"message": "Welcome to x402 Payment API"}


@app.get("/api/free")
async def free_endpoint():
    """Another free endpoint"""
    return {"data": "This is free!"}


@app.get("/api/premium/weather")
async def premium_weather(payment = Depends(get_x402_payment)):
    """Premium endpoint - requires $0.10 payment (handled by middleware)"""
    return {
        "temperature": 72,
        "conditions": "sunny",
        "forecast": "Clear skies ahead",
        "paid_by": payment.from_address if payment else "middleware",
    }


@app.get("/api/data")
async def get_data():
    """Data endpoint - requires $0.05 payment"""
    return {
        "data": [1, 2, 3, 4, 5],
        "metadata": {"source": "premium", "quality": "high"},
    }


# Using dependency injection for payment
PayForInference = X402Dependency("0.001")

@app.post("/api/inference")
async def run_inference(
    prompt: str,
    payment: dict = Depends(PayForInference),
):
    """AI inference endpoint - requires $0.001 payment"""
    return {
        "prompt": prompt,
        "result": f"Generated response for: {prompt}",
        "tokens": 150,
    }


@app.get("/api/custom-payment")
async def custom_payment_endpoint(payment = Depends(X402Dependency("0.25"))):
    """Custom payment amount using dependency"""
    return {
        "message": "Thank you for your payment!",
        "amount_paid": "0.25",
        "payer": payment.from_address,
    }


@app.get("/analytics")
async def get_analytics():
    """Get payment analytics (free endpoint)"""
    analytics = provider.get_analytics()
    return analytics.to_dashboard_dict()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)