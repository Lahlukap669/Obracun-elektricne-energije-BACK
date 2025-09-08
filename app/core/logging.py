import sys
from pathlib import Path
from loguru import logger
from .config import settings
from datetime import datetime

def setup_logging():
    # Remove default handler
    logger.remove()
    
    # Console handler
    logger.add(
        sys.stdout,
        colorize=True,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO" if not settings.DEBUG else "DEBUG",
    )
    
    # Daily rotating file handler
    log_path = Path(settings.LOG_DIR) / "{time:YYYY-MM-DD}.log"
    logger.add(
        log_path,
        rotation="00:00",
        retention="30 days",
        compression="zip",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",
        enqueue=True,
    )
    
    # Error file handler
    error_log_path = Path(settings.LOG_DIR) / "errors_{time:YYYY-MM-DD}.log"
    logger.add(
        error_log_path,
        rotation="00:00",
        retention="90 days",
        compression="zip",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="ERROR",
        enqueue=True,
    )
    
    return logger

# Initialize logging
app_logger = setup_logging()
