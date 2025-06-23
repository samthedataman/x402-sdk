"""Tests for X402Provider"""

import pytest
from unittest.mock import Mock, patch
import time
import asyncio

from fast_x402 import X402Provider, X402Config
from fast_x402.models import PaymentRequirement, PaymentData
from fast_x402.exceptions import InvalidPaymentError, InvalidAmountError


@pytest.fixture
def provider():
    """Create a test provider"""
    config = X402Config(
        wallet_address="0x742d35Cc6634C0532925a3b844Bc9e7595f6E123",
        chain_id=8453,
        analytics_enabled=True,
    )
    return X402Provider(config)


@pytest.fixture
def payment_data():
    """Create test payment data"""
    return PaymentData(
        from_address="0x1234567890abcdef1234567890abcdef12345678",
        to="0x742d35Cc6634C0532925a3b844Bc9e7595f6E123",
        value="100000",  # 0.1 USDC (6 decimals)
        token="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        chain_id=8453,
        nonce="0x1234567890abcdef",
        valid_before=int(time.time()) + 300,
        signature="0xabcdef1234567890",
    )


class TestX402Provider:
    def test_create_payment_requirement(self, provider):
        """Test creating payment requirements"""
        requirement = provider.create_payment_requirement(
            amount="0.10",
            endpoint="/api/test",
        )
        
        assert requirement.amount == "0.10"
        assert requirement.recipient == provider.config.wallet_address
        assert requirement.chain_id == 8453
        assert requirement.scheme == "exact"
        assert len(requirement.nonce) == 66  # 0x + 64 hex chars
        assert requirement.expires_at > time.time()
    
    def test_create_payment_requirement_custom_token(self, provider):
        """Test creating requirement with custom token"""
        custom_token = "0x0000000000000000000000000000000000000001"
        requirement = provider.create_payment_requirement(
            amount="1.00",
            token=custom_token,
            scheme="upto",
        )
        
        assert requirement.amount == "1.00"
        assert requirement.token == custom_token
        assert requirement.scheme == "upto"
    
    @pytest.mark.asyncio
    async def test_verify_payment_success(self, provider, payment_data):
        """Test successful payment verification"""
        requirement = provider.create_payment_requirement("0.10")
        
        # Mock signature verification
        with patch("fast_x402.verification.verify_eip712_signature", return_value=True):
            verification = await provider.verify_payment(
                payment_data,
                requirement,
                endpoint="/api/test"
            )
        
        assert verification.valid is True
        assert verification.transaction_hash is not None
        assert verification.error is None
    
    @pytest.mark.asyncio
    async def test_verify_payment_invalid_recipient(self, provider, payment_data):
        """Test payment with wrong recipient"""
        requirement = provider.create_payment_requirement("0.10")
        payment_data.to = "0x0000000000000000000000000000000000000000"
        
        with pytest.raises(InvalidPaymentError) as exc_info:
            await provider.verify_payment(payment_data, requirement)
        
        assert "Invalid recipient" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_verify_payment_invalid_amount(self, provider, payment_data):
        """Test payment with wrong amount"""
        requirement = provider.create_payment_requirement("1.00")  # Requires 1 USDC
        payment_data.value = "100000"  # Only 0.1 USDC
        
        with patch("fast_x402.verification.verify_eip712_signature", return_value=True):
            with pytest.raises(InvalidAmountError) as exc_info:
                await provider.verify_payment(payment_data, requirement)
        
        assert "Expected exact amount" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_verify_payment_expired(self, provider, payment_data):
        """Test expired payment"""
        requirement = provider.create_payment_requirement("0.10")
        payment_data.valid_before = int(time.time()) - 100  # Expired
        
        with pytest.raises(InvalidPaymentError) as exc_info:
            await provider.verify_payment(payment_data, requirement)
        
        assert "Payment expired" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_verify_payment_with_cache(self, provider, payment_data):
        """Test payment caching"""
        requirement = provider.create_payment_requirement("0.10")
        
        with patch("fast_x402.verification.verify_eip712_signature", return_value=True):
            # First verification
            verification1 = await provider.verify_payment(payment_data, requirement)
            
            # Second verification should use cache
            verification2 = await provider.verify_payment(payment_data, requirement)
        
        assert verification1.transaction_hash == verification2.transaction_hash
        assert len(provider.payment_cache) == 1
    
    @pytest.mark.asyncio
    async def test_custom_validation(self, payment_data):
        """Test custom validation callback"""
        custom_called = False
        
        async def custom_validation(payment: PaymentData) -> bool:
            nonlocal custom_called
            custom_called = True
            return payment.from_address != "0xbad"
        
        config = X402Config(
            wallet_address="0x742d35Cc6634C0532925a3b844Bc9e7595f6E123",
            custom_validation=custom_validation,
        )
        provider = X402Provider(config)
        requirement = provider.create_payment_requirement("0.10")
        
        with patch("fast_x402.verification.verify_eip712_signature", return_value=True):
            verification = await provider.verify_payment(payment_data, requirement)
        
        assert custom_called is True
        assert verification.valid is True
    
    def test_analytics_tracking(self, provider):
        """Test analytics data collection"""
        # Create some requirements
        for i in range(5):
            provider.create_payment_requirement("0.10", endpoint=f"/api/endpoint{i}")
        
        analytics = provider.get_analytics()
        
        assert analytics.total_requests == 5
        assert analytics.total_paid == 0  # No payments verified yet
        assert analytics.conversion_rate == 0.0
    
    @pytest.mark.asyncio
    async def test_analytics_with_payments(self, provider, payment_data):
        """Test analytics after processing payments"""
        requirement = provider.create_payment_requirement("0.10", endpoint="/api/test")
        
        # Process multiple payments
        with patch("fast_x402.verification.verify_eip712_signature", return_value=True):
            for i in range(3):
                # Modify nonce to avoid cache
                payment_data.nonce = f"0x{i:064x}"
                await provider.verify_payment(payment_data, requirement, "/api/test")
        
        analytics = provider.get_analytics()
        
        assert analytics.total_requests == 1
        assert analytics.total_paid == 3
        assert analytics.conversion_rate > 0
        assert len(analytics.top_payers) == 1
        assert analytics.top_payers[0].count == 3
        assert "/api/test" in analytics.revenue_by_endpoint
    
    @pytest.mark.asyncio
    async def test_webhook_sending(self, provider, payment_data):
        """Test webhook notification"""
        webhook_called = False
        webhook_data = None
        
        async def mock_post(url, json, timeout):
            nonlocal webhook_called, webhook_data
            webhook_called = True
            webhook_data = json
        
        config = X402Config(
            wallet_address="0x742d35Cc6634C0532925a3b844Bc9e7595f6E123",
            analytics_webhook="https://webhook.example.com",
        )
        provider = X402Provider(config)
        requirement = provider.create_payment_requirement("0.10")
        
        with patch("fast_x402.verification.verify_eip712_signature", return_value=True):
            with patch("httpx.AsyncClient.post", side_effect=mock_post):
                await provider.verify_payment(payment_data, requirement, "/api/test")
        
        # Give webhook task time to run
        await asyncio.sleep(0.1)
        
        assert webhook_called is True
        assert webhook_data["type"] == "payment_received"
        assert webhook_data["endpoint"] == "/api/test"