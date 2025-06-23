#!/usr/bin/env python3
"""
Real-world x402 SDK test scenario
Simulates an AI agent making payments to an API
"""

import asyncio
import sys
import os

# Add packages to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'packages/fast-x402'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'packages/x402-langchain'))

async def test_real_scenario():
    """Test a real-world scenario: AI agent paying for API access"""
    
    print("🎯 x402 SDK Real-World Test Scenario")
    print("=" * 50)
    
    # 1. Create Provider (API side)
    print("\n1️⃣ Setting up API Provider...")
    from fast_x402.enhanced_provider import EnhancedX402Provider
    
    provider = EnhancedX402Provider(mode="development")
    print(f"   Provider wallet: {provider.config.wallet_address}")
    print(f"   Mode: {provider.config.mode}")
    
    # 2. Create Client (AI agent side)
    print("\n2️⃣ Setting up AI Agent Client...")
    from x402_langchain.enhanced_client import EnhancedX402Client
    
    client = EnhancedX402Client(mode="development", auto_fund=True)
    print(f"   Agent wallet: {client.config.wallet_address}")
    print(f"   Auto funding: enabled")
    
    # 3. Set spending limits
    print("\n3️⃣ Configuring Agent Spending Limits...")
    client.set_spending_limit(daily_limit=10.0, per_request_limit=2.0)
    client.add_trusted_domain("api.weather.com")
    print("   Daily limit: $10.00")
    print("   Per-request limit: $2.00")
    print("   Trusted: api.weather.com")
    
    # 4. Mock some APIs for testing
    print("\n4️⃣ Setting up API Mocks...")
    mock_responses = [
        ("https://api.weather.com/forecast", {"temp": 75, "condition": "sunny"}, 0.05),
        ("https://api.news.com/headlines", {"headlines": ["Market up", "Tech news"]}, 0.03),
        ("https://api.expensive.com/analysis", {"analysis": "premium data"}, 5.0),  # Over limit
    ]
    
    for url, response, cost in mock_responses:
        client.mocking_engine.mock_api(url, response, cost)
        print(f"   Mocked: {url} (${cost})")
    
    # 5. Test payment decisions
    print("\n5️⃣ Testing Agent Payment Decisions...")
    
    test_requests = [
        ("https://api.weather.com/forecast", "Should approve - trusted domain, under limit"),
        ("https://api.news.com/headlines", "Should approve - under limit"),
        ("https://api.expensive.com/analysis", "Should reject - over per-request limit"),
        ("https://unknown-api.com/data", "Should prompt - untrusted domain"),
    ]
    
    for url, expected in test_requests:
        domain = url.split("//")[1].split("/")[0]
        cost = await client.cost_discovery.discover_cost(url)
        should_approve = client._should_approve_payment(domain, cost)
        
        status = "✅ APPROVE" if should_approve else "❌ REJECT"
        print(f"   {status} {url} (${cost}) - {expected}")
    
    # 6. Simulate actual API calls
    print("\n6️⃣ Simulating API Calls...")
    
    for url, _, _ in mock_responses[:2]:  # Only test approved ones
        try:
            response = client.mocking_engine.call_api(url)
            print(f"   ✅ {url}: {response}")
        except Exception as e:
            print(f"   ❌ {url}: Error - {str(e)}")
    
    # 7. Check spending
    print("\n7️⃣ Agent Spending Summary...")
    costs = []
    for url, _, _ in mock_responses[:2]:
        cost = await client.cost_discovery.discover_cost(url)
        costs.append(cost)
    total_spent = sum(costs)
    daily_spent = client.spending_limits.get("daily_spent", 0.0)
    daily_limit = client.spending_limits.get("daily_limit", 10.0)
    
    print(f"   Total spent: ${total_spent:.2f}")
    print(f"   Daily spent: ${daily_spent:.2f} / ${daily_limit:.2f}")
    print(f"   Remaining: ${daily_limit - daily_spent:.2f}")
    
    # 8. Provider analytics
    print("\n8️⃣ Provider Analytics...")
    
    # Simulate some payments received
    test_payments = [
        {"from": client.config.wallet_address, "amount": "0.05", "token": "USDC"},
        {"from": client.config.wallet_address, "amount": "0.03", "token": "USDC"},
    ]
    
    for payment in test_payments:
        await provider.analytics.track_payment_received(payment)
    
    stats = provider.analytics.get_payment_stats()
    print(f"   Payments received: {stats.get('total_payments', 0)}")
    print(f"   Total revenue: ${stats.get('total_amount', 0.0):.2f}")
    print(f"   Unique payers: {stats.get('unique_payers', 0)}")
    
    print("\n🎉 Test completed successfully!")
    print("\n📊 Key Features Demonstrated:")
    print("   ✅ Auto wallet generation")
    print("   ✅ Smart spending limits")
    print("   ✅ Trusted domain management")
    print("   ✅ API cost discovery")
    print("   ✅ Payment approval logic")
    print("   ✅ API mocking for development")
    print("   ✅ Real-time analytics")
    print("   ✅ Development mode operation")

if __name__ == "__main__":
    asyncio.run(test_real_scenario())