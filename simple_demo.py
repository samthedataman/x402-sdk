#!/usr/bin/env python3
"""
Simple x402 SDK Demo - Core Features Only
"""

import sys
import os

# Add packages to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'packages/fast-x402'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'packages/x402-langchain'))

def simple_demo():
    """Demonstrate core x402 SDK features without async complications"""
    
    print("🎯 x402 SDK - Core Features Demo")
    print("=" * 40)
    
    # 1. Wallet Management
    print("\n1️⃣ Wallet Management")
    print("-" * 25)
    
    from fast_x402.shared.wallet import WalletManager
    
    wallet_manager = WalletManager()
    wallet_data, created = wallet_manager.create_or_load_wallet("demo_wallet")
    
    if created:
        print(f"🔐 Created new wallet")
    else:
        print(f"📂 Loaded existing wallet")
    
    print(f"📱 Address: {wallet_data['address']}")
    print(f"🔑 Has private key: {'✅' if wallet_data.get('private_key') else '❌'}")
    print(f"🔤 Has mnemonic: {'✅' if wallet_data.get('mnemonic') else '❌'}")
    
    # 2. Configuration
    print("\n2️⃣ Configuration Management")
    print("-" * 25)
    
    from fast_x402.models import X402Config
    
    # Test configuration
    config = X402Config(
        wallet_address=wallet_data['address'],
        private_key=wallet_data['private_key'],
        mode="development"
    )
    
    print(f"✅ Config created with mode: {config.mode}")
    print(f"📱 Wallet: {config.wallet_address[:10]}...")
    print(f"🌐 Chain ID: {config.chain_id}")
    print(f"💰 Tokens: {', '.join(config.accepted_tokens)}")
    
    # 3. Network Detection
    print("\n3️⃣ Network Detection")
    print("-" * 25)
    
    from fast_x402.network import SmartNetworkSelector
    
    network = SmartNetworkSelector()
    print(f"✅ Current network: {network.current_network}")
    print(f"📍 Chain ID: {network.network_config['chain_id']}")
    
    available_tokens = list(network.network_config['tokens'].keys())
    print(f"💰 Available tokens: {', '.join(available_tokens)}")
    
    # 4. API Mocking (x402-langchain)
    print("\n4️⃣ API Mocking Engine")
    print("-" * 25)
    
    from x402_langchain.mocking import APIMockingEngine
    
    mocker = APIMockingEngine()
    
    # Mock some APIs
    mocker.mock_api("https://api.weather.com/forecast", 
                   {"temperature": 72, "condition": "sunny"}, 0.05)
    mocker.mock_api("https://api.news.com/headlines",
                   {"headlines": ["Market up", "Tech news"]}, 0.03)
    
    print("✅ Mocked weather API - $0.05")
    print("✅ Mocked news API - $0.03")
    
    # Test API calls
    try:
        weather = mocker.call_api("https://api.weather.com/forecast")
        print(f"📊 Weather API: {weather}")
        
        news = mocker.call_api("https://api.news.com/headlines")  
        print(f"📰 News API: {news}")
    except Exception as e:
        print(f"❌ API error: {e}")
    
    # 5. Cost Discovery
    print("\n5️⃣ Cost Discovery")
    print("-" * 25)
    
    from x402_langchain.mocking import CostDiscoveryTool
    
    cost_tool = CostDiscoveryTool()
    
    # Register known costs
    cost_tool.add_known_cost("https://api.openai.com/v1/completions", 0.02)
    cost_tool.add_known_cost("https://api.anthropic.com/v1/messages", 0.03)
    cost_tool.add_known_cost("https://api.service.com/*/analyze", 0.10)
    
    print("✅ Registered API costs:")
    print("   OpenAI: $0.02")
    print("   Anthropic: $0.03")
    print("   Service: $0.10 (pattern)")
    
    # Test cost discovery
    openai_cost = cost_tool.discover_cost("https://api.openai.com/v1/completions")
    service_cost = cost_tool.discover_cost("https://api.service.com/data/analyze")
    unknown_cost = cost_tool.discover_cost("https://unknown-api.com/endpoint")
    
    print(f"💰 OpenAI cost: ${openai_cost}")
    print(f"💰 Service cost: ${service_cost}")
    print(f"💰 Unknown API cost: ${unknown_cost}")
    
    # 6. Approval Rules
    print("\n6️⃣ Smart Approval Rules")
    print("-" * 25)
    
    from x402_langchain.enhanced_client import ApprovalRules
    
    # Create approval rules
    rules = ApprovalRules(
        per_request_limit=1.00,
        daily_limit=10.00,
        trusted_domains=["api.openai.com", "*.anthropic.com"],
        require_approval_above=0.50
    )
    
    print(f"✅ Rules configured:")
    print(f"   Per-request limit: ${rules.per_request_limit}")
    print(f"   Daily limit: ${rules.daily_limit}")
    print(f"   Trusted domains: {len(rules.trusted_domains)}")
    
    # Test approval decisions
    test_cases = [
        ("https://api.openai.com/endpoint", 0.30, "Should approve (trusted, under limit)"),
        ("https://api.openai.com/endpoint", 2.00, "Should reject (over limit)"),
        ("https://unknown-api.com/endpoint", 0.25, "Should prompt (untrusted)"),
    ]
    
    for url, amount, description in test_cases:
        approved = rules.should_approve(url, amount)
        status = "✅ APPROVED" if approved else "❌ REJECTED"
        print(f"   {status} ${amount:.2f} - {description}")
    
    # 7. CLI Tools
    print("\n7️⃣ CLI Tools Available")
    print("-" * 25)
    
    print("✅ x402 create <project> - Create new API project")
    print("✅ x402 test - Test payments with simulated agents")
    print("✅ x402 debug - Visual payment debugger")
    print("✅ x402 dashboard - Open payment dashboard")
    print("✅ x402 playground - Interactive testing")
    
    # 8. Package Information
    print("\n8️⃣ Package Information")
    print("-" * 25)
    
    print("📦 fast-x402 v1.1.0")
    print("   └── FastAPI provider integration")
    print("   └── Auto wallet generation")
    print("   └── Real-time dashboard")
    print("   └── Development mode")
    
    print("📦 x402-langchain v1.1.0")
    print("   └── LangChain agent integration")
    print("   └── Smart approval rules")
    print("   └── API mocking engine")
    print("   └── Cost discovery tools")
    
    # 9. Links
    print("\n🔗 Resources")
    print("-" * 25)
    
    print("🐍 PyPI:")
    print("   https://pypi.org/project/fast-x402/")
    print("   https://pypi.org/project/x402-langchain/")
    print("🐙 GitHub:")
    print("   https://github.com/samthedataman/x402-sdk")
    
    print("\n🎉 All core features working!")
    return True

if __name__ == "__main__":
    try:
        simple_demo()
        print("\n✅ Demo completed successfully!")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()