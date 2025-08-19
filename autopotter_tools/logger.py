import logging
import logging.handlers
import os
import sys
import time
import functools
from contextlib import contextmanager
from typing import Optional, Union
import threading

class CentralLogger:
    """
    Central logging singleton for the enhanced video generation system.
    Provides structured logging with performance tracking and automatic initialization.
    """
    
    _instance = None
    _lock = threading.Lock()
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            with self._lock:
                if not self._initialized:
                    self._logger = None
                    self._config = {}
                    self._initialized = True
    
    def initialize(self, config: dict = None):
        """
        Initialize the logger with configuration.
        If no config provided, defaults to terminal output only.
        """
        if self._logger is not None:
            return  # Already initialized
        
        with self._lock:
            if self._logger is not None:
                return  # Double-check after acquiring lock
            
            # Set default configuration
            self._config = {
                'log_level': 'INFO',
                'log_file': None,
                'log_max_size': '10MB',
                'log_backup_count': 5,
                'log_console_output': True
            }
            
            # Update with provided config
            if config:
                self._config.update(config)
            
            # Create logger
            self._logger = logging.getLogger('autopotter')
            self._logger.setLevel(getattr(logging, self._config['log_level'].upper()))
            
            # Clear any existing handlers
            self._logger.handlers.clear()
            
            # Create formatter
            formatter = logging.Formatter(
                '[%(asctime)s] %(name)s:%(levelname)s: %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            
            # Add console handler (always enabled)
            if self._config['log_console_output'] or self._config['log_file'] is None:
                console_handler = logging.StreamHandler(sys.stdout)
                console_handler.setFormatter(formatter)
                self._logger.addHandler(console_handler)
            
            # Add file handler if specified
            if self._config['log_file']:
                try:
                    # Parse max size (e.g., "10MB" -> 10 * 1024 * 1024)
                    max_size_str = self._config['log_max_size']
                    if max_size_str.endswith('MB'):
                        max_size = int(max_size_str[:-2]) * 1024 * 1024
                    elif max_size_str.endswith('KB'):
                        max_size = int(max_size_str[:-2]) * 1024
                    else:
                        max_size = int(max_size_str)
                    
                    # Ensure log directory exists
                    log_dir = os.path.dirname(self._config['log_file'])
                    if log_dir and not os.path.exists(log_dir):
                        os.makedirs(log_dir)
                    
                    # Create rotating file handler
                    file_handler = logging.handlers.RotatingFileHandler(
                        self._config['log_file'],
                        maxBytes=max_size,
                        backupCount=self._config['log_backup_count']
                    )
                    file_handler.setFormatter(formatter)
                    self._logger.addHandler(file_handler)
                    
                    self._logger.info(f"File logging enabled: {self._config['log_file']}")
                except Exception as e:
                    # Fallback to console only if file logging fails
                    self._logger.warning(f"Failed to initialize file logging: {e}. Using console only.")
            
            self._logger.info("Central logging system initialized")
    
    def get_logger(self, name: str = None) -> logging.Logger:
        """
        Get a logger instance. If no name provided, returns the root autopotter logger.
        """
        if self._logger is None:
            self.initialize()  # Initialize with defaults if not done yet
        
        if name:
            return logging.getLogger(f'autopotter.{name}')
        return self._logger
    
    def set_level(self, level: str):
        """Set the logging level for all handlers."""
        if self._logger:
            level_upper = level.upper()
            self._logger.setLevel(getattr(logging, level_upper))
            for handler in self._logger.handlers:
                handler.setLevel(getattr(logging, level_upper))
            self._logger.info(f"Log level set to {level_upper}")
    
    def performance_logger(self, operation: str):
        """
        Decorator for logging function performance.
        Usage: @logger.performance_logger("operation_name")
        """
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                logger = self.get_logger()
                
                try:
                    logger.debug(f"Starting {operation}")
                    result = func(*args, **kwargs)
                    execution_time = time.time() - start_time
                    logger.debug(f"Completed {operation} in {execution_time:.3f}s")
                    return result
                except Exception as e:
                    execution_time = time.time() - start_time
                    logger.error(f"Failed {operation} after {execution_time:.3f}s: {e}")
                    raise
            
            return wrapper
        return decorator
    
    @contextmanager
    def performance_context(self, operation: str):
        """
        Context manager for logging operation performance.
        Usage: with logger.performance_context("operation_name"):
        """
        start_time = time.time()
        logger = self.get_logger()
        
        try:
            logger.debug(f"Starting {operation}")
            yield
            execution_time = time.time() - start_time
            logger.debug(f"Completed {operation} in {execution_time:.3f}s")
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Failed {operation} after {execution_time:.3f}s: {e}")
            raise

# Global instance
_central_logger = None

def get_logger(name: str = None) -> logging.Logger:
    """
    Get a logger instance. This is the main entry point for the logging system.
    
    Args:
        name: Optional name for the logger (e.g., 'instagram_api', 'gcs_api')
    
    Returns:
        Logger instance configured according to the system configuration
    """
    global _central_logger
    if _central_logger is None:
        _central_logger = CentralLogger()
    return _central_logger.get_logger(name)

def initialize_logging(config: dict = None):
    """
    Initialize the central logging system with configuration.
    This should be called early in the application startup.
    
    Args:
        config: Optional configuration dictionary with logging settings
    """
    global _central_logger
    if _central_logger is None:
        _central_logger = CentralLogger()
    _central_logger.initialize(config)

def get_performance_logger():
    """
    Get the performance logging decorator and context manager.
    """
    global _central_logger
    if _central_logger is None:
        _central_logger = CentralLogger()
    return _central_logger
