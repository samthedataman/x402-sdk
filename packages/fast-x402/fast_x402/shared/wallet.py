"""Wallet creation and management utilities for x402 SDKs"""

import os
import json
from typing import Dict, Optional, Tuple
from pathlib import Path

from eth_account import Account
from mnemonic import Mnemonic


class WalletManager:
    """Manages wallet creation and storage for x402 payments"""
    
    def __init__(self, wallet_dir: Optional[str] = None):
        self.wallet_dir = Path(wallet_dir or os.path.expanduser("~/.x402/wallets"))
        self.wallet_dir.mkdir(parents=True, exist_ok=True)
        
    def create_wallet(self, name: str = "default") -> Dict[str, str]:
        """Create a new wallet with mnemonic phrase"""
        
        # Generate mnemonic
        mnemo = Mnemonic("english")
        mnemonic = mnemo.generate(strength=128)
        
        # Create account from mnemonic
        Account.enable_unaudited_hdwallet_features()
        account = Account.from_mnemonic(mnemonic)
        
        wallet_data = {
            "name": name,
            "address": account.address,
            "private_key": account.key.hex(),
            "mnemonic": mnemonic,
        }
        
        # Save wallet (encrypted in production)
        wallet_path = self.wallet_dir / f"{name}.json"
        if wallet_path.exists():
            raise ValueError(f"Wallet '{name}' already exists")
            
        with open(wallet_path, 'w') as f:
            json.dump(wallet_data, f, indent=2)
        
        print(f"🔐 Created new wallet: {name}")
        print(f"   Address: {wallet_data['address']}")
        print(f"   Saved to: {wallet_path}")
        
        return wallet_data
    
    def load_wallet(self, name: str = "default") -> Dict[str, str]:
        """Load an existing wallet"""
        
        wallet_path = self.wallet_dir / f"{name}.json"
        if not wallet_path.exists():
            raise ValueError(f"Wallet '{name}' not found")
        
        with open(wallet_path, 'r') as f:
            wallet_data = json.load(f)
        
        return wallet_data
    
    def list_wallets(self) -> list[str]:
        """List all available wallets"""
        
        wallets = []
        for wallet_file in self.wallet_dir.glob("*.json"):
            wallets.append(wallet_file.stem)
        
        return wallets
    
    def export_wallet(self, name: str = "default", include_private_key: bool = False) -> Dict[str, str]:
        """Export wallet data (optionally without private key)"""
        
        wallet_data = self.load_wallet(name)
        
        export_data = {
            "name": wallet_data["name"],
            "address": wallet_data["address"],
        }
        
        if include_private_key:
            export_data["private_key"] = wallet_data["private_key"]
            export_data["mnemonic"] = wallet_data["mnemonic"]
        
        return export_data
    
    def create_or_load_wallet(self, name: str = "default") -> Tuple[Dict[str, str], bool]:
        """Create a new wallet or load existing one"""
        
        try:
            wallet = self.load_wallet(name)
            return wallet, False  # loaded existing
        except ValueError:
            wallet = self.create_wallet(name)
            return wallet, True  # created new


def generate_wallet() -> Dict[str, str]:
    """Quick function to generate a new wallet without saving"""
    
    # Generate mnemonic
    mnemo = Mnemonic("english")
    mnemonic = mnemo.generate(strength=128)
    
    # Create account
    Account.enable_unaudited_hdwallet_features()
    account = Account.from_mnemonic(mnemonic)
    
    return {
        "address": account.address,
        "private_key": account.key.hex(),
        "mnemonic": mnemonic,
    }