"""x402-enabled FastAPI application"""

from fastapi import FastAPI, HTTPException
from fast_x402 import X402Provider, X402Config, X402Middleware

# Initialize app
app = FastAPI(title="My x402 API", version="1.0.0")

# Initialize x402 (auto-loads from .x402.config.json)
config = X402Config()
provider = X402Provider(config)

# Add x402 middleware
app.add_middleware(
    X402Middleware,
    provider=provider,
    paths={
        "/api/weather/*": lambda req: provider.create_payment_requirement("0.01"),
        "/api/analyze/*": lambda req: provider.create_payment_requirement("0.05"),
        "/api/premium/*": lambda req: provider.create_payment_requirement("0.10"),
    }
)

# Enable dashboard
provider.enable_dashboard(app, port=3001)

# Free endpoint
@app.get("/")
async def root():
    return {
        "message": "Welcome to my x402 API",
        "pricing": {
            "/api/weather": "$0.01",
            "/api/analyze": "$0.05",
            "/api/premium": "$0.10"
        },
        "wallet": provider.config.wallet_address,
        "dashboard": "http://localhost:3001",
    }

# Paid endpoints
@app.get("/api/weather/{city}")
async def get_weather(city: str):
    return {
        "city": city,
        "temperature": 72,
        "conditions": "Sunny",
        "forecast": "Clear skies ahead!"
    }

@app.post("/api/analyze")
async def analyze_data(data: dict):
    return {
        "analysis": "Deep insights here",
        "confidence": 0.95,
        "recommendations": ["Buy", "Hold", "Profit"]
    }

@app.get("/api/premium/report")
async def premium_report():
    return {
        "report": "Comprehensive analysis with ML predictions",
        "value": "High",
        "next_steps": ["Scale", "Optimize", "Dominate"]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
