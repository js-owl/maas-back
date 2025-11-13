"""
Logging configuration
"""
import logging

# Configure logging to reduce SQLAlchemy verbosity
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Reduce SQLAlchemy engine logging verbosity
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
logging.getLogger('sqlalchemy.pool').setLevel(logging.WARNING)
logging.getLogger('sqlalchemy.dialects').setLevel(logging.WARNING)
logging.getLogger('sqlalchemy.orm').setLevel(logging.WARNING)

# Reduce Bitrix warnings to reduce log noise (optional)
logging.getLogger('backend.bitrix').setLevel(logging.ERROR)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a module"""
    return logging.getLogger(name)

