#!/usr/bin/env python3
"""
Verify all chains from chain_map are properly configured in x402 SDK
"""

import sys
import os

# Add packages to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'packages/fast-x402'))

def verify_chain_coverage():
    """Verify all chains from the user's chain_map are covered"""
    
    # User's chain_map requirement
    required_chains = {
        "ethereum": "ethereum",
        "bsc": "bsc", 
        "polygon": "polygon",
        "arbitrum": "arbitrum",
        "optimism": "optimism",
        "avalanche": "avalanche",
        "base": "base",
        "fantom": "fantom",
        "gnosis": "gnosis",
        "celo": "celo",
        "moonbeam": "moonbeam",
        "moonriver": "moonriver",
        "cronos": "cronos",
        "aurora": "aurora",
        "harmony": "harmony",
        "metis": "metis",
        "boba": "boba",
        "okexchain": "okexchain",
        "heco": "heco",
        "kcc": "kcc",
        "velas": "velas",
        "oasis": "oasis",
        "telos": "telos",
        "dfk": "dfk",
        "klaytn": "klaytn",
        "iotex": "iotex",
        "thundercore": "thundercore",
        "solana": "solana",
        "algorand": "algorand",
        "aptos": "aptos",
        "sui": "sui",
        "hedera": "hedera",
        "injective": "injective",
        "osmosis": "osmosis",
        "evmos": "evmos",
        "arbitrum nova": "arbitrum-nova",
        "canto": "canto",
        "kava": "kava",
        "meter": "meter",
        "tron": "tron",
        "linea": "linea",
        "mantle": "mantle",
        "zksync era": "zksync",
        "polygon zkevm": "polygonzkevm",
        "scroll": "scroll",
        "manta": "manta",
        "blast": "blast",
        "sonic": "sonic",
        "berachain": "berachain",
        "fraxtal": "fraxtal",
        "neutron": "neutron",
        "op_bnb": "opbnb",
        "opbnb": "opbnb",
    }
    
    try:
        from fast_x402.rpc_manager import NETWORK_CONFIGS
        from fast_x402.enhanced_network import ENHANCED_TOKEN_CONFIGS, FACILITATOR_CONFIGS
        
        print("🔍 Verifying chain coverage...")
        print(f"Required chains: {len(required_chains)}")
        print(f"Configured networks: {len(NETWORK_CONFIGS)}")
        print(f"Token configs: {len(ENHANCED_TOKEN_CONFIGS)}")
        print(f"Facilitator configs: {len(FACILITATOR_CONFIGS)}")
        
        missing_networks = []
        missing_tokens = []
        missing_facilitators = []
        
        # Check network configurations
        for chain_name, chain_key in required_chains.items():
            if chain_key not in NETWORK_CONFIGS:
                missing_networks.append(f"{chain_name} -> {chain_key}")
        
        # Check token configurations (only for EVM chains that should have tokens)
        evm_chains_with_tokens = [
            "ethereum", "bsc", "polygon", "arbitrum", "optimism", "avalanche", 
            "base", "fantom", "gnosis", "celo", "moonbeam", "moonriver", 
            "cronos", "aurora", "harmony", "kava", "evmos", "klaytn", 
            "linea", "scroll", "zksync", "polygonzkevm", "mantle", 
            "arbitrum-nova", "blast", "manta", "opbnb"
        ]
        
        for chain_key in evm_chains_with_tokens:
            if chain_key in NETWORK_CONFIGS and chain_key not in ENHANCED_TOKEN_CONFIGS:
                missing_tokens.append(chain_key)
        
        # Check facilitator configurations
        for chain_name, chain_key in required_chains.items():
            if chain_key not in FACILITATOR_CONFIGS:
                missing_facilitators.append(f"{chain_name} -> {chain_key}")
        
        # Report results
        print("\n" + "="*60)
        print("📊 VERIFICATION RESULTS")
        print("="*60)
        
        if not missing_networks:
            print("✅ All required networks are configured!")
        else:
            print(f"❌ Missing {len(missing_networks)} network configurations:")
            for missing in missing_networks:
                print(f"   - {missing}")
        
        if not missing_tokens:
            print("✅ All EVM networks have token configurations!")
        else:
            print(f"⚠️  Missing {len(missing_tokens)} token configurations:")
            for missing in missing_tokens:
                print(f"   - {missing}")
        
        if not missing_facilitators:
            print("✅ All networks have facilitator URLs!")
        else:
            print(f"❌ Missing {len(missing_facilitators)} facilitator configurations:")
            for missing in missing_facilitators:
                print(f"   - {missing}")
        
        # Additional statistics
        print(f"\n📈 Coverage Statistics:")
        print(f"   Networks: {len(NETWORK_CONFIGS) - len(missing_networks)}/{len(required_chains)} ({(len(NETWORK_CONFIGS) - len(missing_networks))/len(required_chains)*100:.1f}%)")
        print(f"   Tokens: {len([k for k in evm_chains_with_tokens if k in ENHANCED_TOKEN_CONFIGS])}/{len(evm_chains_with_tokens)} EVM chains")
        print(f"   Facilitators: {len(FACILITATOR_CONFIGS) - len(missing_facilitators)}/{len(required_chains)} ({(len(FACILITATOR_CONFIGS) - len(missing_facilitators))/len(required_chains)*100:.1f}%)")
        
        # Show chain types
        print(f"\n🔗 Chain Type Breakdown:")
        from fast_x402.rpc_manager import ChainType
        chain_types = {}
        for network_key, network_info in NETWORK_CONFIGS.items():
            chain_type = network_info.chain_type.value
            if chain_type not in chain_types:
                chain_types[chain_type] = 0
            chain_types[chain_type] += 1
        
        for chain_type, count in chain_types.items():
            print(f"   {chain_type.upper()}: {count} networks")
        
        # Success check
        total_missing = len(missing_networks) + len(missing_facilitators)
        if total_missing == 0:
            print("\n🎉 ALL CHAINS SUCCESSFULLY CONFIGURED!")
            return True
        else:
            print(f"\n⚠️  {total_missing} configuration issues found")
            return False
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Verification error: {e}")
        return False

if __name__ == "__main__":
    success = verify_chain_coverage()
    sys.exit(0 if success else 1)