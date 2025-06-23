# x402-langchain 🤖💰

Enable your LangChain AI agents to make autonomous micropayments using the x402 protocol. Give your agents economic agency!

## Features

- 🔧 **Drop-in LangChain Tool** - Works with any LangChain agent
- 💸 **Autonomous Payments** - Agents can pay for APIs, data, and services  
- 🛡️ **Built-in Safeguards** - Spending limits, domain restrictions, approval flows
- 📊 **Payment Analytics** - Track agent spending and ROI
- ⚡ **Instant Settlement** - 2-second finality on Base L2
- 🔐 **Secure by Design** - EIP-712 signatures, no private key exposure

## Installation

```bash
pip install x402-langchain
```

## Quick Start

```python
from langchain_openai import ChatOpenAI
from x402_langchain import create_x402_agent

# Create an AI agent that can make payments
agent = create_x402_agent(
    private_key="0xYourPrivateKey",
    llm=ChatOpenAI(model="gpt-4"),
    spending_limit_daily=10.0,  # $10/day limit
    auto_approve=True,
)

# Agent can now pay for premium APIs!
result = agent.run(
    "Get the current weather in NYC from "
    "https://api.weather.example.com/premium/current?city=NYC"
)
```

That's it! Your agent can now access paid APIs autonomously. 🎉

## How It Works

1. **Agent needs data** → Tries to access a paid API
2. **Receives 402 Payment Required** → API requests payment
3. **Agent evaluates cost** → Checks against spending limits
4. **Signs payment** → Uses EIP-712 standard
5. **Accesses resource** → Gets the data it needs
6. **Continues task** → Uses data to complete objective

## Core Concepts

### X402PaymentTool

The main LangChain tool for making payments:

```python
from x402_langchain import create_x402_tool

payment_tool = create_x402_tool(
    private_key="0xYourPrivateKey",
    spending_limit_daily=50.0,
    spending_limit_per_request=5.0,
    auto_approve=True,
    allowed_domains=["api.trusted.com", "data.provider.com"]
)

# Add to your agent's toolkit
tools = [payment_tool, search_tool, calculator_tool]
```

### Spending Controls

Protect your agents from overspending:

```python
from x402_langchain import X402Config, SpendingLimits

config = X402Config(
    private_key="0xYourPrivateKey",
    spending_limits=SpendingLimits(
        per_request=1.0,   # Max $1 per API call
        per_hour=10.0,     # Max $10 per hour  
        per_day=50.0,      # Max $50 per day
    ),
    allowed_domains=["*.trusted.com"],  # Only pay trusted domains
    blocked_domains=["*.sketchy.com"],  # Never pay these
)
```

### Custom Approval Logic

Implement custom payment approval:

```python
def approve_payment(url: str, amount: float) -> bool:
    """Custom logic to approve/deny payments"""
    
    # Auto-approve small amounts
    if amount < 0.10:
        return True
    
    # Require confirmation for large amounts
    if amount > 5.00:
        return input(f"Approve ${amount} payment to {url}? (y/n): ") == "y"
    
    # Check if URL is for critical data
    if "critical-data" in url:
        return True
        
    return True

agent = create_x402_agent(
    private_key="0xYourPrivateKey",
    llm=llm,
    auto_approve=False,
    approval_callback=approve_payment,
)
```

## Advanced Examples

### Data Marketplace Agent

Create agents that purchase data from multiple sources:

```python
from x402_langchain import X402Agent, X402Config

class DataAnalystAgent(X402Agent):
    async def analyze_market(self, symbol: str):
        # Purchase data from multiple sources
        sources = [
            f"https://financial.data.com/api/quote/{symbol}",
            f"https://sentiment.news.com/api/analysis/{symbol}",
            f"https://technical.indicators.com/api/signals/{symbol}",
        ]
        
        data = []
        for source in sources:
            result = await self.client.fetch_with_payment(
                url=source,
                max_amount=0.50  # Max $0.50 per source
            )
            if result.success:
                data.append(result.data)
        
        # Analyze combined data
        return self.synthesize_analysis(data)
```

### Autonomous Research Agent

Build agents that conduct research by purchasing access to papers and data:

