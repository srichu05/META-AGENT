"""
Logger configuration for the Meta-Agent Math Debate System
"""

import logging
import os
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Optional
from dotenv import load_dotenv  # ✅ NEW

# ✅ NEW: Load environment variables
load_dotenv()

# ✅ NEW: Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from config import SYSTEM_CONFIG  # ✅ NEW: Import from config


def setup_logger(name: str, level: Optional[int] = None) -> logging.Logger:
    """
    Set up logger with both file and console handlers.
    
    Args:
        name: Name of the logger (typically __name__)
        level: Logging level (uses config default if None)
        
    Returns:
        Configured logger instance
    """
    
    # ✅ ENHANCED: Use config for log level if not specified
    if level is None:
        log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
        level = getattr(logging, log_level_str, logging.INFO)
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Avoid adding multiple handlers
    if logger.handlers:
        return logger
    
    # ✅ ENHANCED: Get log directory from config
    log_dir = os.path.dirname(SYSTEM_CONFIG.get("log_file_path", "./logs/app.log"))
    os.makedirs(log_dir, exist_ok=True)
    
    # ✅ ENHANCED: Create formatters with more detail
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(funcName)s() - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # ✅ ENHANCED: Console formatter with colors (if terminal supports it)
    try:
        import colorlog
        color_formatter = colorlog.ColoredFormatter(
            '%(log_color)s%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S',
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
            }
        )
        console_formatter = color_formatter
    except ImportError:
        # colorlog not available, use simple formatter
        console_formatter = simple_formatter
    
    # ✅ ENHANCED: File handler with rotation and config-based filename
    log_file = os.path.join(
        log_dir, 
        f"math_debate_system_{datetime.now().strftime('%Y%m%d')}.log"
    )
    
    try:
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)  # Always capture DEBUG in file
        file_handler.setFormatter(detailed_formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"⚠️ Warning: Could not create file handler: {str(e)}")
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # Prevent logging from propagating to root logger
    logger.propagate = False
    
    return logger


def setup_debug_logger(name: str) -> logging.Logger:
    """
    Set up a debug-level logger.
    
    Args:
        name: Name of the logger
        
    Returns:
        Logger configured for DEBUG level
    """
    return setup_logger(name, logging.DEBUG)


def setup_error_logger(name: str) -> logging.Logger:
    """
    Set up an error-only logger.
    
    Args:
        name: Name of the logger
        
    Returns:
        Logger configured for ERROR level only
    """
    return setup_logger(name, logging.ERROR)


# ✅ NEW: Add warning logger
def setup_warning_logger(name: str) -> logging.Logger:
    """
    Set up a warning-level logger.
    
    Args:
        name: Name of the logger
        
    Returns:
        Logger configured for WARNING level
    """
    return setup_logger(name, logging.WARNING)


# ✅ NEW: Add method to change log level at runtime
def set_log_level(logger: logging.Logger, level: str) -> bool:
    """
    Change the log level of a logger at runtime.
    
    Args:
        logger: Logger instance to modify
        level: New log level as string ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
        
    Returns:
        True if successful, False otherwise
    """
    try:
        level_int = getattr(logging, level.upper(), None)
        if level_int is None:
            print(f"⚠️ Invalid log level: {level}")
            return False
        
        logger.setLevel(level_int)
        # Update console handler level
        for handler in logger.handlers:
            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, RotatingFileHandler):
                handler.setLevel(level_int)
        
        logger.info(f"✅ Log level changed to {level.upper()}")
        return True
        
    except Exception as e:
        print(f"💥 Failed to set log level: {str(e)}")
        return False


# ✅ NEW: Add method to get all active loggers
def get_active_loggers() -> dict:
    """
    Get information about all active loggers.
    
    Returns:
        Dictionary with logger names and their configurations
    """
    loggers_info = {}
    
    # Get root logger
    root_logger = logging.getLogger()
    loggers_info['root'] = {
        'level': logging.getLevelName(root_logger.level),
        'handlers': len(root_logger.handlers)
    }
    
    # Get all named loggers
    for name in logging.Logger.manager.loggerDict:
        logger = logging.getLogger(name)
        if logger.handlers:  # Only include loggers with handlers
            loggers_info[name] = {
                'level': logging.getLevelName(logger.level),
                'handlers': len(logger.handlers)
            }
    
    return loggers_info


# ✅ NEW: Add method to clear all handlers from a logger
def clear_logger_handlers(logger: logging.Logger):
    """
    Clear all handlers from a logger.
    
    Args:
        logger: Logger instance to clear
    """
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)


# Configure root logger to avoid spam from libraries
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)  # ✅ NEW
logging.getLogger("cohere").setLevel(logging.WARNING)  # ✅ NEW
logging.getLogger("anthropic").setLevel(logging.WARNING)  # ✅ NEW

# ✅ NEW: Configure logging based on environment
if os.getenv("DEBUG", "False").lower() in ("true", "1", "yes"):
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.INFO)
