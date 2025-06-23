"""
Enhanced network detection and configuration for x402 SDK
Supports all popular blockchain networks with automatic failover
"""

import os
from typing import Dict, Any, Optional, Tuple, List
from enum import Enum
from .rpc_manager import get_rpc_manager, get_supported_chains, get_chain_info, NETWORK_CONFIGS

class NetworkType(str, Enum):
    """Enhanced network enumeration supporting all popular chains"""
    # Major EVM Networks
    ETHEREUM = "ethereum"
    POLYGON = "polygon"
    ARBITRUM = "arbitrum"
    OPTIMISM = "optimism"
    BASE = "base"
    AVALANCHE = "avalanche"
    BSC = "bsc"
    FANTOM = "fantom"
    CRONOS = "cronos"
    MOONBEAM = "moonbeam"
    GNOSIS = "gnosis"
    CELO = "celo"
    AURORA = "aurora"
    HARMONY = "harmony"
    KAVA = "kava"
    EVMOS = "evmos"
    
    # Layer 2 Solutions
    ZKSYNC = "zksync"
    POLYGON_ZKEVM = "polygon-zkevm"
    LINEA = "linea"
    SCROLL = "scroll"
    
    # Testnets
    GOERLI = "goerli"
    SEPOLIA = "sepolia"
    BASE_SEPOLIA = "base-sepolia"
    
    # Non-EVM
    SOLANA = "solana"
    SOLANA_DEVNET = "solana-devnet"
    
    # Development
    LOCAL = "local"

# Enhanced token configurations for all supported networks
ENHANCED_TOKEN_CONFIGS = {
    # Ethereum Mainnet
    "ethereum": {
        "USDC": {
            "address": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            "decimals": 6,
            "eip712": {"name": "USD Coin", "version": "2"},
        },
        "USDT": {
            "address": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
            "decimals": 6,
            "eip712": {"name": "Tether USD", "version": "1"},
        },
        "DAI": {
            "address": "0x6B175474E89094C44Da98b954EedeAC495271d0F",
            "decimals": 18,
            "eip712": {"name": "Dai Stablecoin", "version": "1"},
        },
    },
    
    # Polygon
    "polygon": {
        "USDC": {
            "address": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",
            "decimals": 6,
            "eip712": {"name": "USD Coin", "version": "2"},
        },
        "USDT": {
            "address": "0xc2132D05D31c914a87C6611C10748AEb04B58e8F",
            "decimals": 6,
            "eip712": {"name": "Tether USD", "version": "1"},
        },
        "DAI": {
            "address": "0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063",
            "decimals": 18,
            "eip712": {"name": "Dai Stablecoin", "version": "1"},
        },
    },
    
    # Arbitrum
    "arbitrum": {
        "USDC": {
            "address": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
            "decimals": 6,
            "eip712": {"name": "USD Coin", "version": "2"},
        },
        "USDT": {
            "address": "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9",
            "decimals": 6,
            "eip712": {"name": "Tether USD", "version": "1"},
        },
        "DAI": {
            "address": "0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1",
            "decimals": 18,
            "eip712": {"name": "Dai Stablecoin", "version": "1"},
        },
    },
    
    # Optimism
    "optimism": {
        "USDC": {
            "address": "0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85",
            "decimals": 6,
            "eip712": {"name": "USD Coin", "version": "2"},
        },
        "USDT": {
            "address": "0x94b008aA00579c1307B0EF2c499aD98a8ce58e58",
            "decimals": 6,
            "eip712": {"name": "Tether USD", "version": "1"},
        },
        "DAI": {
            "address": "0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1",
            "decimals": 18,
            "eip712": {"name": "Dai Stablecoin", "version": "1"},
        },
    },
    
    # Base
    "base": {
        "USDC": {
            "address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
            "decimals": 6,
            "eip712": {"name": "USD Coin", "version": "2"},
        },
        "USDT": {
            "address": "0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb",
            "decimals": 6,
            "eip712": {"name": "Tether USD", "version": "1"},
        },
    },
    
    # BSC
    "bsc": {
        "USDC": {
            "address": "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d",
            "decimals": 18,
            "eip712": {"name": "USD Coin", "version": "2"},
        },
        "USDT": {
            "address": "0x55d398326f99059fF775485246999027B3197955",
            "decimals": 18,
            "eip712": {"name": "Tether USD", "version": "1"},
        },
        "BUSD": {
            "address": "0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56",
            "decimals": 18,
            "eip712": {"name": "BUSD Token", "version": "1"},
        },
    },
    
    # Avalanche
    "avalanche": {
        "USDC": {
            "address": "0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E",
            "decimals": 6,
            "eip712": {"name": "USD Coin", "version": "2"},
        },
        "USDT": {
            "address": "0x9702230A8Ea53601f5cD2dc00fDBc13d4dF4A8c7",
            "decimals": 6,
            "eip712": {"name": "Tether USD", "version": "1"},
        },
    },
    
    # Fantom
    "fantom": {
        "USDC": {
            "address": "0x04068DA6C83AFCFA0e13ba15A6696662335D5B75",
            "decimals": 6,
            "eip712": {"name": "USD Coin", "version": "2"},
        },
        "USDT": {
            "address": "0x049d68029688eAbF473097a2fC38ef61633A3C7A",
            "decimals": 6,
            "eip712": {"name": "Tether USD", "version": "1"},
        },
    },
    
    # Testnets
    "base-sepolia": {
        "USDC": {
            "address": "0x036CbD53842c5426634e7929541eC2318f3dCF7e",
            "decimals": 6,
            "eip712": {"name": "USD Coin", "version": "2"},
        },
    },
    
    "goerli": {
        "USDC": {
            "address": "0x07865c6E87B9F70255377e024ace6630C1Eaa37F",
            "decimals": 6,
            "eip712": {"name": "USD Coin", "version": "2"},
        },
    },
    
    "sepolia": {
        "USDC": {
            "address": "0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238",
            "decimals": 6,
            "eip712": {"name": "USD Coin", "version": "2"},
        },
    },
    
    # Solana (SPL tokens)
    "solana": {
        "USDC": {
            "address": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            "decimals": 6,
            "program_id": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
        },
        "USDT": {
            "address": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
            "decimals": 6,
            "program_id": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
        },
    },
    
    # Local development
    "local": {
        "MOCK": {
            "address": "0x0000000000000000000000000000000000000001",
            "decimals": 6,
            "eip712": {"name": "Mock Token", "version": "1"},
        },
    },
}

