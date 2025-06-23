"""Tests for X402Client"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock
import httpx

from x402_langchain import X402Client, X402Config
from x402_langchain.models import PaymentRequirement, PaymentResult
from x402_langchain.exceptions import (
    SpendingLimitError,
    DomainNotAllowedError,
    PaymentDeniedError,
)


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
        allowed_domains=["api.test.com", "data.test.com"],
        blocked_domains=["bad.com"],
    )


@pytest.fixture
def client(config):
    """Create test client"""
    return X402Client(config)


@pytest.fixture
def payment_requirement():
    """Create test payment requirement"""
    return PaymentRequirement(
        amount="0.50",
        token="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        recipient="0x742d35Cc6634C0532925a3b844Bc9e7595f6E123",
        chain_id=8453,
        nonce="0x1234",
        expires_at=int(time.time()) + 300,
    )


class TestX402Client:
    @pytest.mark.asyncio
    async def test_fetch_free_resource(self, client):
        """Test fetching resource that doesn't require payment"""
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"data": "free"}
        
        with patch.object(httpx.AsyncClient, "request", return_value=mock_response):
            result = await client.fetch_with_payment("https://api.test.com/free")
        
        assert result.success is True
        assert result.amount == "0"
        assert result.data == {"data": "free"}
    
    @pytest.mark.asyncio
    async def test_fetch_paid_resource(self, client, payment_requirement):
        """Test fetching resource that requires payment"""
        # First response: 402 Payment Required
        mock_402_response = AsyncMock()
        mock_402_response.status_code = 402
        mock_402_response.json.return_value = payment_requirement.model_dump(by_alias=True)
        
        # Second response: 200 OK with data
        mock_200_response = AsyncMock()
        mock_200_response.status_code = 200
        mock_200_response.headers = {
            "content-type": "application/json",
            "X-Payment-Confirmation": "0xtxhash",
        }
        mock_200_response.json.return_value = {"data": "paid content"}
        
        with patch.object(
            httpx.AsyncClient, 
            "request", 
            side_effect=[mock_402_response, mock_200_response]
        ):
            result = await client.fetch_with_payment(
                "https://api.test.com/paid",
                max_amount=1.0
            )
        
        assert result.success is True
        assert result.amount == "0.50"
        assert result.data == {"data": "paid content"}
        assert result.transaction_hash == "0xtxhash"
    
    @pytest.mark.asyncio
    async def test_domain_not_allowed(self, client):
        """Test blocked domain raises error"""
        with pytest.raises(DomainNotAllowedError) as exc_info:
            await client.fetch_with_payment("https://notallowed.com/data")
        
        assert "not in allowed list" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_blocked_domain(self, client):
        """Test explicitly blocked domain raises error"""
        with pytest.raises(DomainNotAllowedError) as exc_info:
            await client.fetch_with_payment("https://bad.com/data")
        
        assert "is blocked" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_spending_limit_per_request(self, client, payment_requirement):
        """Test per-request spending limit"""
        payment_requirement.amount = "2.00"  # Exceeds 1.0 limit
        
        mock_response = AsyncMock()
        mock_response.status_code = 402
        mock_response.json.return_value = payment_requirement.model_dump(by_alias=True)
        
        with patch.object(httpx.AsyncClient, "request", return_value=mock_response):
            with pytest.raises(SpendingLimitError) as exc_info:
                await client.fetch_with_payment(
                    "https://api.test.com/expensive",
                    max_amount=5.0  # High max, but per-request limit applies
                )
        
        assert "would exceed spending limits" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_max_amount_limit(self, client, payment_requirement):
        """Test max_amount parameter"""
        payment_requirement.amount = "0.75"
        
        mock_response = AsyncMock()
        mock_response.status_code = 402
        mock_response.json.return_value = payment_requirement.model_dump(by_alias=True)
        
        with patch.object(httpx.AsyncClient, "request", return_value=mock_response):
            with pytest.raises(SpendingLimitError) as exc_info:
                await client.fetch_with_payment(
                    "https://api.test.com/data",
                    max_amount=0.50  # Less than required 0.75
                )
        
        assert "exceeds max" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_spending_tracking(self, client, payment_requirement):
        """Test spending is tracked correctly"""
        payment_requirement.amount = "0.25"
        
        # Setup successful payment responses
        mock_402 = AsyncMock()
        mock_402.status_code = 402
        mock_402.json.return_value = payment_requirement.model_dump(by_alias=True)
        
        mock_200 = AsyncMock()
        mock_200.status_code = 200
        mock_200.headers = {"content-type": "application/json"}
        mock_200.json.return_value = {"data": "ok"}
        
        # Make multiple payments
        for i in range(3):
            with patch.object(
                httpx.AsyncClient,
                "request",
                side_effect=[mock_402, mock_200]
            ):
                await client.fetch_with_payment(f"https://api.test.com/data{i}")
        
        # Check spending status
        status = client.get_spending_status()
        assert status["spent_hour"] == 0.75  # 3 * 0.25
        assert status["spent_today"] == 0.75
        assert status["remaining"]["hour"] == 9.25  # 10.0 - 0.75
        assert status["remaining"]["day"] == 99.25  # 100.0 - 0.75
    
    @pytest.mark.asyncio
    async def test_custom_approval_callback(self, payment_requirement):
        """Test custom approval callback"""
        approved_urls = []
        
        async def custom_approval(url: str, amount: float) -> bool:
            approved_urls.append(url)
            return amount < 0.30  # Only approve small amounts
        
        config = X402Config(
            private_key="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            auto_approve=False,
            approval_callback=custom_approval,
        )
        client = X402Client(config)
        
        # Test approved payment
        payment_requirement.amount = "0.25"
        mock_402 = AsyncMock()
        mock_402.status_code = 402
        mock_402.json.return_value = payment_requirement.model_dump(by_alias=True)
        
        mock_200 = AsyncMock()
        mock_200.status_code = 200
        mock_200.headers = {"content-type": "application/json"}
        mock_200.json.return_value = {"approved": True}
        
        with patch.object(
            httpx.AsyncClient,
            "request",
            side_effect=[mock_402, mock_200]
        ):
            result = await client.fetch_with_payment("https://api.test.com/cheap")
        
        assert result.success is True
        assert "https://api.test.com/cheap" in approved_urls
        
        # Test denied payment
        payment_requirement.amount = "0.50"
        mock_402.json.return_value = payment_requirement.model_dump(by_alias=True)
        
        with patch.object(httpx.AsyncClient, "request", return_value=mock_402):
            with pytest.raises(PaymentDeniedError):
                await client.fetch_with_payment("https://api.test.com/expensive")
    
    @pytest.mark.asyncio
    async def test_payment_logging(self, client, payment_requirement):
        """Test payment logging"""
        logged_payments = []
        
        async def mock_log_payment(*args, **kwargs):
            logged_payments.append(args)
        
        client._log_payment = mock_log_payment
        
        # Successful payment
        mock_402 = AsyncMock()
        mock_402.status_code = 402
        mock_402.json.return_value = payment_requirement.model_dump(by_alias=True)
        
        mock_200 = AsyncMock()
        mock_200.status_code = 200
        mock_200.headers = {"content-type": "application/json"}
        mock_200.json.return_value = {"data": "ok"}
        
        with patch.object(
            httpx.AsyncClient,
            "request",
            side_effect=[mock_402, mock_200]
        ):
            await client.fetch_with_payment("https://api.test.com/data")
        
        assert len(logged_payments) == 1
        assert logged_payments[0][0] == "https://api.test.com/data"
        assert logged_payments[0][1] == 0.5  # amount
        assert logged_payments[0][3] is True  # success
    
    @pytest.mark.asyncio
    async def test_webhook_notification(self, payment_requirement):
        """Test webhook notifications"""
        webhook_calls = []
        
        async def mock_post(self, url, json, timeout):
            webhook_calls.append((url, json))
            return AsyncMock()
        
        config = X402Config(
            private_key="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            webhook_url="https://webhook.test.com/x402",
        )
        client = X402Client(config)
        
        # Make payment
        mock_402 = AsyncMock()
        mock_402.status_code = 402
        mock_402.json.return_value = payment_requirement.model_dump(by_alias=True)
        
        mock_200 = AsyncMock()
        mock_200.status_code = 200
        mock_200.headers = {"content-type": "application/json"}
        mock_200.json.return_value = {"data": "ok"}
        
        with patch.object(httpx.AsyncClient, "request", side_effect=[mock_402, mock_200]):
            with patch.object(httpx.AsyncClient, "post", mock_post):
                await client.fetch_with_payment("https://api.test.com/data")
        
        # Give async task time to run
        await asyncio.sleep(0.1)
        
        assert len(webhook_calls) == 1
        assert webhook_calls[0][0] == "https://webhook.test.com/x402"
        assert webhook_calls[0][1]["type"] == "payment_attempt"
        assert webhook_calls[0][1]["success"] is True