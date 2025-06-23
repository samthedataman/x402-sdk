"""LangChain tools for x402 payments"""

from typing import Type, Optional, Any, Dict
from langchain.tools import BaseTool
from langchain.pydantic_v1 import BaseModel, Field
from langchain.callbacks.manager import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)

from .client import X402Client
from .config import X402Config
from .exceptions import X402Error


class X402PaymentInput(BaseModel):
    """Input for X402PaymentTool"""
    url: str = Field(description="The URL to access that requires payment")
    max_amount: float = Field(
        default=1.0,
        description="Maximum amount in USD willing to pay for this resource"
    )
    method: str = Field(
        default="GET",
        description="HTTP method to use (GET, POST, etc.)"
    )


class X402PaymentTool(BaseTool):
    """Tool for making x402 payments to access paid resources"""
    
    name = "x402_payment"
    description = """Pay for and access x402-enabled resources.
    Use this tool when you need to access APIs or resources that require payment.
    The tool will automatically handle the payment process and return the requested data.
    """
    args_schema: Type[BaseModel] = X402PaymentInput
    return_direct: bool = False
    
    client: X402Client
    
    def __init__(self, config: X402Config, **kwargs):
        """Initialize the tool with x402 configuration"""
        super().__init__(**kwargs)
        self.client = X402Client(config)
    
    def _run(
        self,
        url: str,
        max_amount: float = 1.0,
        method: str = "GET",
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Use the tool synchronously"""
        # Run async version in sync context
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(
            self._arun(url, max_amount, method, run_manager)
        )
    
    async def _arun(
        self,
        url: str,
        max_amount: float = 1.0,
        method: str = "GET",
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> str:
        """Use the tool asynchronously"""
        try:
            result = await self.client.fetch_with_payment(
                url=url,
                max_amount=max_amount,
                method=method,
            )
            
            if result.success:
                if result.amount != "0":
                    return f"Successfully paid {result.amount} to access {url}. Data: {result.data}"
                else:
                    return f"Successfully accessed {url} (no payment required). Data: {result.data}"
            else:
                return f"Failed to access {url}: {result.error}"
                
        except X402Error as e:
            return f"Payment error: {str(e)}"
        except Exception as e:
            return f"Unexpected error: {str(e)}"


def create_x402_tool(
    private_key: str,
    spending_limit_daily: float = 100.0,
    spending_limit_per_request: float = 1.0,
    auto_approve: bool = True,
    allowed_domains: Optional[list] = None,
    **kwargs
) -> X402PaymentTool:
    """Create an x402 payment tool with simplified configuration"""
    
    config = X402Config(
        private_key=private_key,
        spending_limits={
            "per_request": spending_limit_per_request,
            "per_hour": spending_limit_daily / 24,
            "per_day": spending_limit_daily,
        },
        auto_approve=auto_approve,
        allowed_domains=allowed_domains,
        **kwargs
    )
    
    return X402PaymentTool(config)