# Facilitator service configurations
FACILITATOR_CONFIGS = {
    "ethereum": "https://x402-facilitator.ethereum.org",
    "polygon": "https://x402-facilitator.polygon.com",
    "arbitrum": "https://x402-facilitator.arbitrum.io",
    "optimism": "https://x402-facilitator.optimism.io",
    "base": "https://api.coinbase.com/rpc/v1/base/x402",
    "avalanche": "https://x402-facilitator.avax.network",
    "bsc": "https://x402-facilitator.bnbchain.org",
    "fantom": "https://x402-facilitator.fantom.foundation",
    
    # Testnets
    "base-sepolia": "https://api.coinbase.com/rpc/v1/base-sepolia/x402",
    "goerli": "https://x402-facilitator-goerli.ethereum.org",
    "sepolia": "https://x402-facilitator-sepolia.ethereum.org",
    
    # Solana
    "solana": "https://x402-facilitator.solana.com",
    "solana-devnet": "https://x402-facilitator-devnet.solana.com",
    
    # Local
    "local": "http://localhost:8545/x402",
}

class EnhancedNetworkConfig:
    """Enhanced network configuration supporting all popular chains"""
    
    @classmethod
    def detect_network(cls) -> Tuple[str, Dict[str, Any]]:
        """Automatically detect the best network based on environment"""
        
        # 1. Check explicit environment variable
        if os.getenv("X402_NETWORK"):
            network = os.getenv("X402_NETWORK").lower()
            if network in NETWORK_CONFIGS:
                return network, cls._build_config(network)
        
        # 2. Check chain-specific environment variables
        if os.getenv("ETHEREUM_RPC_URL"):
            return "ethereum", cls._build_config("ethereum")
        elif os.getenv("POLYGON_RPC_URL"):
            return "polygon", cls._build_config("polygon")
        elif os.getenv("ARBITRUM_RPC_URL"):
            return "arbitrum", cls._build_config("arbitrum")
        elif os.getenv("BASE_RPC_URL"):
            return "base", cls._build_config("base")
        
        # 3. Check environment mode
        if os.getenv("NODE_ENV") == "development" or os.getenv("FLASK_ENV") == "development":
            return "base-sepolia", cls._build_config("base-sepolia")
        
        # 4. Check if running locally
        if os.getenv("CI") is None and os.path.exists(".git"):
            return "base-sepolia", cls._build_config("base-sepolia")
        
        # 5. Production mode - prefer Base for x402
        if os.getenv("NODE_ENV") == "production" or os.getenv("FLASK_ENV") == "production":
            return "base", cls._build_config("base")
        
        # 6. Default to Base Sepolia testnet for safety
        return "base-sepolia", cls._build_config("base-sepolia")
    
    @classmethod
    def _build_config(cls, network: str) -> Dict[str, Any]:
        """Build complete network configuration"""
        network_info = NETWORK_CONFIGS.get(network)
        if not network_info:
            raise ValueError(f"Unsupported network: {network}")
        
        return {
            "name": network_info.name,
            "chain_id": network_info.chain_id,
            "chain_type": network_info.chain_type.value,
            "native_currency": network_info.native_currency,
            "facilitator_url": FACILITATOR_CONFIGS.get(network, ""),
            "tokens": ENHANCED_TOKEN_CONFIGS.get(network, {}),
            "explorer": network_info.explorer_url,
            "is_testnet": network_info.testnet,
            "gas_token": network_info.native_currency,
        }
    
    @classmethod
    def get_token_config(cls, network: str, token_symbol: str) -> Optional[Dict[str, Any]]:
        """Get token configuration for a network"""
        tokens = ENHANCED_TOKEN_CONFIGS.get(network, {})
        return tokens.get(token_symbol.upper())
    
    @classmethod
    def get_facilitator_url(cls, network: str) -> str:
        """Get facilitator URL for a network"""
        # Allow override via environment
        env_key = f"X402_FACILITATOR_URL_{network.upper()}"
        if os.getenv(env_key):
            return os.getenv(env_key)
        
        if os.getenv("X402_FACILITATOR_URL"):
            return os.getenv("X402_FACILITATOR_URL")
        
        return FACILITATOR_CONFIGS.get(network, "")
    
    @classmethod
    def is_testnet(cls, network: str) -> bool:
        """Check if network is a testnet"""
        network_info = NETWORK_CONFIGS.get(network)
        return network_info.testnet if network_info else True
    
    @classmethod
    def get_supported_networks(cls, include_testnets: bool = True) -> List[str]:
        """Get list of supported networks"""
        return get_supported_chains(include_testnets)
    
    @classmethod
    def get_evm_networks(cls) -> List[str]:
        """Get list of EVM-compatible networks"""
        return [
            network for network, info in NETWORK_CONFIGS.items()
            if info.chain_type.value == "evm"
        ]
    
    @classmethod
    def get_non_evm_networks(cls) -> List[str]:
        """Get list of non-EVM networks"""
        return [
            network for network, info in NETWORK_CONFIGS.items()
            if info.chain_type.value != "evm"
        ]

