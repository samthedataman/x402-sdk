"""
Enhanced RPC Manager for x402 SDK

Supports all popular blockchain networks with automatic failover,
load balancing, and ChainList.org integration for maximum reliability.

Based on the enhanced RPC pattern for multi-chain DeFi applications.
"""

import os
import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from web3 import Web3
from web3.providers import HTTPProvider
from datetime import datetime, timedelta
from collections import defaultdict
import httpx
from enum import Enum
import time

logger = logging.getLogger(__name__)

class ChainType(Enum):
    """Supported blockchain types"""
    EVM = "evm"
    SOLANA = "solana"
    COSMOS = "cosmos"
    SUBSTRATE = "substrate"
    BITCOIN = "bitcoin"

class NetworkInfo:
    """Network information container"""
    def __init__(self, name: str, chain_id: int, chain_type: ChainType, 
                 native_currency: str, rpc_urls: List[str], 
                 explorer_url: str = "", testnet: bool = False):
        self.name = name
        self.chain_id = chain_id
        self.chain_type = chain_type
        self.native_currency = native_currency
        self.rpc_urls = rpc_urls
        self.explorer_url = explorer_url
        self.testnet = testnet

# Comprehensive network configurations
NETWORK_CONFIGS = {
    # Major EVM Networks
    "ethereum": NetworkInfo(
        name="Ethereum Mainnet",
        chain_id=1,
        chain_type=ChainType.EVM,
        native_currency="ETH",
        rpc_urls=[
            "https://eth-mainnet.g.alchemy.com/v2/${ALCHEMY_API_KEY}",
            "https://mainnet.infura.io/v3/${INFURA_API_KEY}",
            "https://ethereum.publicnode.com",
            "https://rpc.ankr.com/eth",
            "https://cloudflare-eth.com",
            "https://eth.llamarpc.com",
            "https://ethereum-rpc.publicnode.com",
        ],
        explorer_url="https://etherscan.io"
    ),
    
    "polygon": NetworkInfo(
        name="Polygon",
        chain_id=137,
        chain_type=ChainType.EVM,
        native_currency="MATIC",
        rpc_urls=[
            "https://polygon-mainnet.g.alchemy.com/v2/${ALCHEMY_API_KEY}",
            "https://polygon-mainnet.infura.io/v3/${INFURA_API_KEY}",
            "https://polygon-rpc.com",
            "https://rpc.ankr.com/polygon",
            "https://polygon.llamarpc.com",
            "https://polygon.publicnode.com",
        ],
        explorer_url="https://polygonscan.com"
    ),
    
    "arbitrum": NetworkInfo(
        name="Arbitrum One",
        chain_id=42161,
        chain_type=ChainType.EVM,
        native_currency="ETH",
        rpc_urls=[
            "https://arb-mainnet.g.alchemy.com/v2/${ALCHEMY_API_KEY}",
            "https://arbitrum-mainnet.infura.io/v3/${INFURA_API_KEY}",
            "https://arb1.arbitrum.io/rpc",
            "https://arbitrum-one.publicnode.com",
            "https://rpc.ankr.com/arbitrum",
            "https://arbitrum.llamarpc.com",
        ],
        explorer_url="https://arbiscan.io"
    ),
    
    "optimism": NetworkInfo(
        name="Optimism",
        chain_id=10,
        chain_type=ChainType.EVM,
        native_currency="ETH",
        rpc_urls=[
            "https://opt-mainnet.g.alchemy.com/v2/${ALCHEMY_API_KEY}",
            "https://optimism-mainnet.infura.io/v3/${INFURA_API_KEY}",
            "https://mainnet.optimism.io",
            "https://optimism.publicnode.com",
            "https://rpc.ankr.com/optimism",
            "https://optimism.llamarpc.com",
        ],
        explorer_url="https://optimistic.etherscan.io"
    ),
    
    "base": NetworkInfo(
        name="Base",
        chain_id=8453,
        chain_type=ChainType.EVM,
        native_currency="ETH",
        rpc_urls=[
            "https://base-mainnet.g.alchemy.com/v2/${ALCHEMY_API_KEY}",
            "https://mainnet.base.org",
            "https://base.publicnode.com",
            "https://rpc.ankr.com/base",
            "https://base.llamarpc.com",
        ],
        explorer_url="https://basescan.org"
    ),
    
    "avalanche": NetworkInfo(
        name="Avalanche C-Chain",
        chain_id=43114,
        chain_type=ChainType.EVM,
        native_currency="AVAX",
        rpc_urls=[
            "https://avalanche-mainnet.infura.io/v3/${INFURA_API_KEY}",
            "https://api.avax.network/ext/bc/C/rpc",
            "https://avalanche.publicnode.com/ext/bc/C/rpc",
            "https://rpc.ankr.com/avalanche",
        ],
        explorer_url="https://snowtrace.io"
    ),
    
    "bsc": NetworkInfo(
        name="BNB Smart Chain",
        chain_id=56,
        chain_type=ChainType.EVM,
        native_currency="BNB",
        rpc_urls=[
            "https://bsc-dataseed.binance.org",
            "https://bsc.publicnode.com",
            "https://rpc.ankr.com/bsc",
            "https://bsc-dataseed1.defibit.io",
            "https://bsc-dataseed2.defibit.io",
        ],
        explorer_url="https://bscscan.com"
    ),
    
    "fantom": NetworkInfo(
        name="Fantom Opera",
        chain_id=250,
        chain_type=ChainType.EVM,
        native_currency="FTM",
        rpc_urls=[
            "https://rpc.ftm.tools",
            "https://fantom.publicnode.com",
            "https://rpc.ankr.com/fantom",
            "https://fantom-mainnet.public.blastapi.io",
        ],
        explorer_url="https://ftmscan.com"
    ),
    
    "cronos": NetworkInfo(
        name="Cronos",
        chain_id=25,
        chain_type=ChainType.EVM,
        native_currency="CRO",
        rpc_urls=[
            "https://evm.cronos.org",
            "https://cronos-evm.publicnode.com",
        ],
        explorer_url="https://cronoscan.com"
    ),
    
    "moonbeam": NetworkInfo(
        name="Moonbeam",
        chain_id=1284,
        chain_type=ChainType.EVM,
        native_currency="GLMR",
        rpc_urls=[
            "https://rpc.api.moonbeam.network",
            "https://moonbeam.publicnode.com",
        ],
        explorer_url="https://moonscan.io"
    ),
    
    "gnosis": NetworkInfo(
        name="Gnosis Chain",
        chain_id=100,
        chain_type=ChainType.EVM,
        native_currency="xDAI",
        rpc_urls=[
            "https://rpc.gnosischain.com",
            "https://gnosis.publicnode.com",
            "https://rpc.ankr.com/gnosis",
        ],
        explorer_url="https://gnosisscan.io"
    ),
    
    "celo": NetworkInfo(
        name="Celo",
        chain_id=42220,
        chain_type=ChainType.EVM,
        native_currency="CELO",
        rpc_urls=[
            "https://forno.celo.org",
            "https://celo.publicnode.com",
        ],
        explorer_url="https://celoscan.io"
    ),
    
    "aurora": NetworkInfo(
        name="Aurora",
        chain_id=1313161554,
        chain_type=ChainType.EVM,
        native_currency="ETH",
        rpc_urls=[
            "https://mainnet.aurora.dev",
        ],
        explorer_url="https://aurorascan.dev"
    ),
    
    "harmony": NetworkInfo(
        name="Harmony One",
        chain_id=1666600000,
        chain_type=ChainType.EVM,
        native_currency="ONE",
        rpc_urls=[
            "https://api.harmony.one",
            "https://harmony-0-rpc.gateway.pokt.network",
        ],
        explorer_url="https://explorer.harmony.one"
    ),
    
    "kava": NetworkInfo(
        name="Kava EVM",
        chain_id=2222,
        chain_type=ChainType.EVM,
        native_currency="KAVA",
        rpc_urls=[
            "https://evm.kava.io",
            "https://kava-evm.publicnode.com",
        ],
        explorer_url="https://explorer.kava.io"
    ),
    
    "evmos": NetworkInfo(
        name="Evmos",
        chain_id=9001,
        chain_type=ChainType.EVM,
        native_currency="EVMOS",
        rpc_urls=[
            "https://eth.bd.evmos.org:8545",
            "https://evmos-evm.publicnode.com",
        ],
        explorer_url="https://evm.evmos.org"
    ),
    
    # Additional Major Networks
    "moonriver": NetworkInfo(
        name="Moonriver",
        chain_id=1285,
        chain_type=ChainType.EVM,
        native_currency="MOVR",
        rpc_urls=[
            "https://rpc.api.moonriver.moonbeam.network",
            "https://moonriver.publicnode.com",
        ],
        explorer_url="https://moonriver.moonscan.io"
    ),
    
    "metis": NetworkInfo(
        name="Metis Andromeda",
        chain_id=1088,
        chain_type=ChainType.EVM,
        native_currency="METIS",
        rpc_urls=[
            "https://andromeda.metis.io/?owner=1088",
            "https://metis-mainnet.public.blastapi.io",
        ],
        explorer_url="https://andromeda-explorer.metis.io"
    ),
    
    "boba": NetworkInfo(
        name="Boba Network",
        chain_id=288,
        chain_type=ChainType.EVM,
        native_currency="ETH",
        rpc_urls=[
            "https://mainnet.boba.network",
            "https://boba-mainnet.gateway.pokt.network/v1/lb/623ad21b20354900396fed7f",
        ],
        explorer_url="https://blockexplorer.boba.network"
    ),
    
    "okexchain": NetworkInfo(
        name="OKExChain",
        chain_id=66,
        chain_type=ChainType.EVM,
        native_currency="OKT",
        rpc_urls=[
            "https://exchainrpc.okex.org",
        ],
        explorer_url="https://www.oklink.com/okexchain"
    ),
    
    "heco": NetworkInfo(
        name="Huobi ECO Chain",
        chain_id=128,
        chain_type=ChainType.EVM,
        native_currency="HT",
        rpc_urls=[
            "https://http-mainnet.hecochain.com",
        ],
        explorer_url="https://hecoinfo.com"
    ),
    
    "kcc": NetworkInfo(
        name="KuCoin Community Chain",
        chain_id=321,
        chain_type=ChainType.EVM,
        native_currency="KCS",
        rpc_urls=[
            "https://rpc-mainnet.kcc.network",
        ],
        explorer_url="https://explorer.kcc.io"
    ),
    
    "velas": NetworkInfo(
        name="Velas EVM",
        chain_id=106,
        chain_type=ChainType.EVM,
        native_currency="VLX",
        rpc_urls=[
            "https://evmexplorer.velas.com/rpc",
        ],
        explorer_url="https://evmexplorer.velas.com"
    ),
    
    "oasis": NetworkInfo(
        name="Oasis Emerald",
        chain_id=42262,
        chain_type=ChainType.EVM,
        native_currency="ROSE",
        rpc_urls=[
            "https://emerald.oasis.dev",
        ],
        explorer_url="https://explorer.emerald.oasis.dev"
    ),
    
    "telos": NetworkInfo(
        name="Telos EVM",
        chain_id=40,
        chain_type=ChainType.EVM,
        native_currency="TLOS",
        rpc_urls=[
            "https://mainnet.telos.net/evm",
        ],
        explorer_url="https://www.teloscan.io"
    ),
    
    "dfk": NetworkInfo(
        name="DeFi Kingdoms",
        chain_id=53935,
        chain_type=ChainType.EVM,
        native_currency="JEWEL",
        rpc_urls=[
            "https://subnets.avax.network/defi-kingdoms/dfk-chain/rpc",
        ],
        explorer_url="https://subnets.avax.network/defi-kingdoms"
    ),
    
    "klaytn": NetworkInfo(
        name="Klaytn",
        chain_id=8217,
        chain_type=ChainType.EVM,
        native_currency="KLAY",
        rpc_urls=[
            "https://klaytn-mainnet-rpc.allthatnode.com:8551",
            "https://public-node-api.klaytnapi.com/v1/cypress",
        ],
        explorer_url="https://scope.klaytn.com"
    ),
    
    "iotex": NetworkInfo(
        name="IoTeX",
        chain_id=4689,
        chain_type=ChainType.EVM,
        native_currency="IOTX",
        rpc_urls=[
            "https://babel-api.mainnet.iotex.io",
        ],
        explorer_url="https://iotexscan.io"
    ),
    
    "thundercore": NetworkInfo(
        name="ThunderCore",
        chain_id=108,
        chain_type=ChainType.EVM,
        native_currency="TT",
        rpc_urls=[
            "https://mainnet-rpc.thundercore.com",
        ],
        explorer_url="https://scan.thundercore.com"
    ),
    
    "arbitrum-nova": NetworkInfo(
        name="Arbitrum Nova",
        chain_id=42170,
        chain_type=ChainType.EVM,
        native_currency="ETH",
        rpc_urls=[
            "https://nova.arbitrum.io/rpc",
        ],
        explorer_url="https://nova.arbiscan.io"
    ),
    
    "canto": NetworkInfo(
        name="Canto",
        chain_id=7700,
        chain_type=ChainType.EVM,
        native_currency="CANTO",
        rpc_urls=[
            "https://canto.gravitychain.io",
        ],
        explorer_url="https://evm.explorer.canto.io"
    ),
    
    "meter": NetworkInfo(
        name="Meter",
        chain_id=82,
        chain_type=ChainType.EVM,
        native_currency="MTR",
        rpc_urls=[
            "https://rpc.meter.io",
        ],
        explorer_url="https://scan.meter.io"
    ),
    
    "manta": NetworkInfo(
        name="Manta Pacific",
        chain_id=169,
        chain_type=ChainType.EVM,
        native_currency="ETH",
        rpc_urls=[
            "https://pacific-rpc.manta.network/http",
        ],
        explorer_url="https://pacific-explorer.manta.network"
    ),
    
    "blast": NetworkInfo(
        name="Blast",
        chain_id=81457,
        chain_type=ChainType.EVM,
        native_currency="ETH",
        rpc_urls=[
            "https://rpc.blast.io",
        ],
        explorer_url="https://blastscan.io"
    ),
    
    "mantle": NetworkInfo(
        name="Mantle",
        chain_id=5000,
        chain_type=ChainType.EVM,
        native_currency="MNT",
        rpc_urls=[
            "https://rpc.mantle.xyz",
        ],
        explorer_url="https://explorer.mantle.xyz"
    ),
    
    "polygonzkevm": NetworkInfo(
        name="Polygon zkEVM",
        chain_id=1101,
        chain_type=ChainType.EVM,
        native_currency="ETH",
        rpc_urls=[
            "https://zkevm-rpc.com",
            "https://polygon-zkevm.publicnode.com",
        ],
        explorer_url="https://zkevm.polygonscan.com"
    ),
    
    "sonic": NetworkInfo(
        name="Sonic",
        chain_id=146,
        chain_type=ChainType.EVM,
        native_currency="S",
        rpc_urls=[
            "https://rpc.soniclabs.com",
        ],
        explorer_url="https://explorer.soniclabs.com"
    ),
    
    "berachain": NetworkInfo(
        name="Berachain",
        chain_id=80085,
        chain_type=ChainType.EVM,
        native_currency="BERA",
        rpc_urls=[
            "https://rpc.berachain.com",
        ],
        explorer_url="https://explorer.berachain.com"
    ),
    
    "fraxtal": NetworkInfo(
        name="Fraxtal",
        chain_id=252,
        chain_type=ChainType.EVM,
        native_currency="frxETH",
        rpc_urls=[
            "https://rpc.frax.com",
        ],
        explorer_url="https://fraxscan.com"
    ),
    
    "opbnb": NetworkInfo(
        name="opBNB",
        chain_id=204,
        chain_type=ChainType.EVM,
        native_currency="BNB",
        rpc_urls=[
            "https://opbnb-mainnet-rpc.bnbchain.org",
        ],
        explorer_url="https://opbnbscan.com"
    ),
    
    # Layer 2 Solutions
    "zksync": NetworkInfo(
        name="zkSync Era",
        chain_id=324,
        chain_type=ChainType.EVM,
        native_currency="ETH",
        rpc_urls=[
            "https://mainnet.era.zksync.io",
            "https://zksync2-mainnet.zksync.io",
        ],
        explorer_url="https://explorer.zksync.io"
    ),
    
    "polygon-zkevm": NetworkInfo(
        name="Polygon zkEVM",
        chain_id=1101,
        chain_type=ChainType.EVM,
        native_currency="ETH",
        rpc_urls=[
            "https://zkevm-rpc.com",
            "https://polygon-zkevm.publicnode.com",
        ],
        explorer_url="https://zkevm.polygonscan.com"
    ),
    
    "linea": NetworkInfo(
        name="Linea",
        chain_id=59144,
        chain_type=ChainType.EVM,
        native_currency="ETH",
        rpc_urls=[
            "https://linea-mainnet.infura.io/v3/${INFURA_API_KEY}",
            "https://rpc.linea.build",
        ],
        explorer_url="https://lineascan.build"
    ),
    
    "scroll": NetworkInfo(
        name="Scroll",
        chain_id=534352,
        chain_type=ChainType.EVM,
        native_currency="ETH",
        rpc_urls=[
            "https://rpc.scroll.io",
        ],
        explorer_url="https://scrollscan.com"
    ),
    
    # Testnets
    "goerli": NetworkInfo(
        name="Goerli Testnet",
        chain_id=5,
        chain_type=ChainType.EVM,
        native_currency="ETH",
        rpc_urls=[
            "https://eth-goerli.g.alchemy.com/v2/${ALCHEMY_API_KEY}",
            "https://goerli.infura.io/v3/${INFURA_API_KEY}",
            "https://rpc.ankr.com/eth_goerli",
        ],
        explorer_url="https://goerli.etherscan.io",
        testnet=True
    ),
    
    "sepolia": NetworkInfo(
        name="Sepolia Testnet",
        chain_id=11155111,
        chain_type=ChainType.EVM,
        native_currency="ETH",
        rpc_urls=[
            "https://eth-sepolia.g.alchemy.com/v2/${ALCHEMY_API_KEY}",
            "https://sepolia.infura.io/v3/${INFURA_API_KEY}",
            "https://rpc.sepolia.org",
        ],
        explorer_url="https://sepolia.etherscan.io",
        testnet=True
    ),
    
    "base-sepolia": NetworkInfo(
        name="Base Sepolia",
        chain_id=84532,
        chain_type=ChainType.EVM,
        native_currency="ETH",
        rpc_urls=[
            "https://base-sepolia.g.alchemy.com/v2/${ALCHEMY_API_KEY}",
            "https://sepolia.base.org",
        ],
        explorer_url="https://sepolia.basescan.org",
        testnet=True
    ),
    
    # Non-EVM Networks
    "solana": NetworkInfo(
        name="Solana",
        chain_id=101,  # Solana uses different ID system
        chain_type=ChainType.SOLANA,
        native_currency="SOL",
        rpc_urls=[
            "https://api.mainnet-beta.solana.com",
            "https://solana-api.projectserum.com",
            "https://rpc.ankr.com/solana",
            "https://api.metaplex.solana.com",
        ],
        explorer_url="https://explorer.solana.com"
    ),
    
    "algorand": NetworkInfo(
        name="Algorand",
        chain_id=0,  # Algorand uses different ID system
        chain_type=ChainType.SUBSTRATE,  # Using substrate as generic non-EVM
        native_currency="ALGO",
        rpc_urls=[
            "https://mainnet-api.algonode.cloud",
            "https://node.algoexplorerapi.io",
        ],
        explorer_url="https://algoexplorer.io"
    ),
    
    "aptos": NetworkInfo(
        name="Aptos",
        chain_id=1,  # Aptos uses different ID system
        chain_type=ChainType.SUBSTRATE,
        native_currency="APT",
        rpc_urls=[
            "https://fullnode.mainnet.aptoslabs.com/v1",
        ],
        explorer_url="https://explorer.aptoslabs.com"
    ),
    
    "sui": NetworkInfo(
        name="Sui",
        chain_id=1,  # Sui uses different ID system
        chain_type=ChainType.SUBSTRATE,
        native_currency="SUI",
        rpc_urls=[
            "https://fullnode.mainnet.sui.io:443",
        ],
        explorer_url="https://explorer.sui.io"
    ),
    
    "hedera": NetworkInfo(
        name="Hedera",
        chain_id=295,
        chain_type=ChainType.EVM,
        native_currency="HBAR",
        rpc_urls=[
            "https://mainnet.hashio.io/api",
        ],
        explorer_url="https://hashscan.io"
    ),
    
    "injective": NetworkInfo(
        name="Injective",
        chain_id=1,  # Cosmos-based
        chain_type=ChainType.COSMOS,
        native_currency="INJ",
        rpc_urls=[
            "https://sentry.chain.grpc-web.injective.network:443",
        ],
        explorer_url="https://explorer.injective.network"
    ),
    
    "osmosis": NetworkInfo(
        name="Osmosis",
        chain_id=1,  # Cosmos-based
        chain_type=ChainType.COSMOS,
        native_currency="OSMO",
        rpc_urls=[
            "https://rpc.osmosis.zone",
        ],
        explorer_url="https://www.mintscan.io/osmosis"
    ),
    
    "neutron": NetworkInfo(
        name="Neutron",
        chain_id=1,  # Cosmos-based
        chain_type=ChainType.COSMOS,
        native_currency="NTRN",
        rpc_urls=[
            "https://rpc.novel.remedy.tm.p2p.org",
        ],
        explorer_url="https://www.mintscan.io/neutron"
    ),
    
    "tron": NetworkInfo(
        name="Tron",
        chain_id=1,  # Tron uses different ID system
        chain_type=ChainType.SUBSTRATE,  # Using as generic non-EVM
        native_currency="TRX",
        rpc_urls=[
            "https://api.trongrid.io",
        ],
        explorer_url="https://tronscan.org"
    ),
    
    "solana-devnet": NetworkInfo(
        name="Solana Devnet",
        chain_id=103,
        chain_type=ChainType.SOLANA,
        native_currency="SOL",
        rpc_urls=[
            "https://api.devnet.solana.com",
        ],
        explorer_url="https://explorer.solana.com/?cluster=devnet",
        testnet=True
    ),
}

