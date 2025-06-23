"""Tests for payment verification"""

import pytest
import time
from unittest.mock import patch, Mock
from eth_account import Account
from eth_account.messages import encode_structured_data

from fast_x402.verification import (
    verify_eip712_signature,
    verify_payment_requirements,
)
from fast_x402.models import PaymentData
from fast_x402.exceptions import (
    InvalidSignatureError,
    PaymentExpiredError,
    InvalidRecipientError,
    InvalidAmountError,
)


@pytest.fixture
def test_account():
    """Create a test account"""
    return Account.create()


@pytest.fixture
def valid_payment_data(test_account):
    """Create valid payment data with proper signature"""
    # Payment parameters
    from_address = test_account.address
    to_address = "0x742d35Cc6634C0532925a3b844Bc9e7595f6E123"
    value = "100000"  # 0.1 USDC
    token = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
    chain_id = 8453
    nonce = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
    valid_before = int(time.time()) + 300
    
    # Create EIP-712 message
    message = {
        "types": {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"},
                {"name": "verifyingContract", "type": "address"},
            ],
            "TransferWithAuthorization": [
                {"name": "from", "type": "address"},
                {"name": "to", "type": "address"},
                {"name": "value", "type": "uint256"},
                {"name": "validBefore", "type": "uint256"},
                {"name": "nonce", "type": "bytes32"},
            ],
        },
        "primaryType": "TransferWithAuthorization",
        "domain": {
            "name": "USDC",
            "version": "2",
            "chainId": chain_id,
            "verifyingContract": token,
        },
        "message": {
            "from": from_address,
            "to": to_address,
            "value": int(value),
            "validBefore": valid_before,
            "nonce": nonce,
        },
    }
    
    # Sign the message
    encoded_message = encode_structured_data(message)
    signed = test_account.sign_message(encoded_message)
    
    return PaymentData(
        from_address=from_address,
        to=to_address,
        value=value,
        token=token,
        chain_id=chain_id,
        nonce=nonce,
        valid_before=valid_before,
        signature=signed.signature.hex(),
    )


class TestEIP712Verification:
    def test_valid_signature(self, valid_payment_data):
        """Test verification of valid EIP-712 signature"""
        result = verify_eip712_signature(valid_payment_data)
        assert result is True
    
    def test_invalid_signature(self, valid_payment_data):
        """Test verification fails with invalid signature"""
        valid_payment_data.signature = "0x" + "00" * 65  # Invalid signature
        
        with pytest.raises(InvalidSignatureError):
            verify_eip712_signature(valid_payment_data)
    
    def test_wrong_signer(self, valid_payment_data):
        """Test verification fails when signer doesn't match from address"""
        # Change from address to different address
        valid_payment_data.from_address = "0x0000000000000000000000000000000000000001"
        
        result = verify_eip712_signature(valid_payment_data)
        assert result is False
    
    def test_signature_case_insensitive(self, valid_payment_data):
        """Test signature verification is case insensitive"""
        # Convert addresses to different case
        valid_payment_data.from_address = valid_payment_data.from_address.upper()
        
        result = verify_eip712_signature(valid_payment_data)
        assert result is True


