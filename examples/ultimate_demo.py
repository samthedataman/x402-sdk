"""Ultimate demo showcasing all x402 SDK convenience features"""

import asyncio
import sys
import os
from pathlib import Path

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent.parent / "packages" / "fast-x402"))
sys.path.insert(0, str(Path(__file__).parent.parent / "packages" / "x402-langchain"))

from fast_x402.enhanced_provider import EnhancedX402Provider
from fast_x402.cli import create_fastapi_example
from x402_langchain.enhanced_client import EnhancedX402Client


async def demo_provider_features():
    """Demonstrate all provider SDK convenience features"""
    
    print("\n" + "="*60)
    print("🚀 PROVIDER SDK CONVENIENCE FEATURES DEMO")
    print("="*60)
    
    # 1. Zero-config setup
    print("\n1️⃣ Zero-Config Provider Setup")
    provider = EnhancedX402Provider(mode="development")
    print(f"   ✅ Auto-created wallet: {provider.config.wallet_address}")
    print(f"   ✅ Auto-detected network: {provider.mode}")
    print(f"   ✅ Dashboard available at: http://localhost:3001")
    
    # 2. Token presets
    print("\n2️⃣ Easy Token Configuration")
    provider.accept_tokens(["USDC", "USDT", "DAI"])
    print("   ✅ Added support for major stablecoins with one line")
    
    # 3. Local development mode
    print("\n3️⃣ Local Development Mode")
    print("   ✅ No blockchain needed - instant testing")
    print("   ✅ Simulated payments with zero cost")
    print("   ✅ Test agents with unlimited funds")
    
    # Create test agents
    if provider.dev_mode:
        provider.dev_mode.create_test_agent("test-agent-1", balance=50.0)
        provider.dev_mode.create_test_agent("test-agent-2", balance=100.0)
        print("   ✅ Created 2 test agents with funds")
    
    # 4. Real-time dashboard
    print("\n4️⃣ Real-Time Dashboard")
    print("   ✅ Live payment feed")
    print("   ✅ Revenue analytics")
    print("   ✅ Agent breakdown")
    print("   💡 Open http://localhost:3001 to see dashboard")
    
    # 5. Developer-friendly errors
    print("\n5️⃣ Clear Error Messages")
    print("   ❌ Instead of: 'EIP712Domain hash mismatch'")
    print("   ✅ You see: 'Wrong network. Expected Base, got Polygon'")
    
    # 6. API documentation generation
    print("\n6️⃣ Auto-Generated Documentation")
    provider.generate_docs()
    print("   ✅ Created docs/pricing.md")
    print("   ✅ Created docs/x402-api.postman.json")
    
    # 7. Test scenarios
    print("\n7️⃣ Built-in Test Scenarios")
    if provider.dev_mode:
        scenario = provider.create_test_scenario("aggressive")
        print("   ✅ Running aggressive agent scenario...")
        # Run for just a few payments
        await asyncio.wait_for(
            scenario(provider.config.wallet_address),
            timeout=3.0
        )
    
    # Show stats
    print("\n📊 Development Mode Stats:")
    stats = provider.get_test_stats()
    print(f"   Total payments: {stats.get('total_payments', 0)}")
    print(f"   Total revenue: ${stats.get('total_revenue', 0):.2f}")
    print(f"   Test agents: {stats.get('test_agents', 0)}")


