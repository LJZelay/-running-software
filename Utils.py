"""
CSE 4504 Team Project - Utility Module
Shared utilities used across features
"""

import logging
from typing import Any
from datetime import datetime


def setup_logger(name: str = 'CSE4504'):
    """Setup and configure logger"""
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # File handler (optional)
        file_handler = logging.FileHandler('cse4504_project.log')
        file_handler.setLevel(logging.DEBUG)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)
        
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
    
    return logger


def validate_input(value: Any, expected_type: type, min_len: int = None, max_len: int = None):
    """
    Validate input parameters
    
    Args:
        value: Value to validate
        expected_type: Expected type
        min_len: Minimum length (for strings/lists)
        max_len: Maximum length (for strings/lists)
    
    Raises:
        ValueError: If validation fails
    """
    if not isinstance(value, expected_type):
        raise ValueError(f"Expected {expected_type.__name__}, got {type(value).__name__}")
    
    if expected_type == str and value.strip() == "":
        raise ValueError("Input string cannot be empty")
    
    if min_len is not None:
        if hasattr(value, '__len__') and len(value) < min_len:
            raise ValueError(f"Input must be at least {min_len} characters/items")
    
    if max_len is not None:
        if hasattr(value, '__len__') and len(value) > max_len:
            raise ValueError(f"Input must not exceed {max_len} characters/items")


def format_output(data: Any, format_type: str = 'string') -> str:
    """
    Format output data
    
    Args:
        data: Data to format
        format_type: 'string', 'json', 'csv', 'table'
    
    Returns:
        Formatted string
    """
    if format_type == 'string':
        return str(data)
    elif format_type == 'json':
        import json
        return json.dumps(data, indent=2, default=str)
    elif format_type == 'table':
        # Simple table formatting
        if isinstance(data, dict):
            rows = [f"{key}: {value}" for key, value in data.items()]
            return '\n'.join(rows)
        elif isinstance(data, list):
            return '\n'.join(str(item) for item in data)
        else:
            return str(data)
    else:
        return str(data)


def get_timestamp() -> str:
    """Get current timestamp in readable format"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def calculate_execution_time(func):
    """Decorator to calculate function execution time"""
    def wrapper(*args, **kwargs):
        start_time = datetime.now()
        result = func(*args, **kwargs)
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        logger.info(f"{func.__name__} executed in {execution_time:.4f} seconds")
        return result
    return wrapper


# Initialize logger
logger = setup_logger()