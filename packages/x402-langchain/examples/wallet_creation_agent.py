"""Example of wallet creation and management for AI agents"""

import os
import asyncio
from x402_langchain import X402Client, X402Config, SpendingLimits


async def main():
    print("🤖 X402 Agent Wallet Creation Example")
    print("="*50)
    
    # Method 1: Auto-create wallet (no private key provided)
    print("\n1. Auto-creating agent wallet:")
    config1 = X402Config(
        # No private_key provided - will create new wallet
        spending_limits=SpendingLimits(
            per_request=0.10,
            per_hour=1.00,
            per_day=5.00
        ),
        auto_approve=True,
    )
    
    try:
        client1 = X402Client(config1)
        print(f"   Agent wallet: {client1.config.wallet_address}")
        
        # Export wallet (without private key)
        wallet_info = client1.export_wallet(include_private_key=False)
        print(f"   Exported info: {wallet_info}")
        
        # Get analytics
        analytics = client1.get_shared_analytics()
        if analytics:
            print(f"   Wallet analytics: {analytics}")
    except Exception as e:
        print(f"   Note: {e}")
        print("   Install required packages: pip install mnemonic eth-account")
    
    # Method 2: Create additional wallet
    print("\n2. Creating additional agent wallet:")
    try:
        address, private_key = client1.create_wallet("research_agent")
        print(f"   New wallet address: {address}")
        print(f"   Private key: {private_key[:10]}...{private_key[-10:]}")
        
        # Create client with the new wallet
        config2 = X402Config(
            private_key=private_key,
            spending_limits=SpendingLimits(
                per_request=0.05,
                per_hour=0.50,
                per_day=2.00
            ),
            auto_approve=True,
        )
        client2 = X402Client(config2)
        print(f"   Research agent initialized with wallet: {client2.config.wallet_address}")
        
    except Exception as e:
        print(f"   Error: {e}")
    
    # Method 3: Using environment variable
    print("\n3. Using wallet from environment:")
    if os.getenv("AGENT_PRIVATE_KEY"):
        config3 = X402Config(
            private_key=os.getenv("AGENT_PRIVATE_KEY"),
            spending_limits=SpendingLimits(
                per_request=1.00,
                per_hour=10.00,
                per_day=50.00
            ),
            auto_approve=True,
        )
        client3 = X402Client(config3)
        print(f"   Production agent wallet: {client3.config.wallet_address}")
    else:
        print("   No AGENT_PRIVATE_KEY environment variable set")
    
    # Demo spending status
    print("\n4. Checking spending status:")
    if 'client1' in locals():
        status = client1.get_spending_status()
        print(f"   Wallet: {status['wallet_address']}")
        print(f"   Daily limit: ${status['limits']['per_day']}")
        print(f"   Spent today: ${status['spent_today']}")
        print(f"   Remaining today: ${status['remaining']['day']}")
    
    # Demo payment simulation
    print("\n5. Simulating payment flow:")
    if 'client1' in locals():
        print("   Making a test request to a free endpoint...")
        try:
            result = await client1.fetch_with_payment(
                url="https://api.example.com/free",
                max_amount=0.10
            )
            print(f"   Result: {'Success' if result.success else 'Failed'}")
            print(f"   Cost: ${result.amount}")
        except Exception as e:
            print(f"   Request failed: {e}")
    
    print("\n✅ Agent wallet creation example complete!")
    
    # Best practices
    print("\n📚 Best Practices:")
    print("1. Store private keys securely (use environment variables or secret managers)")
    print("2. Set appropriate spending limits for each agent")
    print("3. Use separate wallets for different agent purposes")
    print("4. Monitor wallet balances and top up as needed")
    print("5. Export and backup wallet mnemonics securely")


if __name__ == "__main__":
    asyncio.run(main())