async def demo_agent_features():
    """Demonstrate all agent SDK convenience features"""
    
    print("\n" + "="*60)
    print("🤖 AGENT SDK CONVENIENCE FEATURES DEMO")
    print("="*60)
    
    # 1. Auto wallet creation
    print("\n1️⃣ Automatic Wallet Creation")
    agent = EnhancedX402Client(mode="development", auto_fund=True)
    print(f"   ✅ Auto-created wallet: {agent.config.wallet_address}")
    print(f"   ✅ Auto-funding enabled in development")
    
    # 2. API mocking
    print("\n2️⃣ API Mocking for Testing")
    agent.mocking_engine.mock_api(
        "custom.api/data",
        {"result": "mocked response", "quality": "high"},
        cost=0.03
    )
    
    # Test mocked API
    result = await agent.fetch_with_payment("custom.api/data")
    print(f"   ✅ Mocked API response: {result.data}")
    print(f"   ✅ Cost: ${result.amount}")
    
    # 3. Cost discovery
    print("\n3️⃣ Cost Discovery Tool")
    # Mock some costs
    agent.cost_discovery.discovered_costs["expensive.api"] = 1.00
    agent.cost_discovery.discovered_costs["cheap.api"] = 0.01
    agent.cost_discovery.discovered_costs["medium.api"] = 0.10
    
    cost_summary = agent.cost_discovery.get_cost_summary()
    print(f"   ✅ Discovered {cost_summary['total_apis_discovered']} APIs")
    print(f"   ✅ Average cost: ${cost_summary['average_cost']:.2f}")
    
    # Find alternatives
    alternatives = agent.cost_discovery.find_alternatives("expensive.api", 0.50)
    if alternatives:
        print(f"   ✅ Found cheaper alternatives: {alternatives[0]['url']} (${alternatives[0]['cost']})")
    
    # 4. Smart approval rules
    print("\n4️⃣ Smart Approval Rules")
    agent.set_approval_rules({
        "trusted_domains": ["weather.com", "news.com"],
        "max_per_request": 0.10,
        "require_approval_above": 1.00
    })
    print("   ✅ Configured auto-approval for trusted domains")
    print("   ✅ Set spending limits")
    
    # 5. Batch payments
    print("\n5️⃣ Batch API Calls")
    urls = [
        "weather.api/NYC",
        "weather.api/LA", 
        "weather.api/Chicago"
    ]
    
    # Simulate batch with mocks
    for url in urls:
        agent.mocking_engine.mock_api(url, {"temp": 72}, cost=0.01)
    
    results = await agent.batch_pay_and_fetch(urls, max_total=0.05)
    print(f"   ✅ Batched {len(results)} API calls efficiently")
    
    # 6. Dry run mode
    print("\n6️⃣ Dry Run Mode")
    dry_run_result = await agent.dry_run("Get weather for 10 cities")
    print(f"   ✅ Simulated task without spending")
    
    # 7. API intelligence
    print("\n7️⃣ Shared API Intelligence")
    agent.enable_collective_learning()
    
    # Show what agent learned
    api_info = agent.api_intelligence.get_api_info("weather.api/NYC")
    if api_info:
        print(f"   ✅ Learned API cost: ${api_info['cost']}")
        print(f"   ✅ Quality score: {api_info['quality_score']:.2f}")
    
    # 8. Spending analytics
    print("\n8️⃣ Detailed Analytics")
    analytics = agent.get_spending_analytics()
    print(f"   ✅ Tracked spending: ${analytics['spent_today']:.2f}")
    print(f"   ✅ APIs discovered: {len(analytics['api_costs'])}")
    if 'mock_stats' in analytics:
        print(f"   ✅ Mock API calls: {analytics['mock_stats']['total_calls']}")
    
    # Export learnings
    agent.export_learnings()
    print("   ✅ Exported agent learnings to agent_learnings.json")


async def demo_integration():
    """Demonstrate how both SDKs work together"""
    
    print("\n" + "="*60)
    print("🔗 INTEGRATION DEMO - PROVIDER + AGENT")
    print("="*60)
    
    # Create provider
    provider = EnhancedX402Provider(mode="development")
    
    # Create agent
    agent = EnhancedX402Client(mode="development")
    
    # Provider optimizes for agents
    print("\n✨ Provider optimizes for agent patterns")
    print("✨ Agent prefers x402-enabled APIs")
    
    # Simulate end-to-end flow
    print("\n🔄 End-to-End Payment Flow:")
    
    # 1. Agent discovers API
    print("1. Agent discovers API costs")
    
    # 2. Provider creates requirement
    requirement = provider.create_payment_requirement(
        amount="0.05",
        endpoint="/api/analyze"
    )
    print(f"2. Provider requires: ${requirement.amount}")
    
    # 3. Agent makes payment (mocked)
    if agent.mocking_engine:
        agent.mocking_engine.mock_api(
            "http://localhost:8000/api/analyze",
            {"analysis": "complete"},
            cost=0.05
        )
    
    result = await agent.fetch_with_payment("http://localhost:8000/api/analyze")
    print(f"3. Agent paid: ${result.amount}")
    print(f"4. Agent received: {result.data}")
    
    # 5. Both track analytics
    print("\n📊 Both SDKs track analytics:")
    print(f"   Provider revenue: ${provider.get_test_stats().get('total_revenue', 0):.2f}")
    print(f"   Agent spending: ${agent.get_spending_status()['spent_today']:.2f}")


async def main():
    """Run all demos"""
    
    print("\n🎉 X402 SDK ULTIMATE CONVENIENCE DEMO")
    print("Showcasing all developer-friendly features")
    
    try:
        # Demo provider features
        await demo_provider_features()
        
        # Demo agent features  
        await demo_agent_features()
        
        # Demo integration
        await demo_integration()
        
        print("\n" + "="*60)
        print("✅ DEMO COMPLETE!")
        print("="*60)
        
        print("\n📚 Key Takeaways:")
        print("1. Zero configuration needed - everything just works")
        print("2. Local development without blockchain complexity")
        print("3. Clear, actionable error messages")
        print("4. Built-in testing and monitoring tools")
        print("5. Smart defaults with full customization")
        print("6. Both SDKs work seamlessly together")
        
        print("\n🚀 Ready to build? Try:")
        print("   pip install fast-x402 x402-langchain")
        print("   x402 create my-api")
        
    except asyncio.TimeoutError:
        print("\n⏱️ Demo timeout (this is normal for the demo)")
    except Exception as e:
        print(f"\n❌ Demo error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())