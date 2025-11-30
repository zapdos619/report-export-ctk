# session_manager.py - NEW FILE
"""
Session manager for handling Salesforce session lifecycle.
Tracks session validity and handles automatic refresh.
"""

import threading
import time
from typing import Optional, Dict, Callable
from salesforce_auth import SalesforceAuth, SalesforceAuthError


class SessionManager:
    """
    Manages Salesforce session lifecycle with automatic refresh.
    
    Features:
    - Tracks session age
    - Verifies session validity before operations
    - Auto-refreshes expired sessions
    - Thread-safe
    """
    
    # Salesforce sessions typically expire after 2 hours of inactivity
    # We'll proactively refresh after 1.5 hours to be safe
    SESSION_REFRESH_THRESHOLD = 90 * 60  # 90 minutes in seconds
    
    def __init__(self):
        self.session_info: Optional[Dict] = None
        self.credentials: Optional[Dict] = None  # Store for refresh
        self.last_refresh_time: float = 0
        self.lock = threading.RLock()
        
        # Callbacks
        self.on_session_refreshed: Optional[Callable] = None
        self.on_session_expired: Optional[Callable] = None
    
    def initialize(
        self,
        session_info: Dict,
        username: str,
        password: str,
        security_token: str = "",
        domain: str = "login"
    ):
        """
        Initialize session manager with login credentials.
        
        Args:
            session_info: Initial session info from login
            username: Username for refresh
            password: Password for refresh
            security_token: Security token for refresh
            domain: Login domain for refresh
        """
        with self.lock:
            self.session_info = session_info.copy()
            self.credentials = {
                "username": username,
                "password": password,
                "security_token": security_token,
                "domain": domain
            }
            self.last_refresh_time = time.time()
    
    def get_session_id(self) -> Optional[str]:
        """Get current session ID (thread-safe)."""
        with self.lock:
            if not self.session_info:
                return None
            return self.session_info.get("session_id")
    
    def get_session_info(self) -> Optional[Dict]:
        """Get current session info (thread-safe)."""
        with self.lock:
            if not self.session_info:
                return None
            return self.session_info.copy()
    
    def is_session_old(self) -> bool:
        """Check if session is approaching expiration time."""
        with self.lock:
            if not self.session_info:
                return True
            
            age = time.time() - self.last_refresh_time
            return age > self.SESSION_REFRESH_THRESHOLD
    
    def verify_and_refresh_if_needed(self) -> bool:
        """
        Verify current session and refresh if needed.
        
        Returns:
            True if session is valid (or was refreshed), False if refresh failed
        """
        with self.lock:
            if not self.session_info or not self.credentials:
                return False
            
            # Check age first (cheaper than API call)
            if not self.is_session_old():
                return True  # Still young, no need to verify
            
            # Session is old, verify it's still valid
            auth = SalesforceAuth()
            session_id = self.session_info.get("session_id", "")
            instance_url = self.session_info.get("instance_url", "")
            
            if auth.verify_session(session_id, instance_url):
                # Session still valid, just reset timer
                self.last_refresh_time = time.time()
                return True
            
            # Session expired, refresh it
            return self._refresh_session()
    
    def force_refresh(self) -> bool:
        """
        Force a session refresh (re-login).
        
        Returns:
            True if refresh succeeded, False otherwise
        """
        with self.lock:
            return self._refresh_session()
    
    def _refresh_session(self) -> bool:
        """
        Internal method to refresh session (assumes lock held).
        
        Returns:
            True if refresh succeeded, False otherwise
        """
        if not self.credentials:
            print("❌ No credentials stored for refresh")
            if self.on_session_expired:
                try:
                    self.on_session_expired()
                except:
                    pass
            return False
        
        try:
            print("🔄 Refreshing Salesforce session...")
            
            auth = SalesforceAuth()
            new_session_info = auth.refresh_session_soap(
                username=self.credentials["username"],
                password=self.credentials["password"],
                security_token=self.credentials["security_token"],
                domain=self.credentials["domain"]
            )
            
            # Update session info
            self.session_info = new_session_info
            self.last_refresh_time = time.time()
            
            print(f"✅ Session refreshed successfully")
            
            # Notify callback
            if self.on_session_refreshed:
                try:
                    self.on_session_refreshed(new_session_info)
                except Exception as e:
                    print(f"⚠️ Error in refresh callback: {e}")
            
            return True
            
        except SalesforceAuthError as e:
            print(f"❌ Session refresh failed: {e}")
            
            # Notify callback
            if self.on_session_expired:
                try:
                    self.on_session_expired()
                except Exception as e:
                    print(f"⚠️ Error in expired callback: {e}")
            
            return False
        except Exception as e:
            print(f"❌ Unexpected error during session refresh: {e}")
            return False
    
    def clear(self):
        """Clear session and credentials (logout)."""
        with self.lock:
            self.session_info = None
            self.credentials = None
            self.last_refresh_time = 0