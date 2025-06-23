# 🚀 x402 SDKs Now Live on PyPI!

We're excited to announce that both x402 SDK packages are now available on PyPI!

## 📦 Installation

```bash
# For API providers
pip install fast-x402

# For AI developers
pip install x402-langchain

# Or install both
pip install fast-x402 x402-langchain
```

## 🎯 What's Included in v1.1.0

### fast-x402 - Provider SDK
- ✅ Zero-config setup with `x402 create` CLI
- ✅ Automatic wallet generation
- ✅ Smart network detection
- ✅ Local development mode (no blockchain needed!)
- ✅ Real-time payment dashboard
- ✅ Token presets (USDC, USDT, DAI)
- ✅ Developer-friendly error messages
- ✅ Built-in testing tools

### x402-langchain - Agent SDK
- ✅ Automatic wallet creation for agents
- ✅ API mocking for development
- ✅ Cost discovery before payment
- ✅ Smart approval rules
- ✅ Shared API intelligence
- ✅ Payment batching
- ✅ Dry run mode
- ✅ Auto-funding in development

## 🚀 Quick Start

### Provider Setup (30 seconds!)
```bash
# Create a new x402-enabled API
x402 create my-api
cd my-api
python app.py

# Done! Your API is accepting payments
```

### Agent Setup
```python
from x402_langchain import create_smart_agent

# Create an agent with payment capabilities
agent = create_smart_agent()

# Agent can now pay for APIs autonomously!
```

## 📊 Live on PyPI

- **fast-x402**: https://pypi.org/project/fast-x402/
- **x402-langchain**: https://pypi.org/project/x402-langchain/

## 🔗 Resources

- GitHub: https://github.com/x402/x402-sdk
- Documentation: https://docs.x402.org
- Examples: See `/examples` in each package

## 💬 Community

Join our community to share your x402-powered projects!

---

Built with ❤️ by the x402 team. Making micropayments dead simple for developers.