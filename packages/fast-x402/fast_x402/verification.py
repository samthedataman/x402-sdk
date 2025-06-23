"""Payment verification utilities for fast-x402"""

import time
from typing import Dict, Any
from eth_account import Account
from eth_account.messages import encode_typed_data
from web3 import Web3

from .models import PaymentData
from .exceptions import InvalidSignatureError, PaymentExpiredError, InvalidPaymentError


def verify_eip712_signature(payment_data: PaymentData) -> bool:
    """Verify EIP-712 signature for payment authorization"""
    
    # Construct EIP-712 message
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
            "chainId": payment_data.chain_id,
            "verifyingContract": payment_data.token,
        },
        "message": {
            "from": payment_data.from_address,
            "to": payment_data.to,
            "value": int(payment_data.value),
            "validBefore": payment_data.valid_before,
            "nonce": payment_data.nonce,
        },
    }
    
    try:
        # Encode the structured data
        encoded_message = encode_typed_data(message)
        
        # Recover signer from signature
        recovered_address = Account.recover_message(
            encoded_message, 
            signature=payment_data.signature
        )
        
        # Check if recovered address matches the from address
        return recovered_address.lower() == payment_data.from_address.lower()
        
    except Exception as e:
        raise InvalidSignatureError(f"Signature verification failed: {str(e)}")


def verify_payment_requirements(
    payment_data: PaymentData,
    required_amount: str,
    required_token: str,
    required_recipient: str,
    required_chain_id: int,
    scheme: str = "exact"
) -> None:
    """Verify payment meets all requirements"""
    
    # Check expiration
    current_time = int(time.time())
    if payment_data.valid_before < current_time:
        raise PaymentExpiredError(
            f"Payment expired at {payment_data.valid_before}, current time: {current_time}"
        )
    
    # Check recipient
    if payment_data.to.lower() != required_recipient.lower():
        raise InvalidPaymentError(
            f"Expected recipient {required_recipient}, got {payment_data.to}"
        )
    
    # Check token
    if payment_data.token.lower() != required_token.lower():
        raise InvalidPaymentError(
            f"Expected token {required_token}, got {payment_data.token}", "INVALID_TOKEN"
        )
    
    # Check chain ID
    if payment_data.chain_id != required_chain_id:
        raise InvalidPaymentError(
            f"Expected chain {required_chain_id}, got {payment_data.chain_id}", "INVALID_CHAIN"
        )
    
    # Check amount based on scheme
    payment_amount = int(payment_data.value)
    required_amount_wei = Web3.to_wei(float(required_amount), "mwei")  # USDC has 6 decimals
    
    if scheme == "exact":
        if payment_amount != required_amount_wei:
            raise InvalidPaymentError(
                f"Expected exact amount {required_amount_wei}, got {payment_amount}"
            )
    elif scheme == "upto":
        if payment_amount > required_amount_wei:
            raise InvalidPaymentError(
                f"Payment amount {payment_amount} exceeds maximum {required_amount_wei}"
            )
    else:
        raise ValueError(f"Unknown payment scheme: {scheme}")


