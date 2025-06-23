"""Example of creating and using wallets with fast-x402"""

import asyncio
from fast_x402 import X402Provider, X402Config


async def main():
    print("🔐 Fast-x402 Wallet Creation Example")
    print("="*50)
    
    # Method 1: Create provider without existing wallet (auto-creates)
    print("\n1. Creating provider with auto-generated wallet:")
    config1 = X402Config(
        # No wallet_address provided - will create new one
        chain_id=8453,  # Base
        accepted_tokens=["0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"],  # USDC
    )
    
    provider1 = X402Provider(config1)
    print(f"   Provider wallet: {provider1.config.wallet_address}")
    
    # Export wallet info (without private key for security)
    wallet_info = provider1.export_wallet(include_private_key=False)
    print(f"   Exported info: {wallet_info}")
    
    # Method 2: Create additional wallet manually
    print("\n2. Creating additional wallet manually:")
    try:
        address, private_key = provider1.create_wallet("merchant_wallet")
        print(f"   New wallet address: {address}")
        print(f"   Private key: {private_key[:10]}...{private_key[-10:]}")
    except Exception as e:
        print(f"   Note: {e}")
        print("   Install 'mnemonic' package for wallet creation: pip install mnemonic")
    
    # Method 3: Use existing wallet
    print("\n3. Using existing wallet:")
    config2 = X402Config(
        wallet_address="0x742d35Cc6634C0532925a3b844Bc9e7595f5b123",
        chain_id=8453,
        accepted_tokens=["0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"],
    )
    
    provider2 = X402Provider(config2)
    print(f"   Provider wallet: {provider2.config.wallet_address}")
    
    # Show analytics integration
    print("\n4. Analytics Integration:")
    analytics = provider1.get_shared_analytics()
    if analytics:
        print(f"   Shared analytics available: {analytics}")
    else:
        print("   Shared analytics not configured")
    
    # Create payment requirement
    print("\n5. Creating payment requirement:")
    requirement = provider1.create_payment_requirement(
        amount="0.10",
        endpoint="/api/premium-data"
    )
    
    print(f"   Payment to: {requirement.recipient}")
    print(f"   Amount: ${requirement.amount}")
    print(f"   Token: {requirement.token}")
    print(f"   Expires: {requirement.expires_at}")
    
    print("\n✅ Wallet creation example complete!")


if __name__ == "__main__":
    asyncio.run(main())