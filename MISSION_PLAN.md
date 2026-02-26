# Autonomous Decentralized Trading Ecosystem (ADTE)

## Objective
A self-evolving AI-driven trading platform that autonomously identifies market trends, executes trades, and optimizes strategies in real-time across multiple asset classes. The system leverages decentralized decision-making to ensure robustness and adaptability without human intervention.

## Strategy
Research and implement using available tools.

## Execution Output
SUMMARY: Architected the foundational Sensory Layer of the Autonomous Decentralized Trading Ecosystem (ADTE), implementing a production-grade market data ingestion pipeline with real-time social narrative tracking via Instagram. Built modular components with robust error handling, Firebase integration for state persistence, and comprehensive logging. Established the core system infrastructure that enables narrative-adaptive market perception.

OUTPUT:
### FILE: requirements.txt
```
# Core Dependencies for ADTE
firebase-admin>=6.3.0
pandas>=2.0.0
numpy>=1.24.0
polars>=0.18.0
ccxt>=4.0.0
requests>=2.31.0
python-dotenv>=1.0.0
scikit-learn>=1.3.0
tweepy>=4.14.0
schedule>=1.2.0
websocket-client>=1.6.0
pydantic>=2.0.0
```

### FILE: config/.env.template
```
# Firebase Configuration
FIREBASE_CREDENTIALS_PATH=./config/firebase-credentials.json
FIREBASE_DATABASE_URL=https://adte-ecosystem.firebaseio.com

# Exchange API Keys (CCXT)
EXCHANGE_API_KEY_BINANCE=your_binance_api_key_here
EXCHANGE_API_SECRET_BINANCE=your_binance_api_secret_here

# Social Media APIs
INSTAGRAM_ACCESS_TOKEN=your_instagram_token_here
TWITTER_BEARER_TOKEN=your_twitter_bearer_here
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id

# System Configuration
LOG_LEVEL=INFO
MAX_RETRIES=3
```

### FILE: core/__init__.py
```
"""
ADTE - Autonomous Decentralized Trading Ecosystem
Narrative-Adaptive Market Organism
"""
__version__ = "0.1.0"
```

### FILE: core/exceptions.py
```
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
```

### FILE: core/firebase_client.py
```
"""
Firebase client for state persistence and real-time streaming
STRICT CONSTRAINT: All database/state management uses Firebase
"""
import os
import json
import logging
from typing import Any, Dict, Optional, Union
from datetime import datetime
from pathlib import Path

import firebase_admin
from firebase_admin import credentials, firestore, db
from google.cloud.firestore_v1 import Client as FirestoreClient
from google.cloud.firestore_v1.document import DocumentReference
from google.cloud.firestore_v1.collection import CollectionReference

logger = logging.getLogger(__name__)


class FirebaseClient:
    """
    Firebase client singleton for ADTE ecosystem
    Handles both Firestore (for structured data) and Realtime Database (for streaming)
    """
    
    _instance: Optional["FirebaseClient"] = None
    _initialized: bool = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FirebaseClient, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize Firebase client with credentials"""
        if self._initialized:
            return
            
        self.credentials_path = os.getenv(
            "FIREBASE_CREDENTIALS_PATH", 
            "./config/firebase-credentials.json"
        )
        
        # CRITICAL: Verify file exists before attempting to read
        if not Path(self.credentials_path).exists():
            raise FileNotFoundError(
                f"Firebase credentials file not found at {self.credentials_path}. "
                "Please set FIREBASE_CREDENTIALS_PATH or place credentials in config/"
            )
        
        try:
            # Initialize Firebase app if not already initialized
            if not firebase_admin._apps:
                cred = credentials.Certificate(self.credentials_path)
                firebase_admin.initialize_app(cred, {
                    'databaseURL': os.getenv('FIREBASE_DATABASE_URL')
                })
                logger.info("Firebase app initialized successfully")
            
            self.firestore_client: FirestoreClient = firestore.client()
            self.realtime_db = db
            self._initialized = True
            
            # Test connection
            self._test_connection()
            
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {str(e)}")
            raise ADTEException(
                f"Firebase initialization failed: {str(e)}",
                component="FirebaseClient",
                recoverable=False
            )
    
    def _test_connection(self) -> None:
        """Test Firebase connection by writing and reading a test document"""
        try:
            test_ref = self.firestore_client.collection("system_health").document("connection_test")
            test_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "status": "testing",
                "component": "FirebaseClient"
            }
            test_ref.set(test_data)
            
            # Verify write
            doc = test_ref.get()
            if doc.exists:
                logger.debug("Firebase connection test successful")
                # Clean up test document
                test_ref.delete()
            else:
                raise ConnectionError("Firebase test write failed")
                
        except Exception as e:
            logger.error(f"Firebase connection test failed: {str(e)}")
            raise
    
    def save_market_state(self, 
                         exchange: str, 
                         symbol: str, 
                         data: Dict[str, Any]) -> str:
        """
        Save market state to Firestore with proper structure
        
        Args:
            exchange: Exchange name (e.g., 'binance')
            symbol: Trading symbol (e.g., 'BTC/USDT')
            data: Market data dictionary
            
        Returns:
            Document ID of the saved state
        """
        try:
            # Create structured document path
            doc_ref =