"""Tests for LangChain tools"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from langchain.callbacks.manager import CallbackManagerForToolRun

from x402_langchain import X402PaymentTool, create_x402_tool, X402Config
from x402_langchain.models import PaymentResult
from x402_langchain.exceptions import SpendingLimitError


@pytest.fixture
def config():
    """Create test configuration"""
    return X402Config(
        private_key="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
        spending_limits={
            "per_request": 1.0,
            "per_hour": 10.0,
            "per_day": 100.0,
        },
        auto_approve=True,
    )


@pytest.fixture
def payment_tool(config):
    """Create test payment tool"""
    return X402PaymentTool(config)


class TestX402PaymentTool:
    def test_tool_properties(self, payment_tool):
        """Test tool has correct properties"""
        assert payment_tool.name == "x402_payment"
        assert "pay for and access" in payment_tool.description.lower()
        assert payment_tool.args_schema is not None
    
    @pytest.mark.asyncio
    async def test_successful_payment(self, payment_tool):
        """Test successful payment flow"""
        mock_result = PaymentResult(
            success=True,
            url="https://api.test.com/data",
            amount="0.50",
            token="0xUSDC",
            transaction_hash="0xhash123",
            data={"result": "premium data"},
        )
        
        with patch.object(payment_tool.client, "fetch_with_payment", return_value=mock_result):
            result = await payment_tool._arun(
                url="https://api.test.com/data",
                max_amount=1.0,
            )
        
        assert "Successfully paid 0.50" in result
        assert "https://api.test.com/data" in result
        assert "premium data" in result
    
    @pytest.mark.asyncio
    async def test_free_resource(self, payment_tool):
        """Test accessing free resource"""
        mock_result = PaymentResult(
            success=True,
            url="https://api.test.com/free",
            amount="0",
            token="",
            data={"result": "free data"},
        )
        
        with patch.object(payment_tool.client, "fetch_with_payment", return_value=mock_result):
            result = await payment_tool._arun(
                url="https://api.test.com/free",
                max_amount=1.0,
            )
        
        assert "no payment required" in result
        assert "free data" in result
    
    @pytest.mark.asyncio
    async def test_failed_payment(self, payment_tool):
        """Test failed payment"""
        mock_result = PaymentResult(
            success=False,
            url="https://api.test.com/data",
            amount="0.50",
            token="0xUSDC",
            error="Insufficient funds",
        )
        
        with patch.object(payment_tool.client, "fetch_with_payment", return_value=mock_result):
            result = await payment_tool._arun(
                url="https://api.test.com/data",
                max_amount=1.0,
            )
        
        assert "Failed to access" in result
        assert "Insufficient funds" in result
    
    @pytest.mark.asyncio
    async def test_payment_error_handling(self, payment_tool):
        """Test error handling"""
        with patch.object(
            payment_tool.client, 
            "fetch_with_payment", 
            side_effect=SpendingLimitError("Daily limit exceeded")
        ):
            result = await payment_tool._arun(
                url="https://api.test.com/data",
                max_amount=1.0,
            )
        
        assert "Payment error" in result
        assert "Daily limit exceeded" in result
    
    @pytest.mark.asyncio
    async def test_unexpected_error_handling(self, payment_tool):
        """Test handling of unexpected errors"""
        with patch.object(
            payment_tool.client,
            "fetch_with_payment",
            side_effect=Exception("Network error")
        ):
            result = await payment_tool._arun(
                url="https://api.test.com/data",
                max_amount=1.0,
            )
        
        assert "Unexpected error" in result
        assert "Network error" in result
    
    def test_sync_run(self, payment_tool):
        """Test synchronous run method"""
        mock_result = PaymentResult(
            success=True,
            url="https://api.test.com/data",
            amount="0.25",
            token="0xUSDC",
            data={"sync": "data"},
        )
        
        async def mock_fetch(*args, **kwargs):
            return mock_result
        
        with patch.object(payment_tool.client, "fetch_with_payment", side_effect=mock_fetch):
            result = payment_tool._run(
                url="https://api.test.com/data",
                max_amount=1.0,
            )
        
        assert "Successfully paid" in result
        assert "sync" in result


class TestCreateX402Tool:
    def test_create_tool_with_defaults(self):
        """Test creating tool with default settings"""
        tool = create_x402_tool(
            private_key="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
        )
        
        assert isinstance(tool, X402PaymentTool)
        assert tool.client.config.spending_limits.per_day == 100.0
        assert tool.client.config.spending_limits.per_request == 1.0
        assert tool.client.config.auto_approve is True
    
    def test_create_tool_with_custom_limits(self):
        """Test creating tool with custom limits"""
        tool = create_x402_tool(
            private_key="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            spending_limit_daily=50.0,
            spending_limit_per_request=5.0,
            auto_approve=False,
            allowed_domains=["api.trusted.com"],
        )
        
        assert tool.client.config.spending_limits.per_day == 50.0
        assert tool.client.config.spending_limits.per_request == 5.0
        assert tool.client.config.spending_limits.per_hour == 50.0 / 24
        assert tool.client.config.auto_approve is False
        assert tool.client.config.allowed_domains == ["api.trusted.com"]
    
    def test_tool_input_schema(self):
        """Test tool input schema validation"""
        tool = create_x402_tool(
            private_key="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
        )
        
        # Get schema
        schema = tool.args_schema.schema()
        
        assert "url" in schema["properties"]
        assert schema["properties"]["url"]["type"] == "string"
        assert "max_amount" in schema["properties"]
        assert schema["properties"]["max_amount"]["default"] == 1.0
        assert "method" in schema["properties"]
        assert schema["properties"]["method"]["default"] == "GET"