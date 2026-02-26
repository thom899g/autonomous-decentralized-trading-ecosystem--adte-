"""
Custom exceptions for the ADTE ecosystem
"""
from typing import Optional


class ADTEException(Exception):
    """Base exception for all ADTE errors"""
    
    def __init__(self, message: str, component: str = "Unknown", 
                 recoverable: bool = False):
        self.message = message
        self.component = component
        self.recoverable = recoverable
        super().__init__(message)


class DataSourceException(ADTEException):
    """Exceptions related to data sources"""
    pass


class ExchangeConnectionException(DataSourceException):
    """Failed to connect to exchange"""
    pass


class RateLimitException(ExchangeConnectionException):
    """Exchange rate limit exceeded"""
    
    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(message, component="ExchangeAPI", recoverable=True)
        self.retry_after = retry_after


class SocialMediaException(DataSourceException):
    """Social media API failures"""
    pass


class NarrativeProcessingException(ADTEException):
    """Failed to process market narratives"""
    pass


class TradeExecutionException(ADTEException):
    """Trade execution failures"""
    
    def __init__(self, message: str, order_id: Optional[str] = None):
        super().__init__(message, component="TradeExecutor")
        self.order_id = order_id