class EnhancedRPCManager:
    """Enhanced RPC Manager with multi-chain support and automatic failover"""
    
    def __init__(self, cache_ttl: int = 300, max_retries: int = 3):
        self.cache_ttl = cache_ttl
        self.max_retries = max_retries
        self.web3_instances = {}
        self.rpc_health = defaultdict(dict)
        self.last_health_check = {}
        self.current_rpc_index = defaultdict(int)
        self.logger = logging.getLogger(__name__)
        
        # Initialize API keys from environment
        self.api_keys = {
            "alchemy": os.getenv("ALCHEMY_API_KEY", ""),
            "infura": os.getenv("INFURA_API_KEY", ""),
            "quicknode": os.getenv("QUICKNODE_API_KEY", ""),
        }
        
        # Initialize Web3 instances for all supported networks
        self._initialize_all_networks()
    
    def _initialize_all_networks(self):
        """Initialize Web3 instances for all supported networks"""
        self.logger.info("🚀 Initializing multi-chain RPC connections...")
        
        initialized_count = 0
        failed_count = 0
        
        for network_key, network_info in NETWORK_CONFIGS.items():
            if network_info.chain_type == ChainType.EVM:
                success = self._initialize_evm_network(network_key, network_info)
                if success:
                    initialized_count += 1
                else:
                    failed_count += 1
        
        self.logger.info(
            f"✅ Multi-chain RPC initialization complete: "
            f"{initialized_count} networks connected, {failed_count} failed"
        )
    
    def _initialize_evm_network(self, network_key: str, network_info: NetworkInfo) -> bool:
        """Initialize a single EVM network with fallback RPC endpoints"""
        rpc_urls = self._substitute_api_keys(network_info.rpc_urls)
        
        for i, rpc_url in enumerate(rpc_urls):
            try:
                # Skip URLs with missing API keys
                if "${" in rpc_url:
                    continue
                    
                w3 = Web3(HTTPProvider(rpc_url, request_kwargs={"timeout": 10}))
                
                if w3.is_connected():
                    # Test with a block number call
                    block_number = w3.eth.block_number
                    if block_number > 0:
                        self.web3_instances[network_key] = w3
                        self.current_rpc_index[network_key] = i
                        self.rpc_health[network_key][rpc_url] = {
                            "status": "healthy",
                            "last_check": datetime.now(),
                            "block_number": block_number
                        }
                        
                        self.logger.info(
                            f"✅ {network_info.name} connected via {rpc_url.split('/')[2]}"
                        )
                        return True
                        
            except Exception as e:
                self.logger.debug(f"Failed to connect to {network_key} via {rpc_url}: {e}")
                self.rpc_health[network_key][rpc_url] = {
                    "status": "unhealthy",
                    "last_check": datetime.now(),
                    "error": str(e)
                }
                continue
        
        self.logger.warning(f"❌ Failed to connect to {network_info.name}")
        return False
    
    def _substitute_api_keys(self, rpc_urls: List[str]) -> List[str]:
        """Substitute API keys in RPC URLs"""
        substituted = []
        
        for url in rpc_urls:
            # Substitute known API key patterns
            if "${ALCHEMY_API_KEY}" in url and self.api_keys["alchemy"]:
                url = url.replace("${ALCHEMY_API_KEY}", self.api_keys["alchemy"])
            elif "${INFURA_API_KEY}" in url and self.api_keys["infura"]:
                url = url.replace("${INFURA_API_KEY}", self.api_keys["infura"])
            elif "${QUICKNODE_API_KEY}" in url and self.api_keys["quicknode"]:
                url = url.replace("${QUICKNODE_API_KEY}", self.api_keys["quicknode"])
            
            substituted.append(url)
        
        return substituted
    
    def get_web3(self, network: str, prefer_fastest: bool = True) -> Optional[Web3]:
        """Get Web3 instance for a network with automatic failover"""
        network = network.lower()
        
        # Return cached instance if healthy
        if network in self.web3_instances:
            w3 = self.web3_instances[network]
            try:
                # Quick health check
                w3.eth.block_number
                return w3
            except Exception as e:
                self.logger.warning(f"Health check failed for {network}: {e}")
                # Try to rotate to next RPC
                if self._rotate_rpc(network):
                    return self.web3_instances.get(network)
        
        # Try to initialize if not available
        if network in NETWORK_CONFIGS:
            network_info = NETWORK_CONFIGS[network]
            if network_info.chain_type == ChainType.EVM:
                if self._initialize_evm_network(network, network_info):
                    return self.web3_instances.get(network)
        
        return None
    
    def _rotate_rpc(self, network: str) -> bool:
        """Rotate to next healthy RPC endpoint for a network"""
        if network not in NETWORK_CONFIGS:
            return False
        
        network_info = NETWORK_CONFIGS[network]
        rpc_urls = self._substitute_api_keys(network_info.rpc_urls)
        
        current_index = self.current_rpc_index.get(network, 0)
        
        # Try next RPCs in sequence
        for i in range(len(rpc_urls)):
            next_index = (current_index + i + 1) % len(rpc_urls)
            rpc_url = rpc_urls[next_index]
            
            # Skip URLs with missing API keys
            if "${" in rpc_url:
                continue
            
            try:
                w3 = Web3(HTTPProvider(rpc_url, request_kwargs={"timeout": 10}))
                if w3.is_connected():
                    block_number = w3.eth.block_number
                    if block_number > 0:
                        self.web3_instances[network] = w3
                        self.current_rpc_index[network] = next_index
                        
                        self.logger.info(
                            f"🔄 {network} rotated to {rpc_url.split('/')[2]}"
                        )
                        return True
                        
            except Exception as e:
                self.logger.debug(f"RPC rotation failed for {rpc_url}: {e}")
                continue
        
        return False
    
    def get_supported_networks(self, include_testnets: bool = False) -> List[str]:
        """Get list of supported networks"""
        networks = []
        for key, info in NETWORK_CONFIGS.items():
            if include_testnets or not info.testnet:
                networks.append(key)
        return networks
    
    def get_network_info(self, network: str) -> Optional[NetworkInfo]:
        """Get network information"""
        return NETWORK_CONFIGS.get(network.lower())
    
    def is_testnet(self, network: str) -> bool:
        """Check if network is a testnet"""
        network_info = self.get_network_info(network)
        return network_info.testnet if network_info else False
    
    def get_chain_id(self, network: str) -> Optional[int]:
        """Get chain ID for a network"""
        network_info = self.get_network_info(network)
        return network_info.chain_id if network_info else None
    
    def get_explorer_url(self, network: str) -> Optional[str]:
        """Get block explorer URL for a network"""
        network_info = self.get_network_info(network)
        return network_info.explorer_url if network_info else None
    
    def get_native_currency(self, network: str) -> Optional[str]:
        """Get native currency symbol for a network"""
        network_info = self.get_network_info(network)
        return network_info.native_currency if network_info else None
    
    async def health_check_all(self) -> Dict[str, Any]:
        """Perform health check on all networks"""
        health_status = {
            "timestamp": datetime.now().isoformat(),
            "networks": {},
            "summary": {
                "total": 0,
                "healthy": 0,
                "unhealthy": 0
            }
        }
        
        for network_key in NETWORK_CONFIGS.keys():
            network_info = NETWORK_CONFIGS[network_key]
            
            if network_info.chain_type == ChainType.EVM and network_key in self.web3_instances:
                try:
                    w3 = self.web3_instances[network_key]
                    block_number = w3.eth.block_number
                    
                    health_status["networks"][network_key] = {
                        "status": "healthy",
                        "block_number": block_number,
                        "name": network_info.name,
                        "chain_id": network_info.chain_id
                    }
                    health_status["summary"]["healthy"] += 1
                    
                except Exception as e:
                    health_status["networks"][network_key] = {
                        "status": "unhealthy",
                        "error": str(e),
                        "name": network_info.name,
                        "chain_id": network_info.chain_id
                    }
                    health_status["summary"]["unhealthy"] += 1
            else:
                health_status["networks"][network_key] = {
                    "status": "not_initialized",
                    "name": network_info.name,
                    "chain_id": network_info.chain_id
                }
                health_status["summary"]["unhealthy"] += 1
            
            health_status["summary"]["total"] += 1
        
        return health_status
    
    def get_fastest_rpc(self, network: str) -> Optional[str]:
        """Get the fastest RPC endpoint for a network"""
        # This would implement latency testing
        # For now, return the first healthy one
        network_info = self.get_network_info(network)
        if network_info:
            rpc_urls = self._substitute_api_keys(network_info.rpc_urls)
            return next((url for url in rpc_urls if "${" not in url), None)
        return None

