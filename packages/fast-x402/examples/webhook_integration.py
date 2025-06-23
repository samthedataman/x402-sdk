"""Example of x402 with webhook notifications"""

from fastapi import FastAPI, BackgroundTasks
from fast_x402 import X402Provider, X402Config, x402_middleware
import httpx
from datetime import datetime
import json

app = FastAPI(title="x402 Webhook Integration Example")

# Webhook configuration
WEBHOOK_URL = "https://your-webhook-endpoint.com/payments"
SLACK_WEBHOOK = "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"


async def send_webhook(payment_data: dict, endpoint: str):
    """Send payment notification to webhook"""
    payload = {
        "event": "payment_received",
        "timestamp": datetime.utcnow().isoformat(),
        "payment": payment_data,
        "endpoint": endpoint,
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                WEBHOOK_URL,
                json=payload,
                timeout=5.0
            )
            if response.status_code != 200:
                print(f"Webhook failed: {response.status_code}")
    except Exception as e:
        print(f"Webhook error: {e}")


async def notify_slack(payment_data: dict, endpoint: str):
    """Send Slack notification for payments"""
    amount = float(payment_data.get("value", 0)) / 1_000_000  # Convert from wei
    
    message = {
        "text": f"💰 New Payment Received!",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*New x402 Payment*\n"
                           f"Amount: ${amount:.2f} USDC\n"
                           f"From: `{payment_data.get('from', 'Unknown')[:10]}...`\n"
                           f"Endpoint: `{endpoint}`"
                }
            }
        ]
    }
    
    try:
        async with httpx.AsyncClient() as client:
            await client.post(SLACK_WEBHOOK, json=message)
    except Exception as e:
        print(f"Slack notification error: {e}")


async def on_payment_received(payment_data: dict, background_tasks: BackgroundTasks):
    """Handle payment received events"""
    endpoint = payment_data.get("endpoint", "unknown")
    
    # Log payment
    print(f"Payment received: {json.dumps(payment_data, indent=2)}")
    
    # Send webhooks in background
    background_tasks.add_task(send_webhook, payment_data, endpoint)
    background_tasks.add_task(notify_slack, payment_data, endpoint)
    
    # Update metrics, analytics, etc.
    # ...


# Configure x402 with webhook support
provider = X402Provider(
    X402Config(
        wallet_address="0x742d35Cc6634C0532925a3b844Bc9e7595f6E123",
        analytics_enabled=True,
        analytics_webhook=WEBHOOK_URL,
    )
)

# Add middleware with payment callback
app.add_middleware(
    x402_middleware,
    wallet_address=provider.config.wallet_address,
    routes={
        "/api/data": "0.05",
        "/api/compute": {"amount": "0.10", "scheme": "exact"},
        "/api/inference/*": "0.001",
    },
    on_payment=on_payment_received
)


@app.get("/api/data")
async def get_data(background_tasks: BackgroundTasks):
    """Endpoint that requires payment and sends notifications"""
    return {
        "data": "Premium data that triggered webhook",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/api/compute")
async def compute_task(task: dict, background_tasks: BackgroundTasks):
    """Compute endpoint with webhook notifications"""
    import asyncio
    
    # Simulate computation
    await asyncio.sleep(1)
    
    result = {
        "task_id": task.get("id", "unknown"),
        "result": "Computed successfully",
        "compute_time": 1.0
    }
    
    return result


@app.get("/webhooks/test")
async def test_webhooks(background_tasks: BackgroundTasks):
    """Test webhook configuration"""
    test_payment = {
        "from": "0x1234567890abcdef1234567890abcdef12345678",
        "value": "50000",  # $0.05
        "token": "USDC",
        "endpoint": "/test"
    }
    
    background_tasks.add_task(send_webhook, test_payment, "/test")
    background_tasks.add_task(notify_slack, test_payment, "/test")
    
    return {"message": "Test webhooks sent"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)