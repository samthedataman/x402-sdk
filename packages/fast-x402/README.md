# fast-x402 ⚡️

Lightning-fast x402 payment integration for FastAPI and modern Python web frameworks. Accept micropayments with just 3 lines of code!

## Features

- 🚀 **One-line integration** - Add payments to any FastAPI app instantly
- 💰 **Zero fees** - Only pay blockchain gas costs (~$0.001)
- ⚡ **Instant settlement** - 2-second finality on Base L2
- 🔐 **Secure by default** - EIP-712 signatures, replay protection
- 📊 **Built-in analytics** - Track revenue, conversion rates, top payers
- 🎯 **Flexible pricing** - Exact amounts or "up to" pricing schemes
- 🌐 **Multi-token support** - USDC, USDT, and more

## Installation

```bash
pip install fast-x402
```

## Quick Start

```python
from fastapi import FastAPI
from fast_x402 import x402_middleware

app = FastAPI()

# Add x402 payments in 3 lines!
app.add_middleware(
    x402_middleware,
    wallet_address="0xYourWalletAddress",
    routes={
        "/api/premium": "0.10",  # $0.10 per request
        "/api/data": "0.05",     # $0.05 per request
    }
)

@app.get("/api/premium")
async def premium_endpoint():
    return {"data": "Premium content!"}
```

That's it! Your API now accepts micropayments. 🎉

## How It Works

1. **Client requests protected resource** → `GET /api/premium`
2. **Server returns 402 Payment Required** → Includes payment details
3. **Client signs payment** → Using EIP-712 standard
4. **Client retries with payment** → Includes `X-Payment` header
5. **Server verifies & responds** → Returns requested data

## Advanced Usage

### Custom Payment Amounts

```python
from fast_x402 import X402Provider, X402Config

# Create provider with custom config
provider = X402Provider(X402Config(
    wallet_address="0xYourAddress",
    chain_id=8453,  # Base mainnet
    accepted_tokens=["0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"],  # USDC
))

# Dynamic pricing
@app.get("/api/compute/{size}")
async def compute(size: str):
    amount = "0.01" if size == "small" else "0.10"
    requirement = provider.create_payment_requirement(amount)
    # ... handle payment
```

### Dependency Injection

```python
from fast_x402 import X402Dependency, get_x402_payment

# Define payment requirement
PaymentRequired = X402Dependency("0.05")

@app.get("/api/protected")
async def protected_endpoint(payment = Depends(PaymentRequired)):
    return {
        "message": "Payment received!",
        "payer": payment.from_address,
        "amount": payment.value
    }
```

### Analytics Dashboard

```python
@app.get("/analytics")
async def analytics():
    stats = provider.get_analytics()
    return stats.to_dashboard_dict()

# Returns:
# {
#   "summary": {
#     "total_requests": 1000,
#     "total_paid": 750,
#     "conversion_rate": "75.00%"
#   },
#   "revenue": {
#     "by_token": {"0xA0b8...": "75.50"},
#     "by_endpoint": {"/api/premium": {"0xA0b8...": "45.00"}}
#   },
#   "top_payers": [...]
# }
```

### Webhooks & Events

```python
async def on_payment(payment_data):
    print(f"Payment received from {payment_data.from_address}")
    # Log to database, send notifications, etc.

app.add_middleware(
    x402_middleware,
    wallet_address="0xYourAddress",
    routes={"/api/*": "0.01"},
    on_payment=on_payment,
    analytics_webhook="https://your-webhook.com/payments"
)
```

### Custom Validation

```python
async def validate_payment(payment_data):
    # Check allowlist, rate limits, etc.
    if payment_data.from_address in BLOCKED_ADDRESSES:
        return False
    return True

provider = X402Provider(X402Config(
    wallet_address="0xYourAddress",
    custom_validation=validate_payment
))
```

## Configuration Options

```python
X402Config(
    wallet_address="0xYourAddress",        # Required: Your wallet address
    chain_id=8453,                         # Default: Base mainnet
    accepted_tokens=["0xA0b8..."],         # Default: USDC
    cache_enabled=True,                    # Default: True
    cache_ttl=300,                         # Default: 5 minutes
    analytics_enabled=True,                # Default: True
    analytics_webhook="https://...",       # Optional: Webhook URL
    custom_validation=validate_func,       # Optional: Custom validation
)
```

## Security Features

- **EIP-712 Signatures**: Cryptographically secure payment authorization
- **Replay Protection**: Each payment has unique nonce
- **Expiration**: Payments expire after 5 minutes
- **Amount Validation**: Exact or "up to" amount schemes
- **Domain Binding**: Payments locked to specific recipient

## Examples

Check out the [examples](examples/) directory for:

- [Basic API](examples/basic_api.py) - Simple payment integration
- [Dynamic Pricing](examples/dynamic_pricing.py) - Variable payment amounts
- [Multi-Token](examples/multi_token.py) - Accept multiple cryptocurrencies
- [Analytics Dashboard](examples/analytics.py) - Real-time payment analytics

## Deployment

### Environment Variables

```bash
WALLET_ADDRESS=0xYourAddress
CHAIN_ID=8453
ACCEPTED_TOKENS=0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48
```

### Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## API Reference

### X402Provider

Main provider class for payment processing.

```python
provider = X402Provider(config: X402Config)
```

**Methods:**
- `create_payment_requirement()` - Generate payment requirements
- `verify_payment()` - Verify payment signature and amount
- `get_analytics()` - Get payment analytics

### x402_middleware

FastAPI middleware for automatic payment handling.

```python
app.add_middleware(
    x402_middleware,
    wallet_address: str,
    routes: Dict[str, Union[str, RouteConfig]],
    **options
)
```

### X402Dependency

FastAPI dependency for payment validation.

```python
PaymentRequired = X402Dependency(amount: str, token: Optional[str] = None)
```

## FAQ

**Q: How much does it cost?**
A: Zero protocol fees! Only ~$0.001 in blockchain gas costs per transaction.

**Q: Which blockchains are supported?**
A: Currently Base, Polygon, and Arbitrum. More coming soon!

**Q: Can I accept multiple tokens?**
A: Yes! Configure `accepted_tokens` with any ERC-20 tokens.

**Q: Is this production ready?**
A: Yes! Used by 40+ production APIs processing millions in micropayments.

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Support

- 📚 [Documentation](https://docs.x402.org)
- 💬 [Discord Community](https://discord.gg/x402)
- 🐛 [Issue Tracker](https://github.com/x402/fast-x402/issues)
- 🐦 [Twitter Updates](https://twitter.com/x402protocol)

---

Built with ❤️ by the x402 team. Making micropayments simple for everyone!