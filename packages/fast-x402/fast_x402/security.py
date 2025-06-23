"""Security utilities for fast-x402"""

import re
import secrets
from typing import Optional, List
from web3 import Web3
from eth_utils import is_address

from .logger import logger
from .exceptions import X402Error


def validate_address(address: str) -> bool:
    """Validate Ethereum address"""
    if not address:
        return False
    
    if not is_address(address):
        logger.warning(f"Invalid Ethereum address format: {address[:10]}...")
        return False
    
    return True


def validate_amount(amount: str, max_amount: Optional[str] = None) -> bool:
    """Validate payment amount"""
    try:
        amount_float = float(amount)
        
        if amount_float < 0:
            logger.error(f"Negative amount not allowed: {amount}")
            return False
        
        if amount_float > 1000000:  # $1M sanity check
            logger.error(f"Amount exceeds maximum allowed: {amount}")
            return False
        
        if max_amount:
            max_float = float(max_amount)
            if amount_float > max_float:
                logger.warning(f"Amount {amount} exceeds maximum {max_amount}")
                return False
        
        return True
        
    except (ValueError, TypeError) as e:
        logger.error(f"Invalid amount format: {amount} - {e}")
        return False


def sanitize_nonce(nonce: str) -> str:
    """Sanitize nonce to prevent injection"""
    # Remove any non-hex characters
    sanitized = re.sub(r'[^0-9a-fA-Fx]', '', nonce)
    
    # Ensure it starts with 0x
    if not sanitized.startswith('0x'):
        sanitized = '0x' + sanitized.replace('0x', '')
    
    # Limit length to prevent DOS
    if len(sanitized) > 66:  # 0x + 64 hex chars
        sanitized = sanitized[:66]
    
    return sanitized


def validate_chain_id(chain_id: int, allowed_chains: Optional[List[int]] = None) -> bool:
    """Validate blockchain chain ID"""
    # Default allowed chains
    if allowed_chains is None:
        allowed_chains = [
            1,      # Ethereum mainnet
            8453,   # Base mainnet
            137,    # Polygon mainnet
            42161,  # Arbitrum One
            10,     # Optimism
        ]
    
    if chain_id not in allowed_chains:
        logger.warning(f"Chain ID {chain_id} not in allowed list: {allowed_chains}")
        return False
    
    return True


def validate_url(url: str, allowed_domains: Optional[List[str]] = None) -> bool:
    """Validate URL and check against allowed domains"""
    from urllib.parse import urlparse
    
    try:
        parsed = urlparse(url)
        
        # Must have scheme and netloc
        if not parsed.scheme or not parsed.netloc:
            logger.error(f"Invalid URL format: {url}")
            return False
        
        # Must be http or https
        if parsed.scheme not in ['http', 'https']:
            logger.error(f"Invalid URL scheme: {parsed.scheme}")
            return False
        
        # Check against allowed domains if provided
        if allowed_domains:
            domain = parsed.netloc.lower()
            # Remove port if present
            domain = domain.split(':')[0]
            
            # Check if domain matches any allowed pattern
            domain_allowed = False
            for allowed in allowed_domains:
                if allowed.startswith('*.'):
                    # Wildcard subdomain
                    if domain.endswith(allowed[2:]) or domain == allowed[2:]:
                        domain_allowed = True
                        break
                elif domain == allowed:
                    domain_allowed = True
                    break
            
            if not domain_allowed:
                logger.warning(f"Domain {domain} not in allowed list")
                return False
        
        return True
        
    except Exception as e:
        logger.error(f"URL validation error: {e}")
        return False


def generate_secure_nonce() -> str:
    """Generate cryptographically secure nonce"""
    return '0x' + secrets.token_hex(32)


def mask_sensitive_data(data: str, visible_chars: int = 6) -> str:
    """Mask sensitive data for logging"""
    if not data or len(data) <= visible_chars * 2:
        return data
    
    return f"{data[:visible_chars]}...{data[-visible_chars:]}"


class RateLimiter:
    """Simple in-memory rate limiter"""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: dict = {}
        
    def is_allowed(self, key: str) -> bool:
        """Check if request is allowed"""
        import time
        
        now = time.time()
        
        # Clean old entries
        self.requests = {
            k: v for k, v in self.requests.items() 
            if now - v['first_request'] < self.window_seconds
        }
        
        if key not in self.requests:
            self.requests[key] = {
                'count': 1,
                'first_request': now
            }
            return True
        
        entry = self.requests[key]
        if now - entry['first_request'] >= self.window_seconds:
            # Reset window
            entry['count'] = 1
            entry['first_request'] = now
            return True
        
        if entry['count'] >= self.max_requests:
            logger.warning(f"Rate limit exceeded for {mask_sensitive_data(key)}")
            return False
        
        entry['count'] += 1
        return True