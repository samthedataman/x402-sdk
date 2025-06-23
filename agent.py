"""
x402-agent - AI Agent Payment SDK
pip install x402-agent
"""

import json
import time
import asyncio
import logging
from typing import Dict, Any, Optional, List, Union, Callable, Tuple
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
import os

import requests
import aiohttp
from eth_account import Account
from eth_account.messages import encode_structured_data
from web3 import Web3

# LangChain support
try:
    from langchain.tools import BaseTool
    from langchain.callbacks.manager import CallbackManagerForToolRun
    from langchain.agents import AgentExecutor
    from pydantic import BaseModel, Field

    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    BaseTool = object
    BaseModel = object

__version__ = "1.0.0"
__all__ = [
    "X402Agent",
    "PaymentConfig",
    "PaymentResult",
    "create_langchain_tool",
    "batch_fetch",
]

logger = logging.getLogger(__name__)


# ============================================
# MODELS
# ============================================


class PaymentStatus(Enum):
    """Payment status"""

    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"


@dataclass
class PaymentResult:
    """Result of a payment attempt"""

    status: PaymentStatus
    response: Optional[Union[requests.Response, Dict]] = None
    amount: Optional[Decimal] = None
    token: Optional[str] = None
    transaction_hash: Optional[str] = None
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.status == PaymentStatus.COMPLETED

    @property
    def data(self) -> Any:
        """Get response data"""
        if self.response and hasattr(self.response, "json"):
            try:
                return self.response.json()
            except:
                return self.response.text
        return self.response


@dataclass
class PaymentConfig:
    """
    Agent payment configuration

    Args:
        private_key: Ethereum private key for signing payments
        daily_limit: Maximum daily spending limit
        per_request_limit: Maximum amount per single request
        auto_approve: Automatically approve payments within limits
        allowed_tokens: List of accepted payment tokens
        allowed_domains: List of allowed payment domains
        approval_callback: Custom approval function
    """

    private_key: str
    daily_limit: Decimal = Decimal("100.0")
    per_request_limit: Decimal = Decimal("10.0")
    auto_approve: bool = True
    allowed_tokens: List[str] = field(default_factory=lambda: ["USDC"])
    allowed_domains: List[str] = field(default_factory=list)
    approval_callback: Optional[Callable] = None

    # Network config
    chain_id: int = 8453  # Base mainnet
    rpc_url: str = "https://base.llamarpc.com"

    def __post_init__(self):
        """Validate configuration"""
        if not self.private_key:
            raise ValueError("Private key is required")
        if self.daily_limit <= 0:
            raise ValueError("Daily limit must be positive")
        if self.per_request_limit <= 0:
            raise ValueError("Per request limit must be positive")


# ============================================
# MAIN AGENT CLASS
# ============================================


