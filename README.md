# x402 Payment Protocol SDK Monorepo 🚀

[![PyPI - fast-x402](https://img.shields.io/pypi/v/fast-x402.svg)](https://pypi.org/project/fast-x402/)
[![PyPI - x402-langchain](https://img.shields.io/pypi/v/x402-langchain.svg)](https://pypi.org/project/x402-langchain/)
[![Python](https://img.shields.io/pypi/pyversions/fast-x402.svg)](https://pypi.org/project/fast-x402/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

This monorepo contains Python SDKs for the x402 payment protocol - enabling instant micropayments for both API providers and AI agents.

## 📦 Packages

### [fast-x402](packages/fast-x402/) ⚡️
Lightning-fast x402 payment integration for FastAPI and modern Python web frameworks. Accept micropayments with just 3 lines of code!

```python
from fastapi import FastAPI
from fast_x402 import x402_middleware

app = FastAPI()
app.add_middleware(x402_middleware, 
    wallet_address="0xYourAddress",
    routes={"/api/premium": "0.10"}
)
```

### [x402-langchain](packages/x402-langchain/) 🤖
Enable your LangChain AI agents to make autonomous micropayments. Give your agents economic agency!

```python
from x402_langchain import create_x402_agent

agent = create_x402_agent(
    private_key="0xYourPrivateKey",
    llm=ChatOpenAI(model="gpt-4"),
    spending_limit_daily=10.0,
)
```

## 🎯 Key Features

- **Zero Protocol Fees** - Only pay ~$0.001 in blockchain gas
- **Instant Settlement** - 2-second finality on Base L2
- **Simple Integration** - Add payments in minutes, not weeks
- **Built for AI** - Native support for autonomous agent payments
- **Secure by Design** - EIP-712 signatures, spending limits, domain restrictions

## 🚀 Quick Start

### Install Individual Packages

```bash
# For API providers
pip install fast-x402

# For AI developers  
pip install x402-langchain
```

### Development Setup

```bash
# Clone the repository
git clone https://github.com/x402/x402-sdk.git
cd x402-sdk

# Install dependencies
pip install poetry
poetry install

# Run tests
poetry run pytest

# Run examples
cd packages/fast-x402/examples
python basic_api.py
```

## 📖 Documentation

- [fast-x402 Documentation](packages/fast-x402/README.md) - For API providers
- [x402-langchain Documentation](packages/x402-langchain/README.md) - For AI developers
- [Protocol Specification](https://docs.x402.org) - Technical details

## 💡 Use Cases

### For API Providers (fast-x402)
- Monetize APIs with micropayments
- Replace complex subscriptions with pay-per-use
- Accept payments from AI agents automatically
- Zero payment processing fees

### For AI Developers (x402-langchain)
- Build agents that can purchase data autonomously
- Access premium APIs without manual API keys
- Implement spending controls and limits
- Track agent expenditures and ROI

## 🏗️ Architecture

The x402 protocol enables instant payments through HTTP headers:

1. **Client requests resource** → `GET /api/data`
2. **Server returns 402** → Payment details in response
3. **Client signs payment** → EIP-712 standard
4. **Client retries with payment** → `X-Payment` header
5. **Server delivers resource** → Instant settlement

## 🛡️ Security

- **EIP-712 Signatures** - Cryptographically secure payments
- **Replay Protection** - Each payment has unique nonce
- **Spending Limits** - Control agent expenditures
- **Domain Restrictions** - Whitelist/blacklist payment destinations

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Workflow

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📊 Status

| Package | Version | Tests | Coverage |
|---------|---------|--------|----------|
| fast-x402 | 1.0.0 | ✅ | 95% |
| x402-langchain | 1.0.0 | ✅ | 92% |

## 🚦 Roadmap

- [ ] JavaScript/TypeScript SDKs
- [ ] Rust implementation
- [ ] Multi-chain support (Polygon, Arbitrum)
- [ ] Advanced payment schemes ("upto", "subscription")
- [ ] Payment analytics dashboard
- [ ] Agent marketplace integration

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

Built on top of the x402 protocol by Coinbase. Special thanks to:
- The Coinbase team for creating the x402 standard
- The Anthropic team for the Model Context Protocol
- The LangChain community for the agent framework

## 📞 Support

- 💬 [Discord Community](https://discord.gg/x402)
- 📧 [Email Support](mailto:support@x402.org)
- 🐛 [Issue Tracker](https://github.com/x402/x402-sdk/issues)
- 🐦 [Twitter Updates](https://twitter.com/x402protocol)

---

<p align="center">
  Built with ❤️ by the x402 community
</p>

<p align="center">
  <a href="https://x402.org">Website</a> •
  <a href="https://docs.x402.org">Documentation</a> •
  <a href="https://github.com/x402/x402-sdk">GitHub</a>
</p>