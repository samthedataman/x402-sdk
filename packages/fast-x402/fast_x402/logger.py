"""Logging configuration for fast-x402"""

import logging
import sys
from typing import Optional


def setup_logger(name: str = "fast-x402", level: Optional[str] = None) -> logging.Logger:
    """Set up logger with proper formatting"""
    
    logger = logging.getLogger(name)
    
    # Don't add handlers if they already exist
    if logger.handlers:
        return logger
    
    # Set level from environment or parameter
    import os
    log_level = level or os.environ.get("FAST_X402_LOG_LEVEL", "INFO")
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Create console handler with formatting
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logger.level)
    
    # Create formatter
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(handler)
    
    return logger


# Default logger instance
logger = setup_logger()