class X402Agent:
    """
    AI Agent with x402 payment capabilities

    Example:
        agent = X402Agent(private_key="your_key")

        # Simple payment
        result = agent.fetch("https://api.example.com/data", max_amount=0.10)

        # Batch operations
        results = agent.batch_fetch([
            {"url": "https://api1.com/data", "max_amount": 0.05},
            {"url": "https://api2.com/data", "max_amount": 0.10}
        ])
    """

    def __init__(
        self,
        private_key: Optional[str] = None,
        config: Optional[PaymentConfig] = None,
        **kwargs,
    ):
        # Initialize config
        if config:
            self.config = config
        else:
            # Get private key from env if not provided
            if not private_key:
                private_key = os.getenv("X402_PRIVATE_KEY")
                if not private_key:
                    raise ValueError(
                        "Private key required. Set X402_PRIVATE_KEY env variable."
                    )

            self.config = PaymentConfig(private_key=private_key, **kwargs)

        # Initialize account
        self.account = Account.from_key(self.config.private_key)
        self.address = self.account.address

        # Web3 instance
        self.w3 = Web3(Web3.HTTPProvider(self.config.rpc_url))

        # Session for HTTP requests
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": f"x402-agent/{__version__}"})

        # Spending tracking
        self._daily_spend = Decimal("0")
        self._last_reset = time.strftime("%Y-%m-%d")
        self._payment_history = []

        logger.info(f"X402Agent initialized with address: {self.address}")

    def fetch(
        self,
        url: str,
        max_amount: Union[float, Decimal] = None,
        method: str = "GET",
        **kwargs,
    ) -> PaymentResult:
        """
        Fetch a resource, handling x402 payments automatically

        Args:
            url: URL to fetch
            max_amount: Maximum amount willing to pay
            method: HTTP method
            **kwargs: Additional request arguments

        Returns:
            PaymentResult with response data
        """
        max_amount = (
            Decimal(str(max_amount)) if max_amount else self.config.per_request_limit
        )

        # Make initial request
        try:
            response = self.session.request(method, url, **kwargs)

            # If not 402, return successful response
            if response.status_code != 402:
                return PaymentResult(
                    status=PaymentStatus.COMPLETED,
                    response=response,
                    amount=Decimal("0"),
                )

            # Parse payment requirements
            requirements = self._parse_requirements(response)

            # Validate payment
            validation_result = self._validate_payment(requirements, max_amount)
            if not validation_result[0]:
                return PaymentResult(
                    status=PaymentStatus.REJECTED, error=validation_result[1]
                )

            # Get approval
            if not self._get_approval(requirements):
                return PaymentResult(
                    status=PaymentStatus.REJECTED,
                    error="Payment rejected by approval process",
                )

            # Make payment
            payment_result = self._make_payment(url, requirements, method, **kwargs)

            # Track spending
            if payment_result.success:
                self._track_spending(requirements["amount"])
                self._payment_history.append(
                    {
                        "url": url,
                        "amount": requirements["amount"],
                        "timestamp": time.time(),
                    }
                )

            return payment_result

        except Exception as e:
            logger.error(f"Request failed: {e}")
            return PaymentResult(status=PaymentStatus.FAILED, error=str(e))

    async def fetch_async(
        self,
        url: str,
        max_amount: Union[float, Decimal] = None,
        method: str = "GET",
        **kwargs,
    ) -> PaymentResult:
        """Async version of fetch"""
        # Async implementation
        async with aiohttp.ClientSession() as session:
            async with session.request(method, url, **kwargs) as response:
                if response.status != 402:
                    return PaymentResult(
                        status=PaymentStatus.COMPLETED,
                        response=await response.json(),
                        amount=Decimal("0"),
                    )

                # Handle payment flow...
                # Similar to sync version but with async calls

    def batch_fetch(
        self,
        requests: List[Dict[str, Any]],
        parallel: bool = False,
        max_workers: int = 5,
    ) -> List[PaymentResult]:
        """
        Fetch multiple resources

        Args:
            requests: List of request configurations
            parallel: Execute requests in parallel
            max_workers: Max parallel workers

        Returns:
            List of PaymentResults
        """
        results = []

        if parallel:
            from concurrent.futures import ThreadPoolExecutor

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = []
                for req in requests:
                    future = executor.submit(
                        self.fetch,
                        req["url"],
                        req.get("max_amount"),
                        req.get("method", "GET"),
                        **req.get("kwargs", {}),
                    )
                    futures.append(future)

                for future in futures:
                    results.append(future.result())
        else:
            for req in requests:
                result = self.fetch(
                    req["url"],
                    req.get("max_amount"),
                    req.get("method", "GET"),
                    **req.get("kwargs", {}),
                )
                results.append(result)

        return results

    def _parse_requirements(self, response: requests.Response) -> Dict[str, Any]:
        """Parse payment requirements from 402 response"""
        # Try header first
        payment_header = response.headers.get("X-Payment-Required")
        if payment_header:
            data = json.loads(payment_header)
        else:
            data = response.json()

        return {
            "amount": Decimal(str(data["amount"])),
            "token": data["token"],
            "recipient": data["recipient"],
            "chain_id": data.get("chainId", self.config.chain_id),
            "nonce": data["nonce"],
            "expires_at": data["expiresAt"],
            "metadata": data.get("metadata", {}),
        }

    def _validate_payment(
        self, requirements: Dict[str, Any], max_amount: Decimal
    ) -> Tuple[bool, Optional[str]]:
        """Validate payment requirements"""
        # Check amount
        if requirements["amount"] > max_amount:
            return False, f"Amount {requirements['amount']} exceeds max {max_amount}"

        if requirements["amount"] > self.config.per_request_limit:
            return False, f"Amount exceeds per-request limit"

        # Check daily limit
        if self._daily_spend + requirements["amount"] > self.config.daily_limit:
            return False, "Would exceed daily spending limit"

        # Check token
        if requirements["token"] not in self.config.allowed_tokens:
            return False, f"Token {requirements['token']} not allowed"

        # Check domain
        if self.config.allowed_domains:
            # Extract domain from metadata or URL
            domain = requirements.get("metadata", {}).get("domain", "")
            if not any(d in domain for d in self.config.allowed_domains):
                return False, "Domain not in allowed list"

        # Check expiration
        if requirements["expires_at"] < int(time.time()):
            return False, "Payment requirements expired"

        return True, None

    def _get_approval(self, requirements: Dict[str, Any]) -> bool:
        """Get payment approval"""
        if self.config.auto_approve:
            return True

        if self.config.approval_callback:
            return self.config.approval_callback(requirements)

        # Default: approve if under 10% of daily limit
        return requirements["amount"] < (self.config.daily_limit * Decimal("0.1"))

    def _make_payment(
        self, url: str, requirements: Dict[str, Any], method: str, **kwargs
    ) -> PaymentResult:
        """Execute payment and retry request"""
        try:
            # Create payment signature
            signature = self._create_signature(requirements)

            # Prepare payment data
            payment_data = {
                "signature": signature,
                "signer": self.address,
                "amount": str(requirements["amount"]),
                "token": requirements["token"],
                "nonce": requirements["nonce"],
                "expiresAt": requirements["expires_at"],
            }

            # Add payment header
            headers = kwargs.get("headers", {}).copy()
            headers["X-Payment"] = json.dumps(payment_data)
            kwargs["headers"] = headers

            # Retry request with payment
            response = self.session.request(method, url, **kwargs)

            if response.status_code == 200:
                tx_hash = response.headers.get("X-Payment-Transaction")
                return PaymentResult(
                    status=PaymentStatus.COMPLETED,
                    response=response,
                    amount=requirements["amount"],
                    token=requirements["token"],
                    transaction_hash=tx_hash,
                )
            else:
                return PaymentResult(
                    status=PaymentStatus.FAILED,
                    error=f"Payment failed with status {response.status_code}",
                    response=response,
                )

        except Exception as e:
            logger.error(f"Payment failed: {e}")
            return PaymentResult(status=PaymentStatus.FAILED, error=str(e))

    def _create_signature(self, requirements: Dict[str, Any]) -> str:
        """Create EIP-712 payment signature"""
        structured_data = {
            "types": {
                "EIP712Domain": [
                    {"name": "name", "type": "string"},
                    {"name": "version", "type": "string"},
                    {"name": "chainId", "type": "uint256"},
                ],
                "Payment": [
                    {"name": "recipient", "type": "address"},
                    {"name": "amount", "type": "uint256"},
                    {"name": "token", "type": "address"},
                    {"name": "nonce", "type": "uint256"},
                    {"name": "expiresAt", "type": "uint256"},
                ],
            },
            "domain": {
                "name": "x402 Payment",
                "version": "1",
                "chainId": requirements["chain_id"],
            },
            "primaryType": "Payment",
            "message": {
                "recipient": requirements["recipient"],
                "amount": int(requirements["amount"] * 10**6),  # USDC decimals
                "token": self._get_token_address(requirements["token"]),
                "nonce": int(requirements["nonce"]),
                "expiresAt": requirements["expires_at"],
            },
        }

        encoded = encode_structured_data(structured_data)
        signed_message = self.account.sign_message(encoded)
        return signed_message.signature.hex()

    def _get_token_address(self, token: str) -> str:
        """Get token contract address"""
        addresses = {
            "USDC": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
            "USDT": "0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2",
            "DAI": "0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb",
        }
        return addresses.get(token, token)

    def _track_spending(self, amount: Decimal):
        """Track spending against limits"""
        today = time.strftime("%Y-%m-%d")
        if today != self._last_reset:
            self._daily_spend = Decimal("0")
            self._last_reset = today

        self._daily_spend += amount

    def get_balance(self) -> Dict[str, Any]:
        """Get current spending balance"""
        return {
            "daily_spent": float(self._daily_spend),
            "daily_remaining": float(self.config.daily_limit - self._daily_spend),
            "daily_limit": float(self.config.daily_limit),
            "per_request_limit": float(self.config.per_request_limit),
        }

    def get_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get payment history"""
        return self._payment_history[-limit:]


# ============================================
# LANGCHAIN INTEGRATION
# ============================================

if LANGCHAIN_AVAILABLE:

    class X402ToolInput(BaseModel):
        """Input schema for x402 tool"""

        url: str = Field(description="URL to fetch")
        max_amount: float = Field(default=1.0, description="Max amount to pay")
        method: str = Field(default="GET", description="HTTP method")

    class X402Tool(BaseTool):
        """LangChain tool for x402 payments"""

        name = "x402_fetch"
        description = "Fetch data from x402-enabled APIs with automatic payment"
        args_schema = X402ToolInput

        def __init__(self, agent: X402Agent, **kwargs):
            super().__init__(**kwargs)
            self.agent = agent

        def _run(
            self,
            url: str,
            max_amount: float = 1.0,
            method: str = "GET",
            run_manager: Optional[CallbackManagerForToolRun] = None,
        ) -> str:
            """Execute the tool"""
            result = self.agent.fetch(url, max_amount, method)

            if result.success:
                return json.dumps(result.data)
            else:
                return f"Failed: {result.error}"

        async def _arun(self, *args, **kwargs):
            """Async execution"""
            raise NotImplementedError("Async not yet supported")


def create_langchain_tool(
    private_key: str = None, config: PaymentConfig = None, **kwargs
) -> "X402Tool":
    """
    Create a LangChain tool for x402 payments

    Example:
        tool = create_langchain_tool(private_key="your_key")

        agent = initialize_agent(
            tools=[tool],
            llm=llm,
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION
        )
    """
    if not LANGCHAIN_AVAILABLE:
        raise ImportError(
            "LangChain not installed. Install with: pip install langchain"
        )

    agent = X402Agent(private_key=private_key, config=config, **kwargs)
    return X402Tool(agent=agent)


# ============================================
# CONVENIENCE FUNCTIONS
# ============================================


def batch_fetch(
    urls: List[str],
    private_key: str = None,
    max_amount: float = 1.0,
    parallel: bool = True,
) -> List[PaymentResult]:
    """
    Convenience function for batch fetching

    Example:
        results = batch_fetch([
            "https://api1.com/data",
            "https://api2.com/data"
        ], max_amount=0.10)
    """
    agent = X402Agent(private_key=private_key)
    requests = [{"url": url, "max_amount": max_amount} for url in urls]
    return agent.batch_fetch(requests, parallel=parallel)


def create_agent(**kwargs) -> X402Agent:
    """Create an X402Agent with configuration"""
    return X402Agent(**kwargs)


# ============================================
# CLI INTERFACE
# ============================================


def main():
    """CLI interface for x402-agent"""
    import argparse

    parser = argparse.ArgumentParser(description="x402 Agent CLI")
    parser.add_argument("url", help="URL to fetch")
    parser.add_argument(
        "--max-amount", type=float, default=1.0, help="Max payment amount"
    )
    parser.add_argument("--private-key", help="Private key (or set X402_PRIVATE_KEY)")

    args = parser.parse_args()

    try:
        agent = X402Agent(private_key=args.private_key)
        result = agent.fetch(args.url, args.max_amount)

        if result.success:
            print(f"Success! Paid {result.amount} {result.token}")
            print(f"Data: {result.data}")
        else:
            print(f"Failed: {result.error}")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
"""
x402 Python SDK for LangChain
A comprehensive SDK for integrating x402 payment protocol with LangChain agents
"""

import json
import time
import logging
from typing import Dict, Any, Optional, List, Union, Callable
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
import requests
from eth_account import Account
from eth_account.messages import encode_structured_data
from web3 import Web3
from langchain.tools import BaseTool
from langchain.callbacks.manager import CallbackManagerForToolRun
from langchain.agents import AgentExecutor
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PaymentStatus(Enum):
    """Payment status enumeration"""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class TokenType(Enum):
    """Supported token types"""
    USDC = "USDC"
    USDT = "USDT"
    DAI = "DAI"


@dataclass
class PaymentRequirements:
    """Payment requirements from 402 response"""
    amount: Decimal
    token: str
    recipient: str
    chain_id: int
    nonce: str
    expires_at: int
    payment_url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PaymentResult:
    """Result of a payment transaction"""
    status: PaymentStatus
    transaction_hash: Optional[str] = None
    amount: Optional[Decimal] = None
    token: Optional[str] = None
    error: Optional[str] = None
    response_data: Optional[Any] = None


@dataclass
class AgentWallet:
    """Wallet configuration for an agent"""
    private_key: str
    address: str
    spending_limit_per_request: Decimal
    spending_limit_daily: Decimal
    allowed_tokens: List[str] = field(default_factory=lambda: ["USDC"])
    allowed_domains: List[str] = field(default_factory=list)
    current_daily_spend: Decimal = field(default=Decimal("0"))
    last_reset_date: str = field(default="")


class X402Config:
    """Configuration for x402 SDK"""
    def __init__(
        self,
        private_key: str,
        rpc_url: str = "https://base.llamarpc.com",
        chain_id: int = 8453,  # Base mainnet
        max_retries: int = 3,
        timeout: int = 30,
        spending_limit_per_request: Decimal = Decimal("1.0"),
        spending_limit_daily: Decimal = Decimal("100.0"),
        allowed_tokens: List[str] = None,
        allowed_domains: List[str] = None,
        auto_approve: bool = False,
        approval_callback: Optional[Callable] = None
    ):
        self.account = Account.from_key(private_key)
        self.wallet = AgentWallet(
            private_key=private_key,
            address=self.account.address,
            spending_limit_per_request=spending_limit_per_request,
            spending_limit_daily=spending_limit_daily,
            allowed_tokens=allowed_tokens or ["USDC"],
            allowed_domains=allowed_domains or []
        )
        self.rpc_url = rpc_url
        self.chain_id = chain_id
        self.max_retries = max_retries
        self.timeout = timeout
        self.auto_approve = auto_approve
        self.approval_callback = approval_callback
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))


class X402Client:
    """Main client for x402 protocol interactions"""
    
    def __init__(self, config: X402Config):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "x402-python-sdk/1.0.0"
        })
    
    def parse_payment_requirements(self, response: requests.Response) -> PaymentRequirements:
        """Parse payment requirements from HTTP 402 response"""
        try:
            # Check for X-Payment-Required header
            payment_header = response.headers.get("X-Payment-Required")
            if payment_header:
                data = json.loads(payment_header)
            else:
                # Fallback to response body
                data = response.json()
            
            return PaymentRequirements(
                amount=Decimal(str(data["amount"])),
                token=data["token"],
                recipient=data["recipient"],
                chain_id=data.get("chainId", self.config.chain_id),
                nonce=data["nonce"],
                expires_at=data["expiresAt"],
                payment_url=data.get("paymentUrl"),
                metadata=data.get("metadata", {})
            )
        except Exception as e:
            logger.error(f"Failed to parse payment requirements: {e}")
            raise ValueError(f"Invalid payment requirements format: {e}")
    
    def validate_payment_requirements(self, requirements: PaymentRequirements) -> bool:
        """Validate payment requirements against wallet constraints"""
        # Check token allowlist
        if requirements.token not in self.config.wallet.allowed_tokens:
            raise ValueError(f"Token {requirements.token} not in allowed tokens")
        
        # Check spending limits
        if requirements.amount > self.config.wallet.spending_limit_per_request:
            raise ValueError(f"Amount {requirements.amount} exceeds per-request limit")
        
        # Check daily spending limit
        today = time.strftime("%Y-%m-%d")
        if self.config.wallet.last_reset_date != today:
            self.config.wallet.current_daily_spend = Decimal("0")
            self.config.wallet.last_reset_date = today
        
        if self.config.wallet.current_daily_spend + requirements.amount > self.config.wallet.spending_limit_daily:
            raise ValueError(f"Payment would exceed daily spending limit")
        
        # Check expiration
        if requirements.expires_at < int(time.time()):
            raise ValueError("Payment requirements have expired")
        
        return True
    
    def create_payment_signature(self, requirements: PaymentRequirements) -> str:
        """Create EIP-712 signature for payment authorization"""
        # EIP-712 structured data
        structured_data = {
            "types": {
                "EIP712Domain": [
                    {"name": "name", "type": "string"},
                    {"name": "version", "type": "string"},
                    {"name": "chainId", "type": "uint256"},
                ],
                "Payment": [
                    {"name": "recipient", "type": "address"},
                    {"name": "amount", "type": "uint256"},
                    {"name": "token", "type": "address"},
                    {"name": "nonce", "type": "uint256"},
                    {"name": "expiresAt", "type": "uint256"},
                ]
            },
            "domain": {
                "name": "x402 Payment",
                "version": "1",
                "chainId": requirements.chain_id,
            },
            "primaryType": "Payment",
            "message": {
                "recipient": requirements.recipient,
                "amount": int(requirements.amount * 10**6),  # USDC has 6 decimals
                "token": self._get_token_address(requirements.token),
                "nonce": int(requirements.nonce),
                "expiresAt": requirements.expires_at,
            }
        }
        
        # Sign the structured data
        encoded = encode_structured_data(structured_data)
        signed_message = self.config.account.sign_message(encoded)
        
        return signed_message.signature.hex()
    
    def _get_token_address(self, token_symbol: str) -> str:
        """Get token contract address for given symbol"""
        # Base mainnet addresses
        token_addresses = {
            "USDC": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
            "USDT": "0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2",
            "DAI": "0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb"
        }
        return token_addresses.get(token_symbol, token_symbol)
    
    def make_payment_request(
        self,
        url: str,
        requirements: PaymentRequirements,
        method: str = "GET",
        **kwargs
    ) -> PaymentResult:
        """Make HTTP request with payment authorization"""
        try:
            # Validate requirements
            self.validate_payment_requirements(requirements)
            
            # Get approval if needed
            if not self.config.auto_approve:
                if self.config.approval_callback:
                    approved = self.config.approval_callback(requirements)
                    if not approved:
                        return PaymentResult(
                            status=PaymentStatus.FAILED,
                            error="Payment rejected by approval callback"
                        )
            
            # Create payment signature
            signature = self.create_payment_signature(requirements)
            
            # Prepare payment header
            payment_data = {
                "signature": signature,
                "signer": self.config.wallet.address,
                "amount": str(requirements.amount),
                "token": requirements.token,
                "nonce": requirements.nonce,
                "expiresAt": requirements.expires_at
            }
            
            # Add payment header
            headers = kwargs.get("headers", {})
            headers["X-Payment"] = json.dumps(payment_data)
            kwargs["headers"] = headers
            
            # Make request
            response = self.session.request(method, url, **kwargs)
            
            # Check if payment was successful
            if response.status_code == 200:
                # Update daily spend
                self.config.wallet.current_daily_spend += requirements.amount
                
                # Extract transaction hash from response
                tx_hash = response.headers.get("X-Payment-Transaction")
                
                return PaymentResult(
                    status=PaymentStatus.COMPLETED,
                    transaction_hash=tx_hash,
                    amount=requirements.amount,
                    token=requirements.token,
                    response_data=response
                )
            else:
                return PaymentResult(
                    status=PaymentStatus.FAILED,
                    error=f"Payment failed with status {response.status_code}",
                    response_data=response
                )
                
        except Exception as e:
            logger.error(f"Payment request failed: {e}")
            return PaymentResult(
                status=PaymentStatus.FAILED,
                error=str(e)
            )
    
    def fetch_with_payment(
        self,
        url: str,
        method: str = "GET",
        max_amount: Optional[Decimal] = None,
        **kwargs
    ) -> Union[requests.Response, PaymentResult]:
        """Fetch resource, automatically handling 402 payment requirements"""
        
        # Initial request
        response = self.session.request(method, url, **kwargs)
        
        # If not 402, return response as-is
        if response.status_code != 402:
            return response
        
        # Parse payment requirements
        requirements = self.parse_payment_requirements(response)
        
        # Check max amount if specified
        if max_amount and requirements.amount > max_amount:
            return PaymentResult(
                status=PaymentStatus.FAILED,
                error=f"Required amount {requirements.amount} exceeds max {max_amount}"
            )
        
        # Make payment and retry request
        payment_result = self.make_payment_request(url, requirements, method, **kwargs)
        
        if payment_result.status == PaymentStatus.COMPLETED:
            return payment_result.response_data
        else:
            return payment_result


# LangChain Integration

class X402PaymentToolInput(BaseModel):
    """Input schema for x402 payment tool"""
    url: str = Field(description="URL of the resource to access")
    method: str = Field(default="GET", description="HTTP method to use")
    max_amount: float = Field(default=1.0, description="Maximum amount willing to pay")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Request body data")


class X402PaymentTool(BaseTool):
    """LangChain tool for making x402 payments"""
    
    name = "x402_payment"
    description = """Make payments to access x402-enabled resources. 
    Use this when you need to access paid APIs, data sources, or services.
    The tool will automatically handle payment requirements and retry the request."""
    args_schema = X402PaymentToolInput
    
    def __init__(self, client: X402Client, **kwargs):
        super().__init__(**kwargs)
        self.client = client
    
    def _run(
        self,
        url: str,
        method: str = "GET",
        max_amount: float = 1.0,
        data: Optional[Dict[str, Any]] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Execute payment-enabled request"""
        try:
            result = self.client.fetch_with_payment(
                url=url,
                method=method,
                max_amount=Decimal(str(max_amount)),
                json=data
            )
            
            if isinstance(result, PaymentResult):
                if result.status == PaymentStatus.FAILED:
                    return f"Payment failed: {result.error}"
                else:
                    return f"Payment status: {result.status}"
            else:
                # Successful response
                if hasattr(result, 'json'):
                    try:
                        return json.dumps(result.json())
                    except:
                        return result.text
                else:
                    return str(result)
                    
        except Exception as e:
            return f"Error: {str(e)}"
    
    async def _arun(self, *args, **kwargs):
        """Async version not implemented yet"""
        raise NotImplementedError("Async execution not yet supported")