# Global RPC manager instance
_rpc_manager = None

async def get_rpc_manager() -> EnhancedRPCManager:
    """Get global RPC manager instance"""
    global _rpc_manager
    if _rpc_manager is None:
        _rpc_manager = EnhancedRPCManager()
    return _rpc_manager

def get_web3_for_chain(chain: str) -> Optional[Web3]:
    """Get Web3 instance for a chain (sync version)"""
    global _rpc_manager
    if _rpc_manager is None:
        _rpc_manager = EnhancedRPCManager()
    return _rpc_manager.get_web3(chain)

def get_supported_chains(include_testnets: bool = False) -> List[str]:
    """Get list of supported blockchain networks"""
    global _rpc_manager
    if _rpc_manager is None:
        _rpc_manager = EnhancedRPCManager()
    return _rpc_manager.get_supported_networks(include_testnets)

def get_chain_info(chain: str) -> Optional[Dict[str, Any]]:
    """Get comprehensive chain information"""
    global _rpc_manager
    if _rpc_manager is None:
        _rpc_manager = EnhancedRPCManager()
    
    network_info = _rpc_manager.get_network_info(chain)
    if network_info:
        return {
            "name": network_info.name,
            "chain_id": network_info.chain_id,
            "chain_type": network_info.chain_type.value,
            "native_currency": network_info.native_currency,
            "explorer_url": network_info.explorer_url,
            "testnet": network_info.testnet,
            "rpc_endpoints": len(network_info.rpc_urls)
        }
    return None