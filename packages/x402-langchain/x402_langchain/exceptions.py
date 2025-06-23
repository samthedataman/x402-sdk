"""Custom exceptions for x402-langchain"""


class X402Error(Exception):
    """Base exception for x402-langchain errors"""
    pass


class PaymentError(X402Error):
    """Error during payment processing"""
    pass


class InsufficientFundsError(PaymentError):
    """Agent has insufficient funds"""
    pass


class PaymentDeniedError(PaymentError):
    """Payment was denied by approval logic"""
    pass


class SpendingLimitError(PaymentError):
    """Payment would exceed spending limits"""
    pass


class DomainNotAllowedError(PaymentError):
    """Payment to this domain is not allowed"""
    pass


class PaymentTimeoutError(PaymentError):
    """Payment request timed out"""
    pass


class InvalidPaymentRequirementError(X402Error):
    """Invalid payment requirement from server"""
    pass