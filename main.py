# main.py - FIXED VERSION
"""
Salesforce Report Exporter
Entry Point - Shows login first, then main application

Usage:
    python main.py
"""

import customtkinter as ctk
import sys
from typing import Optional, Dict


class AppLauncher:
    """
    Application launcher that manages the login → main app flow.
    
    KEY FIX: Uses a single persistent event loop with proper window transitions.
    """
    
    def __init__(self):
        self.session_info: Optional[Dict] = None
        self.login_window = None
        self.main_app = None
        self.root = None  # ← NEW: Persistent root window
        
        # Set theme early
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
    
    def start(self):
        """
        Start the application with a single persistent event loop.
        
        KEY FIX: Creates a hidden root window that persists throughout app lifecycle.
        """
        # Create persistent root window (hidden)
        self.root = ctk.CTk()
        self.root.withdraw()  # Hide it
        
        # Show login window
        self._show_login_window()
        
        # Start the SINGLE event loop (never exits until app closes)
        self.root.mainloop()
    
    def _show_login_window(self):
        """Show the login window as a Toplevel"""
        from login_window import LoginWindow
        
        # Clean up previous login window if it exists
        if self.login_window:
            try:
                self.login_window.destroy()
            except:
                pass
            self.login_window = None
        
        # Create login as Toplevel (not standalone)
        self.login_window = LoginWindow(
            master=self.root,  # ← NEW: Parent to root
            on_login_success=self._on_login_success,
            on_login_cancelled=self._on_login_cancelled
        )
    
    def _on_login_success(self, session_info: Dict):
        """
        Called when login succeeds.
        
        KEY FIX: Destroys login window and creates main app WITHOUT exiting event loop.
        """
        self.session_info = session_info
        
        # Destroy login window (but event loop continues!)
        if self.login_window:
            try:
                self.login_window.destroy()
            except:
                pass
            self.login_window = None
        
        # Create main app AFTER login window is fully destroyed
        # Small delay ensures clean transition
        self.root.after(100, self._show_main_app)
    
    def _on_login_cancelled(self):
        """
        Called when user cancels/closes login window.
        Exit the application cleanly.
        """
        if self.login_window:
            try:
                self.login_window.destroy()
            except:
                pass
        
        # Exit the app
        if self.root:
            self.root.quit()
            self.root.destroy()
        
        sys.exit(0)
    
    def _show_main_app(self):
        """Create and show the main application window as Toplevel"""
        from main_app import SalesforceExporterApp
        
        # Clean up previous main app if it exists
        if self.main_app:
            try:
                self.main_app.destroy()
            except:
                pass
            self.main_app = None
        
        # Create main app as Toplevel (not standalone)
        self.main_app = SalesforceExporterApp(
            master=self.root,
            session_info=self.session_info,
            on_logout=self._on_logout
        )
    
    def _on_logout(self):
        """
        Called when user logs out from main app.
        
        KEY FIX: Destroys main app and shows login WITHOUT creating new event loop.
        """
        # Destroy main app
        if self.main_app:
            try:
                self.main_app.destroy()
            except:
                pass
            self.main_app = None
        
        # Reset session
        self.session_info = None
        
        # Show login again (event loop continues!)
        self.root.after(100, self._show_login_window)


def main():
    """Main entry point"""
    try:
        launcher = AppLauncher()
        launcher.start()
    except KeyboardInterrupt:
        print("\n👋 Application closed by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()