class X402Agent:
    """High-level agent wrapper with x402 payment capabilities"""
    
    def __init__(
        self,
        private_key: str,
        agent_executor: AgentExecutor,
        config_kwargs: Optional[Dict[str, Any]] = None
    ):
        # Initialize x402 config
        config_params = config_kwargs or {}
        self.config = X402Config(private_key=private_key, **config_params)
        self.client = X402Client(self.config)
        
        # Create payment tool
        self.payment_tool = X402PaymentTool(client=self.client)
        
        # Add to agent's tools
        if hasattr(agent_executor, 'tools'):
            agent_executor.tools.append(self.payment_tool)
        
        self.agent = agent_executor
    
    def run(self, *args, **kwargs):
        """Run agent with payment capabilities"""
        return self.agent.run(*args, **kwargs)
    
    def get_spending_report(self) -> Dict[str, Any]:
        """Get spending report for the agent"""
        return {
            "address": self.config.wallet.address,
            "daily_spend": float(self.config.wallet.current_daily_spend),
            "daily_limit": float(self.config.wallet.spending_limit_daily),
            "per_request_limit": float(self.config.wallet.spending_limit_per_request),
            "allowed_tokens": self.config.wallet.allowed_tokens,
            "allowed_domains": self.config.wallet.allowed_domains
        }