class EnhancedSmartNetworkSelector:
    """Enhanced network selector with multi-chain support"""
    
    def __init__(self, preferred_network: Optional[str] = None):
        self.current_network = None
        self.network_config = None
        self.rpc_manager = None
        self._initialize(preferred_network)
    
    async def _async_initialize(self, preferred_network: Optional[str] = None):
        """Async initialization for RPC manager"""
        self.rpc_manager = await get_rpc_manager()
        if preferred_network and preferred_network in NETWORK_CONFIGS:
            self.current_network = preferred_network
            self.network_config = EnhancedNetworkConfig._build_config(preferred_network)
        else:
            self._detect_and_configure()
    
    def _initialize(self, preferred_network: Optional[str] = None):
        """Sync initialization"""
        if preferred_network and preferred_network in NETWORK_CONFIGS:
            self.current_network = preferred_network
            self.network_config = EnhancedNetworkConfig._build_config(preferred_network)
        else:
            self._detect_and_configure()
    
    def _detect_and_configure(self):
        """Detect network and configure accordingly"""
        self.current_network, self.network_config = EnhancedNetworkConfig.detect_network()
        
        # Log the detection
        print(f"🌐 Detected network: {self.network_config['name']}")
        
        if self.network_config["is_testnet"]:
            print("   ⚠️  Running on testnet - payments are simulated")
        else:
            print("   💰 Running on mainnet - real payments enabled")
    
    def get_chain_id(self) -> int:
        """Get current chain ID"""
        return self.network_config["chain_id"]
    
    def get_chain_type(self) -> str:
        """Get current chain type (evm, solana, etc.)"""
        return self.network_config["chain_type"]
    
    def get_facilitator_url(self) -> str:
        """Get facilitator URL"""
        return EnhancedNetworkConfig.get_facilitator_url(self.current_network)
    
    def get_token_address(self, symbol: str = "USDC") -> str:
        """Get token address for current network"""
        token_config = EnhancedNetworkConfig.get_token_config(self.current_network, symbol)
        if not token_config:
            raise ValueError(f"Token {symbol} not configured for {self.current_network}")
        
        return token_config["address"]
    
    def get_token_config(self, symbol: str = "USDC") -> Dict[str, Any]:
        """Get full token configuration"""
        return EnhancedNetworkConfig.get_token_config(self.current_network, symbol)
    
    def get_available_tokens(self) -> List[str]:
        """Get list of available tokens on current network"""
        tokens = ENHANCED_TOKEN_CONFIGS.get(self.current_network, {})
        return list(tokens.keys())
    
    def switch_network(self, network: str):
        """Switch to a different network"""
        if network not in NETWORK_CONFIGS:
            raise ValueError(f"Unknown network: {network}")
        
        self.current_network = network
        self.network_config = EnhancedNetworkConfig._build_config(network)
        
        print(f"🔄 Switched to network: {self.network_config['name']}")
    
    def get_explorer_url(self, address: str) -> str:
        """Get block explorer URL for an address"""
        base_url = self.network_config["explorer"]
        return f"{base_url}/address/{address}"
    
    def get_tx_explorer_url(self, tx_hash: str) -> str:
        """Get block explorer URL for a transaction"""
        base_url = self.network_config["explorer"]
        if self.get_chain_type() == "solana":
            return f"{base_url}/tx/{tx_hash}"
        else:
            return f"{base_url}/tx/{tx_hash}"
    
    def is_evm_compatible(self) -> bool:
        """Check if current network is EVM compatible"""
        return self.network_config["chain_type"] == "evm"
    
    def is_solana_compatible(self) -> bool:
        """Check if current network is Solana compatible"""
        return self.network_config["chain_type"] == "solana"
    
    def get_native_currency(self) -> str:
        """Get native currency symbol"""
        return self.network_config["native_currency"]
    
    def get_gas_token(self) -> str:
        """Get gas token symbol"""
        return self.network_config["gas_token"]
    
    def is_mainnet(self) -> bool:
        """Check if current network is mainnet"""
        return not self.network_config["is_testnet"]
    
    def is_testnet(self) -> bool:
        """Check if current network is testnet"""
        return self.network_config["is_testnet"]
    
    def get_network_summary(self) -> Dict[str, Any]:
        """Get comprehensive network summary"""
        return {
            "network": self.current_network,
            "name": self.network_config["name"],
            "chain_id": self.network_config["chain_id"],
            "chain_type": self.network_config["chain_type"],
            "native_currency": self.network_config["native_currency"],
            "is_testnet": self.network_config["is_testnet"],
            "available_tokens": self.get_available_tokens(),
            "explorer": self.network_config["explorer"],
            "facilitator_url": self.get_facilitator_url(),
        }
    
    def to_config_dict(self) -> Dict[str, Any]:
        """Convert to configuration dictionary"""
        return {
            "network": self.current_network,
            "chain_id": self.network_config["chain_id"],
            "chain_type": self.network_config["chain_type"],
            "facilitator_url": self.get_facilitator_url(),
            "is_testnet": self.network_config["is_testnet"],
            "tokens": self.network_config["tokens"],
            "native_currency": self.network_config["native_currency"],
        }

# Convenience functions
def get_all_supported_networks(include_testnets: bool = True) -> List[str]:
    """Get all supported networks"""
    return EnhancedNetworkConfig.get_supported_networks(include_testnets)

def get_network_info(network: str) -> Optional[Dict[str, Any]]:
    """Get network information"""
    return get_chain_info(network)

def is_network_supported(network: str) -> bool:
    """Check if a network is supported"""
    return network.lower() in NETWORK_CONFIGS

def get_token_addresses(network: str) -> Dict[str, str]:
    """Get all token addresses for a network"""
    tokens = ENHANCED_TOKEN_CONFIGS.get(network, {})
    return {symbol: config["address"] for symbol, config in tokens.items()}

# Backward compatibility aliases
NetworkConfig = EnhancedNetworkConfig
SmartNetworkSelector = EnhancedSmartNetworkSelector
Network = NetworkType