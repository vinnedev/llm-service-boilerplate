"""
Logger Service - Centralized logging configuration.
"""
import logging
import sys
from typing import Optional


# Configure root logger
def setup_logging(level: int = logging.INFO) -> None:
    """Setup root logging configuration."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ]
    )


def get_logger(name: str, level: Optional[int] = None) -> logging.Logger:
    """
    Get a logger instance with the given name.
    
    Args:
        name: Logger name (usually __name__ or module path)
        level: Optional log level override
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    if level is not None:
        logger.setLevel(level)
    
    return logger


# Setup logging on module import
setup_logging()
