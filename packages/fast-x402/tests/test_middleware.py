"""Tests for FastAPI middleware"""

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
import json

from fast_x402 import x402_middleware, X402Provider, X402Config
from fast_x402.models import PaymentData


@pytest.fixture
def app():
    """Create test FastAPI app with x402 middleware"""
    app = FastAPI()
    
    # Add middleware
    app.add_middleware(
        x402_middleware,
        wallet_address="0x742d35Cc6634C0532925a3b844Bc9e7595f6E123",
        routes={
            "/paid": "0.10",
            "/premium/*": "0.50",
            "/custom": {"amount": "1.00", "scheme": "upto"},
        },
    )
    
    @app.get("/")
    async def root():
        return {"message": "Free endpoint"}
    
    @app.get("/paid")
    async def paid_endpoint(request: Request):
        return {
            "message": "Paid content",
            "payment": getattr(request.state, "x402_payment", None),
        }
    
    @app.get("/premium/data")
    async def premium_data():
        return {"data": "Premium data"}
    
    @app.get("/custom")
    async def custom_endpoint():
        return {"message": "Custom payment"}
    
    return app


@pytest.fixture
def client(app):
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def valid_payment():
    """Create valid payment data"""
    return PaymentData(
        from_address="0x1234567890abcdef1234567890abcdef12345678",
        to="0x742d35Cc6634C0532925a3b844Bc9e7595f6E123",
        value="100000",  # 0.1 USDC
        token="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        chain_id=8453,
        nonce="0x1234567890abcdef",
        valid_before=9999999999,
        signature="0xabcdef1234567890",
    )


class TestX402Middleware:
    def test_free_endpoint(self, client):
        """Test that free endpoints work without payment"""
        response = client.get("/")
        assert response.status_code == 200
        assert response.json() == {"message": "Free endpoint"}
    
    def test_paid_endpoint_without_payment(self, client):
        """Test paid endpoint returns 402 without payment"""
        response = client.get("/paid")
        assert response.status_code == 402
        
        data = response.json()
        assert "amount" in data
        assert data["amount"] == "0.10"
        assert data["recipient"] == "0x742d35Cc6634C0532925a3b844Bc9e7595f6E123"
        assert "nonce" in data
        assert "expires_at" in data
    
    def test_paid_endpoint_with_payment(self, client, valid_payment, monkeypatch):
        """Test paid endpoint with valid payment"""
        # Mock signature verification
        async def mock_verify(*args, **kwargs):
            from fast_x402.models import PaymentVerification
            return PaymentVerification(valid=True, transaction_hash="0xmockhash")
        
        monkeypatch.setattr(
            "fast_x402.provider.X402Provider.verify_payment",
            mock_verify
        )
        
        # Make request with payment
        headers = {"X-Payment": valid_payment.model_dump_json(by_alias=True)}
        response = client.get("/paid", headers=headers)
        
        assert response.status_code == 200
        assert response.headers.get("X-Payment-Confirmation") == "0xmockhash"
        
        data = response.json()
        assert data["message"] == "Paid content"
        # Payment should be attached to request state
        assert data["payment"] is not None
    
    def test_wildcard_route_matching(self, client):
        """Test wildcard route matching"""
        response = client.get("/premium/data")
        assert response.status_code == 402
        
        data = response.json()
        assert data["amount"] == "0.50"  # Premium route price
    
    def test_custom_route_config(self, client):
        """Test custom route configuration"""
        response = client.get("/custom")
        assert response.status_code == 402
        
        data = response.json()
        assert data["amount"] == "1.00"
        assert data["scheme"] == "upto"
    
    def test_invalid_payment_data(self, client):
        """Test invalid payment data handling"""
        headers = {"X-Payment": "invalid json"}
        response = client.get("/paid", headers=headers)
        
        assert response.status_code == 500
        assert "error" in response.json()
    
    def test_payment_verification_failure(self, client, valid_payment, monkeypatch):
        """Test payment verification failure"""
        from fast_x402.exceptions import InvalidPaymentError
        
        async def mock_verify(*args, **kwargs):
            raise InvalidPaymentError("Invalid signature", "INVALID_SIGNATURE")
        
        monkeypatch.setattr(
            "fast_x402.provider.X402Provider.verify_payment",
            mock_verify
        )
        
        headers = {"X-Payment": valid_payment.model_dump_json(by_alias=True)}
        response = client.get("/paid", headers=headers)
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "Invalid signature"
        assert data["code"] == "INVALID_SIGNATURE"
    
    def test_payment_callback(self, client, valid_payment, monkeypatch):
        """Test payment callback is called"""
        callback_called = False
        payment_received = None
        
        async def on_payment(payment_data):
            nonlocal callback_called, payment_received
            callback_called = True
            payment_received = payment_data
        
        # Create app with callback
        app = FastAPI()
        app.add_middleware(
            x402_middleware,
            wallet_address="0x742d35Cc6634C0532925a3b844Bc9e7595f6E123",
            routes={"/test": "0.10"},
            on_payment=on_payment,
        )
        
        @app.get("/test")
        async def test_endpoint():
            return {"status": "ok"}
        
        # Mock verification
        async def mock_verify(*args, **kwargs):
            from fast_x402.models import PaymentVerification
            return PaymentVerification(valid=True, transaction_hash="0xhash")
        
        monkeypatch.setattr(
            "fast_x402.provider.X402Provider.verify_payment",
            mock_verify
        )
        
        # Test
        client = TestClient(app)
        headers = {"X-Payment": valid_payment.model_dump_json(by_alias=True)}
        response = client.get("/test", headers=headers)
        
        assert response.status_code == 200
        assert callback_called is True
        assert payment_received is not None
    
    def test_error_callback(self, client, monkeypatch):
        """Test error callback is called"""
        error_received = None
        
        def on_error(error):
            nonlocal error_received
            error_received = error
        
        # Create app with error callback
        app = FastAPI()
        app.add_middleware(
            x402_middleware,
            wallet_address="0x742d35Cc6634C0532925a3b844Bc9e7595f6E123",
            routes={"/test": "0.10"},
            on_error=on_error,
        )
        
        @app.get("/test")
        async def test_endpoint():
            return {"status": "ok"}
        
        # Test with invalid payment
        client = TestClient(app)
        headers = {"X-Payment": "invalid"}
        response = client.get("/test", headers=headers)
        
        assert response.status_code == 500
        assert error_received is not None