```python
agent = create_x402_agent(
    private_key=private_key,
    llm=ChatOpenAI(model="gpt-4"),
    spending_limit_daily=25.0,
)

research_prompt = """
Research the latest developments in quantum computing.
You have a budget to purchase academic papers and datasets.

Available paid resources:
- https://arxiv.premium.com/api/papers/quantum-computing ($0.25/paper)
- https://patents.data.com/api/search/quantum ($0.50/search)
- https://research.gate.com/api/datasets/quantum ($1.00/dataset)

Provide a comprehensive summary with citations.
"""

result = agent.run(research_prompt)
```

### Multi-Agent Collaboration

Create teams of agents that coordinate payments:

```python
# Research agent finds data sources
research_agent = create_x402_agent(
    private_key=research_key,
    spending_limit_daily=20.0,
)

# Analysis agent processes purchased data  
analyst_agent = create_x402_agent(
    private_key=analyst_key,
    spending_limit_daily=30.0,
)

# Coordinator agent manages the team
coordinator = MultiAgentCoordinator(
    agents=[research_agent, analyst_agent],
    total_budget=50.0,
)

result = coordinator.execute_task(
    "Analyze global supply chain disruptions"
)
```

## Monitoring & Analytics

Track your agent's spending:

```python
# Get spending report
report = agent.get_spending_report()
print(f"Spent today: ${report['spent_today']}")
print(f"Remaining budget: ${report['remaining']['day']}")

# Set up webhooks for payment notifications
config = X402Config(
    private_key=private_key,
    webhook_url="https://your-server.com/webhooks/x402",
    log_payments=True,
)

# Export payment history
history = agent.export_payment_history()
for payment in history:
    print(f"{payment.timestamp}: ${payment.amount} to {payment.url}")
```

## Security Best Practices

1. **Private Key Management**
   ```python
   # Use environment variables
   import os
   private_key = os.getenv("AGENT_PRIVATE_KEY")
   
   # Or use key management service
   from your_kms import get_key
   private_key = get_key("agent-wallet")
   ```

2. **Domain Restrictions**
   ```python
   config = X402Config(
       private_key=private_key,
       allowed_domains=[
           "api.trusted-provider.com",
           "*.verified-data.net",
       ],
       blocked_domains=[
           "*.suspicious.com",
       ]
   )
   ```

3. **Spending Limits**
   ```python
   # Conservative limits for production
   spending_limits = SpendingLimits(
       per_request=0.10,    # 10 cents max per request
       per_hour=1.00,       # $1 per hour
       per_day=10.00,       # $10 per day
   )
   ```

4. **Audit Trails**
   ```python
   # Enable comprehensive logging
   config.log_payments = True
   config.webhook_url = "https://your-audit-system.com/x402"
   ```

## Common Use Cases

### API Data Aggregation
Agents that collect data from multiple paid APIs to answer complex questions.

### Autonomous Trading
Trading bots that pay for real-time market data and execute strategies.

### Research Automation  
Academic agents that purchase papers, datasets, and compute resources.

### Content Creation
Creative agents that pay for stock images, music, and other assets.

### Customer Service
Support agents that access premium knowledge bases and expert systems.

## API Reference

### X402Config
Main configuration class for payment behavior.

### X402Client  
Low-level client for making payments.

### X402PaymentTool
LangChain tool for agent integration.

### X402Agent
High-level wrapper for payment-enabled agents.

## FAQ

**Q: How do agents get funds?**
A: You fund the agent's wallet address with USDC on Base. The agent spends from this balance.

**Q: What happens if an agent runs out of funds?**
A: Payment attempts will fail with `InsufficientFundsError`. The agent continues but cannot access paid resources.

**Q: Can agents share wallets?**
A: Not recommended. Each agent should have its own wallet for security and accounting.

**Q: How are payments tracked?**
A: All payments are logged with timestamps, amounts, and destinations. Use webhooks for real-time tracking.

## Troubleshooting

### "Payment denied" errors
- Check spending limits
- Verify domain is allowed
- Ensure approval callback returns True

### "Invalid signature" errors  
- Verify private key is correct
- Check chain ID matches (8453 for Base)
- Ensure token address is correct

### "Insufficient funds" errors
- Check wallet balance on Base
- Verify USDC approval for transfers
- Top up agent wallet with more USDC

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Support

- 📚 [Documentation](https://docs.x402.org/langchain)
- 💬 [Discord Community](https://discord.gg/x402-agents)
- 🐛 [Issue Tracker](https://github.com/x402/x402-langchain/issues)
- 🐦 [Twitter Updates](https://twitter.com/x402protocol)

---

Built with ❤️ by the x402 team. Empowering AI agents with economic autonomy!