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