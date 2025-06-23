"""Custom exceptions for fast-x402"""


class X402Error(Exception):
    """Base exception for x402 errors"""
    def __init__(self, message: str, code: str, status_code: int = 402):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)


class PaymentRequiredError(X402Error):
    """Raised when payment is required but not provided"""
    def __init__(self, message: str = "Payment required", code: str = "PAYMENT_REQUIRED"):
        super().__init__(message, code, 402)


class InvalidPaymentError(X402Error):
    """Raised when payment is invalid"""
    def __init__(self, message: str, code: str = "INVALID_PAYMENT"):
        super().__init__(message, code, 400)


class PaymentExpiredError(InvalidPaymentError):
    """Raised when payment has expired"""
    def __init__(self, message: str = "Payment expired"):
        super().__init__(message, "PAYMENT_EXPIRED")


class InvalidSignatureError(InvalidPaymentError):
    """Raised when payment signature is invalid"""
    def __init__(self, message: str = "Invalid signature"):
        super().__init__(message, "INVALID_SIGNATURE")


class InvalidAmountError(InvalidPaymentError):
    """Raised when payment amount is invalid"""
    def __init__(self, message: str = "Invalid amount"):
        super().__init__(message, "INVALID_AMOUNT")


class InvalidRecipientError(InvalidPaymentError):
    """Raised when payment recipient is invalid"""
    def __init__(self, message: str = "Invalid recipient"):
        super().__init__(message, "INVALID_RECIPIENT")