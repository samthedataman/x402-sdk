"""Smart network detection and configuration for x402"""

import os
from typing import Dict, Any, Optional, Tuple
from enum import Enum


class Network(str, Enum):
    """Supported networks"""
    BASE_MAINNET = "base"
    BASE_SEPOLIA = "base-sepolia"
    POLYGON_MAINNET = "polygon"
    POLYGON_MUMBAI = "polygon-mumbai"
    ARBITRUM_MAINNET = "arbitrum"
    ARBITRUM_SEPOLIA = "arbitrum-sepolia"
    LOCAL = "local"


class NetworkConfig:
    """Network-specific configuration"""
    
    CONFIGS = {
        Network.BASE_MAINNET: {
            "chain_id": 8453,
            "name": "Base Mainnet",
            "facilitator_url": "https://api.coinbase.com/rpc/v1/base/x402",
            "tokens": {
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
            "explorer": "https://basescan.org",
            "gas_token": "ETH",
            "is_testnet": False,
        },
        Network.BASE_SEPOLIA: {
            "chain_id": 84532,
            "name": "Base Sepolia Testnet",
            "facilitator_url": "https://api.coinbase.com/rpc/v1/base-sepolia/x402",
            "tokens": {
                "USDC": {
                    "address": "0x036CbD53842c5426634e7929541eC2318f3dCF7e",
                    "decimals": 6,
                    "eip712": {"name": "USD Coin", "version": "2"},
                },
            },
            "explorer": "https://sepolia.basescan.org",
            "gas_token": "ETH",
            "is_testnet": True,
            "faucets": [
                "https://faucet.quicknode.com/base-sepolia",
                "https://sepoliafaucet.com",
            ],
        },
        Network.POLYGON_MAINNET: {
            "chain_id": 137,
            "name": "Polygon Mainnet",
            "facilitator_url": "https://x402-facilitator.polygon.com",
            "tokens": {
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
            },
            "explorer": "https://polygonscan.com",
            "gas_token": "MATIC",
            "is_testnet": False,
        },
        Network.LOCAL: {
            "chain_id": 31337,
            "name": "Local Development",
            "facilitator_url": "http://localhost:8545/x402",
            "tokens": {
                "MOCK": {
                    "address": "0x0000000000000000000000000000000000000001",
                    "decimals": 6,
                    "eip712": {"name": "Mock Token", "version": "1"},
                },
            },
            "explorer": "http://localhost:3000",
            "gas_token": "ETH",
            "is_testnet": True,
        },
    }
    
    @classmethod
    def detect_network(cls) -> Tuple[Network, Dict[str, Any]]:
        """Automatically detect the best network based on environment"""
        
        # 1. Check explicit environment variable
        if os.getenv("X402_NETWORK"):
            network = Network(os.getenv("X402_NETWORK"))
            return network, cls.CONFIGS[network]
        
        # 2. Check if running in development mode
        if os.getenv("NODE_ENV") == "development" or os.getenv("FLASK_ENV") == "development":
            return Network.BASE_SEPOLIA, cls.CONFIGS[Network.BASE_SEPOLIA]
        
        # 3. Check if running locally
        if os.getenv("CI") is None and os.path.exists(".git"):
            # Local development detected
            return Network.BASE_SEPOLIA, cls.CONFIGS[Network.BASE_SEPOLIA]
        
        # 4. Check if running in production
        if os.getenv("NODE_ENV") == "production" or os.getenv("FLASK_ENV") == "production":
            return Network.BASE_MAINNET, cls.CONFIGS[Network.BASE_MAINNET]
        
        # 5. Default to testnet for safety
        return Network.BASE_SEPOLIA, cls.CONFIGS[Network.BASE_SEPOLIA]
    
    @classmethod
    def get_token_config(cls, network: Network, token_symbol: str) -> Optional[Dict[str, Any]]:
        """Get token configuration for a network"""
        
        network_config = cls.CONFIGS.get(network)
        if not network_config:
            return None
        
        return network_config["tokens"].get(token_symbol.upper())
    
    @classmethod
    def get_facilitator_url(cls, network: Network) -> str:
        """Get facilitator URL for a network"""
        
        config = cls.CONFIGS.get(network)
        if not config:
            raise ValueError(f"Unknown network: {network}")
        
        # Allow override via environment
        return os.getenv("X402_FACILITATOR_URL", config["facilitator_url"])
    
    @classmethod
    def is_testnet(cls, network: Network) -> bool:
        """Check if network is a testnet"""
        
        config = cls.CONFIGS.get(network)
        return config.get("is_testnet", False) if config else False


class SmartNetworkSelector:
    """Intelligently select and manage network configuration"""
    
    def __init__(self):
        self.current_network = None
        self.network_config = None
        self._detect_and_configure()
    
    def _detect_and_configure(self):
        """Detect network and configure accordingly"""
        
        self.current_network, self.network_config = NetworkConfig.detect_network()
        
        # Log the detection
        print(f"🌐 Detected network: {self.network_config['name']}")
        
        if self.network_config["is_testnet"]:
            print("   ⚠️  Running on testnet - payments are simulated")
        else:
            print("   💰 Running on mainnet - real payments enabled")
    
    def get_chain_id(self) -> int:
        """Get current chain ID"""
        return self.network_config["chain_id"]
    
    def get_facilitator_url(self) -> str:
        """Get facilitator URL"""
        return NetworkConfig.get_facilitator_url(self.current_network)
    
    def get_token_address(self, symbol: str = "USDC") -> str:
        """Get token address for current network"""
        
        token_config = NetworkConfig.get_token_config(self.current_network, symbol)
        if not token_config:
            raise ValueError(f"Token {symbol} not configured for {self.current_network}")
        
        return token_config["address"]
    
    def get_token_config(self, symbol: str = "USDC") -> Dict[str, Any]:
        """Get full token configuration"""
        
        return NetworkConfig.get_token_config(self.current_network, symbol)
    
    def switch_network(self, network: Network):
        """Switch to a different network"""
        
        if network not in NetworkConfig.CONFIGS:
            raise ValueError(f"Unknown network: {network}")
        
        self.current_network = network
        self.network_config = NetworkConfig.CONFIGS[network]
        
        print(f"🔄 Switched to network: {self.network_config['name']}")
    
    def get_explorer_url(self, address: str) -> str:
        """Get block explorer URL for an address"""
        
        base_url = self.network_config["explorer"]
        return f"{base_url}/address/{address}"
    
    def get_faucet_urls(self) -> list[str]:
        """Get testnet faucet URLs"""
        
        if not self.network_config["is_testnet"]:
            return []
        
        return self.network_config.get("faucets", [])
    
    def to_config_dict(self) -> Dict[str, Any]:
        """Convert to configuration dictionary"""
        
        return {
            "network": self.current_network.value,
            "chain_id": self.network_config["chain_id"],
            "facilitator_url": self.get_facilitator_url(),
            "is_testnet": self.network_config["is_testnet"],
            "tokens": self.network_config["tokens"],
        }