# Utility functions

def create_x402_agent(
    private_key: str,
    langchain_agent: AgentExecutor,
    spending_limit_daily: float = 100.0,
    spending_limit_per_request: float = 1.0,
    auto_approve: bool = False,
    **kwargs
) -> X402Agent:
    """Convenience function to create an x402-enabled agent"""
    
    config_kwargs = {
        "spending_limit_daily": Decimal(str(spending_limit_daily)),
        "spending_limit_per_request": Decimal(str(spending_limit_per_request)),
        "auto_approve": auto_approve,
        **kwargs
    }
    
    return X402Agent(
        private_key=private_key,
        agent_executor=langchain_agent,
        config_kwargs=config_kwargs
    )


# Example usage
if __name__ == "__main__":
    # Example: Create x402-enabled agent
    from langchain.agents import create_react_agent
    from langchain.llms import OpenAI
    
    # Initialize LLM and base agent
    llm = OpenAI()
    base_agent = create_react_agent(llm=llm, tools=[])
    
    # Add x402 payment capabilities
    x402_agent = create_x402_agent(
        private_key="YOUR_PRIVATE_KEY",
        langchain_agent=base_agent,
        spending_limit_daily=10.0,
        auto_approve=True
    )
    
    # Use the agent
    result = x402_agent.run("Access the premium API at https://api.example.com/data")
    print(result)