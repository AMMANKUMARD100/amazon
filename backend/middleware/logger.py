import os
import logging
from logging.handlers import RotatingFileHandler

# Define logs directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
os.makedirs(LOGS_DIR, exist_ok=True)

# Formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def setup_logger(name, filename, level=logging.INFO):
    """Helper function to create a logger writing to a specific rotating log file."""
    log_path = os.path.join(LOGS_DIR, filename)
    handler = RotatingFileHandler(log_path, maxBytes=1024 * 1024 * 5, backupCount=5)
    handler.setFormatter(formatter)
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    # Avoid duplicate handlers if setup is called multiple times
    if not logger.handlers:
        logger.addHandler(handler)
        # Prevent logging from propagating to root logger and cluttering console
        logger.propagate = False
        
    return logger

# Initialize specialized loggers
auth_logger = setup_logger('auth', 'auth.log')
activity_logger = setup_logger('activity', 'activity.log')
mcp_logger = setup_logger('mcp', 'mcp.log')
error_logger = setup_logger('error', 'error.log', level=logging.ERROR)

def log_activity(user_id, action, details=None, ip_address=None):
    """Helper to log student activity to both database and log file."""
    from backend.database.connection import execute_query
    
    # Write to database (audit trails)
    try:
        execute_query(
            "INSERT INTO activity_logs (user_id, action, details, ip_address) VALUES (?, ?, ?, ?);",
            (user_id, action, details, ip_address),
            commit=True
        )
    except Exception as e:
        error_logger.error(f"Failed to write activity log to DB: {e}")
        
    # Write to local file
    user_str = f"User {user_id}" if user_id else "Anonymous"
    activity_logger.info(f"{user_str} - Action: {action} - Details: {details} - IP: {ip_address}")