class TestPaymentRequirements:
    def test_valid_payment(self):
        """Test valid payment passes all checks"""
        payment = PaymentData(
            from_address="0x1234567890abcdef1234567890abcdef12345678",
            to="0x742d35Cc6634C0532925a3b844Bc9e7595f6E123",
            value="100000",  # 0.1 USDC (6 decimals)
            token="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            chain_id=8453,
            nonce="0xabc",
            valid_before=int(time.time()) + 300,
            signature="0xsig",
        )
        
        # Should not raise any exception
        verify_payment_requirements(
            payment,
            required_amount="0.1",
            required_token="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            required_recipient="0x742d35Cc6634C0532925a3b844Bc9e7595f6E123",
            required_chain_id=8453,
            scheme="exact"
        )
    
    def test_expired_payment(self):
        """Test expired payment is rejected"""
        payment = PaymentData(
            from_address="0x1234567890abcdef1234567890abcdef12345678",
            to="0x742d35Cc6634C0532925a3b844Bc9e7595f6E123",
            value="100000",
            token="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            chain_id=8453,
            nonce="0xabc",
            valid_before=int(time.time()) - 100,  # Expired
            signature="0xsig",
        )
        
        with pytest.raises(PaymentExpiredError) as exc_info:
            verify_payment_requirements(
                payment,
                required_amount="0.1",
                required_token="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
                required_recipient="0x742d35Cc6634C0532925a3b844Bc9e7595f6E123",
                required_chain_id=8453,
            )
        
        assert "Payment expired" in str(exc_info.value)
    
    def test_wrong_recipient(self):
        """Test payment to wrong recipient is rejected"""
        payment = PaymentData(
            from_address="0x1234567890abcdef1234567890abcdef12345678",
            to="0x0000000000000000000000000000000000000001",  # Wrong recipient
            value="100000",
            token="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            chain_id=8453,
            nonce="0xabc",
            valid_before=int(time.time()) + 300,
            signature="0xsig",
        )
        
        with pytest.raises(InvalidRecipientError) as exc_info:
            verify_payment_requirements(
                payment,
                required_amount="0.1",
                required_token="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
                required_recipient="0x742d35Cc6634C0532925a3b844Bc9e7595f6E123",
                required_chain_id=8453,
            )
        
        assert "Expected recipient" in str(exc_info.value)
    
    def test_exact_amount_mismatch(self):
        """Test exact amount scheme requires exact match"""
        payment = PaymentData(
            from_address="0x1234567890abcdef1234567890abcdef12345678",
            to="0x742d35Cc6634C0532925a3b844Bc9e7595f6E123",
            value="50000",  # 0.05 USDC, but 0.1 required
            token="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            chain_id=8453,
            nonce="0xabc",
            valid_before=int(time.time()) + 300,
            signature="0xsig",
        )
        
        with pytest.raises(InvalidAmountError) as exc_info:
            verify_payment_requirements(
                payment,
                required_amount="0.1",
                required_token="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
                required_recipient="0x742d35Cc6634C0532925a3b844Bc9e7595f6E123",
                required_chain_id=8453,
                scheme="exact"
            )
        
        assert "Expected exact amount" in str(exc_info.value)
    
    def test_upto_amount_within_limit(self):
        """Test upto scheme allows amounts up to limit"""
        payment = PaymentData(
            from_address="0x1234567890abcdef1234567890abcdef12345678",
            to="0x742d35Cc6634C0532925a3b844Bc9e7595f6E123",
            value="50000",  # 0.05 USDC, under 0.1 limit
            token="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            chain_id=8453,
            nonce="0xabc",
            valid_before=int(time.time()) + 300,
            signature="0xsig",
        )
        
        # Should not raise exception
        verify_payment_requirements(
            payment,
            required_amount="0.1",
            required_token="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            required_recipient="0x742d35Cc6634C0532925a3b844Bc9e7595f6E123",
            required_chain_id=8453,
            scheme="upto"
        )
    
    def test_upto_amount_exceeds_limit(self):
        """Test upto scheme rejects amounts over limit"""
        payment = PaymentData(
            from_address="0x1234567890abcdef1234567890abcdef12345678",
            to="0x742d35Cc6634C0532925a3b844Bc9e7595f6E123",
            value="200000",  # 0.2 USDC, over 0.1 limit
            token="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            chain_id=8453,
            nonce="0xabc",
            valid_before=int(time.time()) + 300,
            signature="0xsig",
        )
        
        with pytest.raises(InvalidAmountError) as exc_info:
            verify_payment_requirements(
                payment,
                required_amount="0.1",
                required_token="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
                required_recipient="0x742d35Cc6634C0532925a3b844Bc9e7595f6E123",
                required_chain_id=8453,
                scheme="upto"
            )
        
        assert "exceeds maximum" in str(exc_info.value)