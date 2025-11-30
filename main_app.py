# main_app.py - REDESIGNED VERSION
# Salesforce Report Exporter with Tree View and Dual-Panel Selection

# main_app.py - Complete imports section (lines 1-20)

import customtkinter as ctk
import threading
import queue
import os
import subprocess
import platform
import datetime
import time
from pathlib import Path  # ✅ ADD THIS
from tkinter import filedialog, messagebox, ttk
from typing import Optional, List, Dict, Any, Callable
from login_window import LoginWindow
from exporter import SalesforceReportExporter
from virtual_tree import VirtualTreeView
from checkpoint import ExportCheckpoint  # ✅ ADD THIS
from session_manager import SessionManager  # ✅ ADD THIS

class ExportProgressTracker:
    """
    Track export progress with ETA and speed calculation.
    """
    
    def __init__(self):
        self.start_time = None
        self.completed = 0
        self.total = 0
        self.last_update_time = None
        self.last_completed = 0
        self.speed_samples = []  # Rolling average of speed
        self.max_samples = 10
    
    def start(self, total: int):
        """Start tracking progress"""
        self.start_time = time.time()
        self.last_update_time = self.start_time
        self.completed = 0
        self.total = total
        self.last_completed = 0
        self.speed_samples = []
    
    def update(self, completed: int):
        """Update progress"""
        current_time = time.time()
        
        if self.last_update_time:
            time_delta = current_time - self.last_update_time
            if time_delta > 0:
                # Calculate instant speed
                items_delta = completed - self.last_completed
                instant_speed = items_delta / time_delta
                
                # Add to rolling average
                self.speed_samples.append(instant_speed)
                if len(self.speed_samples) > self.max_samples:
                    self.speed_samples.pop(0)
        
        self.completed = completed
        self.last_update_time = current_time
        self.last_completed = completed
    
    def get_speed(self) -> float:
        """Get current speed (reports/second)"""
        if not self.speed_samples:
            return 0.0
        return sum(self.speed_samples) / len(self.speed_samples)
    
    def get_eta_seconds(self) -> float:
        """Get estimated time remaining in seconds"""
        speed = self.get_speed()
        if speed <= 0:
            return 0.0
        
        remaining = self.total - self.completed
        return remaining / speed
    
    def get_elapsed_seconds(self) -> float:
        """Get elapsed time in seconds"""
        if not self.start_time:
            return 0.0
        return time.time() - self.start_time
    
    def format_time(self, seconds: float) -> str:
        """Format seconds into human-readable time"""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        else:
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            return f"{hours}h {minutes}m"
    
    def get_progress_text(self) -> str:
        """Get formatted progress text with ETA and speed"""
        if self.total == 0:
            return "Ready to export"
        
        percentage = int((self.completed / self.total) * 100)
        speed = self.get_speed()
        eta_seconds = self.get_eta_seconds()
        
        text = f"Exporting: {self.completed}/{self.total} reports ({percentage}%)"
        
        if speed > 0:
            text += f" • {speed:.1f} reports/sec"
        
        if eta_seconds > 0 and self.completed < self.total:
            eta_formatted = self.format_time(eta_seconds)
            text += f" • ETA: {eta_formatted}"
        
        return text
    
    def get_completion_text(self) -> str:
        """Get formatted completion text with statistics"""
        elapsed = self.get_elapsed_seconds()
        elapsed_formatted = self.format_time(elapsed)
        
        avg_speed = self.completed / elapsed if elapsed > 0 else 0
        
        text = f"✅ Completed {self.completed}/{self.total} reports in {elapsed_formatted}"
        
        if avg_speed > 0:
            text += f" (avg: {avg_speed:.1f} reports/sec)"
        
        return text

class SalesforceExporterApp(ctk.CTkToplevel):
    """
    Main application window for Salesforce Report Exporter.
    Redesigned with folder/report tree view and dual-panel selection.
    """
    
    # main_app.py - Complete __init__ method (replaces existing one around line 40-180)

    def __init__(self, master, session_info: Dict, on_logout: Optional[Callable] = None):
        """Initialize with improved state management"""
        super().__init__(master)
        
        # Store session info and logout callback
        self.session_info = session_info
        self.on_logout_callback = on_logout
        
        # ✅ CRITICAL: Initialize ALL state flags FIRST (before any other code runs)
        # This prevents AttributeError when window configure events fire early
        self.is_exporting = False  # ← MUST be initialized early
        self.is_loading = False    # ← MUST be initialized early
        self._export_state = "idle"  # ← NEW: Single state variable
        self._showing_dialog = False  # ← Dialog flag
        
        # ✅ NEW: Search results cache
        self.search_cache: Dict[str, Dict] = {}  # {keyword: {folders, reports_by_folder}}
        self.search_cache_max_size = 10  # Keep last 10 searches
        
        # Thread Safety - Initialize locks early
        self.data_lock = threading.RLock()
        self.ui_lock = threading.RLock()
        self.state_lock = threading.RLock()  # ← NEW: Dedicated state lock
        
        # Export control
        self.export_cancel_event = threading.Event()
        
        # Window setup (after basic state init)
        self.title("Salesforce Report Exporter")
        self.geometry("1200x800")
        self.grab_set()
        
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # UI State Management
        self.ui_state = "idle"
        self.pending_ui_operations = []
        
        # Session data
        self.output_zip_path: Optional[str] = None
        self.available_folders: List[Dict] = []
        self.available_reports: List[Dict] = []
        self.reports_by_folder: Dict[str, List[Dict]] = {}
        
        # Selection tracking
        self.selected_items: Dict[str, Dict] = {}
        self.search_timer = None
        
        # ✅ NEW: Virtual tree view instance
        self.virtual_tree: Optional[VirtualTreeView] = None
        self.tree_items: Dict[str, Dict] = {}  # Keep for compatibility
        
        # ✅ NEW: Checkpoint support
        self.checkpoint_path = None
        self.pending_checkpoint = None  # Stores detected checkpoint info
        self.resume_mode = False
        
        # Progress tracker
        self.progress_tracker = ExportProgressTracker()
        
        # Queue for thread-safe UI updates
        self.update_queue = queue.Queue()
        
        # Window configuration tracking (initialize before binding)
        self._configure_timer = None
        self._last_window_geometry = None
        self._last_export_state = None
        
        # ✅ NEW: Initialize session manager with credentials
        self.session_manager = SessionManager()
        
        # Extract credentials from session_info (added by login_window)
        credentials = session_info.get("credentials", {})
        if credentials:
            self.session_manager.initialize(
                session_info=session_info,
                username=credentials.get("username", ""),
                password=credentials.get("password", ""),
                security_token=credentials.get("security_token", ""),
                domain=credentials.get("domain", "login")
            )
            
            # Setup callbacks
            self.session_manager.on_session_refreshed = self._on_session_refreshed
            self.session_manager.on_session_expired = self._on_session_expired
            
            print("✅ Session manager initialized")
        else:
            print("⚠️ No credentials provided - session refresh disabled")
        
        # Setup UI
        self._setup_ui()
        
        # Center window on screen
        self.after(100, self._center_window)
        
        # Start queue processor
        self._process_queue()
        
        # Bind window close event
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        # Keyboard shortcuts
        self.unbind('<Control-e>')
        self.unbind('<Escape>')
        self.bind('<Control-e>', lambda e: self._start_export_safe())
        self.bind('<Escape>', lambda e: self._cancel_export_safe())
        
        # Window configuration tracking (bind AFTER attributes are initialized)
        self.bind('<Configure>', self._on_window_configure)
        
        # Auto-load data after UI is ready
        self.after(500, self._show_welcome_message)
        
        # ✅ NEW: Start emergency reset monitor
        self.after(5000, self._emergency_reset_if_stuck)
        

    # main_app.py - Add these NEW methods after __init__ (around line 200)

    def _on_session_refreshed(self, new_session_info: Dict):
        """
        Callback when session is refreshed.
        Update our session_info with new session ID.
        
        Args:
            new_session_info: New session info from refresh
        """
        with self.data_lock:
            # Update session ID and related info
            self.session_info["session_id"] = new_session_info.get("session_id")
            self.session_info["server_url"] = new_session_info.get("server_url")
            
            self._log("🔄 Session refreshed successfully")
            self._log(f"   New session ID: ...{new_session_info.get('session_id', '')[-8:]}")

    def _on_session_expired(self):
        """
        Callback when session expires and cannot be refreshed.
        Show error and optionally logout.
        """
        self._log("❌ Session expired and could not be refreshed")
        
        # If export is running, it will fail - let the error handler deal with it
        # If not exporting, show a warning
        if not self._is_export_busy():
            def show_expired_dialog():
                result = messagebox.showerror(
                    "Session Expired",
                    "Your Salesforce session has expired and could not be refreshed.\n\n"
                    "Please log out and log back in.",
                    icon='error'
                )
            
            # Show dialog on main thread
            self._safe_ui_update(show_expired_dialog)

    def _emergency_reset_if_stuck(self):
        """
        Emergency reset if UI appears stuck.
        Called periodically to check for stuck states.
        """
        try:
            # Check if we're in "cancelling" state for too long
            current_state = self._get_export_state()
            
            if current_state == "cancelling":
                # Check how long we've been cancelling
                if not hasattr(self, '_cancelling_start_time'):
                    self._cancelling_start_time = time.time()
                else:
                    elapsed = time.time() - self._cancelling_start_time
                    
                    if elapsed > 15:  # Stuck for 15+ seconds
                        print("🚨 EMERGENCY: Export stuck in cancelling state, forcing reset")
                        self._log("🚨 Emergency reset: Export was stuck")
                        
                        # Force reset
                        self._reset_export_state()
                        self._set_export_ui_state(True)
                        self._refresh_button_visibility()
                        
                        self.progress_label.configure(
                            text="⚠️ Export cancelled (forced reset)",
                            text_color="orange"
                        )
                        
                        # Clear timestamp
                        delattr(self, '_cancelling_start_time')
            else:
                # Not cancelling, clear timestamp
                if hasattr(self, '_cancelling_start_time'):
                    delattr(self, '_cancelling_start_time')
        
        except Exception as e:
            print(f"⚠️ Emergency reset check error: {e}")
        
        # Schedule next check in 5 seconds
        self.after(5000, self._emergency_reset_if_stuck)    

    def _cancel_export_safe(self):
        """
        Safe wrapper for ESC key binding.
        Only cancels if actually exporting.
        """
        export_state = self._get_export_state()
        
        if export_state == "running":
            self._cancel_export()
        else:
            print(f"ℹ️ ESC pressed but export state is '{export_state}' - ignoring")
            
    def _setup_ui(self):
        """Setup the main UI layout"""
        
        # Configure grid layout (3 rows)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # Header (fixed height)
        self.grid_rowconfigure(1, weight=1)  # Main content (expandable)
        self.grid_rowconfigure(2, weight=0)  # Bottom section (fixed height)
        
        # Header
        self._create_header()
        
        # Main content area (3-panel layout)
        self._create_main_content()
        
        # Bottom section (file naming, progress, export button, log)
        self._create_bottom_section()
        
    def _center_window(self):
        """Center the main window on screen"""
        # Force window to update and calculate its actual size
        self.update_idletasks()
        
        # Explicitly set the geometry again to ensure it's correct
        self.geometry("1200x800")
        
        # Wait a tiny bit for the geometry to apply
        self.update_idletasks()
        
        # Now calculate center position
        width = 1200
        height = 800
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        
        # Apply the centered geometry
        self.geometry(f'{width}x{height}+{x}+{y}')
    
    # ===== NEW: UI STATE MANAGEMENT METHODS =====
    # ✅ NEW: Atomic state management methods
    def _get_export_state(self) -> str:
        """Get current export state (thread-safe)"""
        with self.state_lock:
            return self._export_state
        
    def _set_export_state(self, new_state: str):
        """
        Set export state atomically (thread-safe).
        Valid states: "idle", "running", "cancelling"
        """
        with self.state_lock:
            old_state = self._export_state
            self._export_state = new_state
            
            # Auto-sync is_exporting for backward compatibility
            self.is_exporting = (new_state in ("running", "cancelling"))
            
            # Log state transitions for debugging
            if old_state != new_state:
                print(f"🔄 Export state: {old_state} → {new_state}")


    def _is_export_busy(self) -> bool:
        """Check if export is currently running or cancelling"""
        state = self._get_export_state()
        return state in ("running", "cancelling")

    # main_app.py - REPLACE _reset_export_state (around line 120)

    def _reset_export_state(self):
        """
        Reset export state to idle and clear all flags.
        
        FIXED: Always resets, even if already idle.
        """
        with self.state_lock:
            self._export_state = "idle"
            self.is_exporting = False
            self._showing_dialog = False
            self.export_cancel_event.clear()
        
        print("🔄 Export state reset to IDLE")
        
        # ✅ Force button refresh on main thread (ALWAYS)
        def force_button_reset():
            try:
                # Hide cancel button
                self.cancel_button.grid_remove()
                self.cancel_button.configure(
                    state="disabled",
                    text="🛑 Cancel Export"
                )
                
                # Show export button
                self.export_button.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 5))
                self.export_button.lift()
                
                # Update export button state
                self._update_export_button_state()
                
                # Force UI update
                self.update_idletasks()
                
                print("✅ Buttons reset successfully")
            except Exception as e:
                print(f"⚠️ Button reset error: {e}")
        
        # Execute on main thread
        self.after(50, force_button_reset)
        
    def _set_ui_state(self, state: str):
        """
        Set UI state and update UI accordingly.
        States: 'idle', 'loading', 'exporting'
        """
        with self.ui_lock:
            self.ui_state = state
            
            if state == "idle":
                self.is_loading = False
                self.is_exporting = False
                
            elif state == "loading":
                self.is_loading = True
                self.is_exporting = False
                
            elif state == "exporting":
                self.is_loading = False
                self.is_exporting = True
    
    def _is_ui_busy(self) -> bool:
        """Check if UI is currently busy with an operation"""
        with self.ui_lock:
            return self.ui_state != "idle"
    
    def _safe_ui_update(self, callback, *args, **kwargs):
        """
        Execute UI update safely on main thread.
        Prevents race conditions and ensures thread safety.
        
        IMPROVED: Better error handling and thread detection.
        """
        def wrapper():
            try:
                callback(*args, **kwargs)
            except Exception as e:
                print(f"⚠️ UI update error in callback: {str(e)}")
        
        # Check if we're on main thread
        try:
            import threading
            if threading.current_thread() is threading.main_thread():
                # Already on main thread - execute immediately
                wrapper()
            else:
                # Schedule on main thread
                self.after(0, wrapper)
        except Exception:
            # Fallback: always schedule
            try:
                self.after(0, wrapper)
            except:
                # Last resort: use queue
                self.update_queue.put(("ui_update", (callback, args, kwargs)))
    
    def _prevent_double_click(self, button: ctk.CTkButton, duration: float = 2.0):
        """
        Disable button temporarily to prevent double-clicks.
        Re-enables after duration seconds.
        """
        button.configure(state="disabled")
        
        def re_enable():
            try:
                button.configure(state="normal")
            except:
                pass  # Button might be destroyed
        
        self.after(int(duration * 1000), re_enable)
    
    def _on_closing(self):
        """
        Handle window close event.
        
        KEY FIX: Calls logout instead of directly destroying.
        This ensures proper cleanup through the parent.
        """
        if self._is_ui_busy():
            result = messagebox.askyesno(
                "Operation in Progress",
                "An operation is in progress. Are you sure you want to exit?\n\n"
                "This will cancel the current operation.",
                icon='warning'
            )
            
            if not result:
                return
            
            # Cancel ongoing operations
            self.export_cancel_event.set()
            self._log("🛑 Cancelling operations...")
            
            # Give threads time to cleanup, then close
            self.after(500, self._force_close)
        else:
            # No operations running - can close immediately
            self._force_close()
    
    def _force_close(self):
        """
        Force close the window.
        
        Called after operations are cancelled or if no operations running.
        """
        try:
            self.grab_release()
        except:
            pass
        
        # If we have a logout callback, use it (proper flow)
        if self.on_logout_callback:
            try:
                self.on_logout_callback()
                return
            except:
                pass
        
        # Fallback: destroy directly
        try:
            self.destroy()
        except:
            pass
    
    def _on_window_configure(self, event=None):
        """
        Handle window move/resize events with debouncing.
        Fixes button visibility issues when moving between monitors.
        
        IMPROVED: Better debouncing with adaptive delays and safety checks.
        """
        # Only process events for the main window (not child widgets)
        if event and event.widget != self:
            return
        
        # ✅ SAFETY: Check if attributes exist (early window events can fire before init completes)
        if not hasattr(self, 'is_exporting') or not hasattr(self, '_configure_timer'):
            return
        
        # ✅ Cancel any pending configure updates (debouncing)
        if self._configure_timer:
            try:
                self.after_cancel(self._configure_timer)
            except:
                pass
        
        # ✅ Adaptive delay based on current state
        try:
            with self.ui_lock:
                delay = 400 if self.is_exporting else 100
        except:
            delay = 100  # Fallback if lock fails
        
        self._configure_timer = self.after(delay, self._apply_window_configure)

    def _apply_window_configure(self):
        """
        Apply window configuration changes after debounce delay.
        
        IMPROVED: Simplified with better error handling.
        """
        try:
            # ✅ SAFETY: Check attributes exist
            if not hasattr(self, 'is_exporting'):
                return
            
            # Refresh buttons with current state
            self._refresh_button_visibility()
            
        except Exception as e:
            # Log errors for debugging
            try:
                print(f"⚠️ Window configure error: {e}")
            except:
                pass
        finally:
            # Clear timer reference
            self._configure_timer = None


    def _refresh_button_visibility(self):
        """
        Refresh export/cancel button visibility based on ACTUAL current state.
        
        This is the SINGLE SOURCE OF TRUTH for button visibility.
        Thread-safe and handles all edge cases.
        
        IMPROVED: Uses atomic state management to prevent race conditions.
        """
        # ✅ CRITICAL: Read state atomically
        export_state = self._get_export_state()
        is_cancelling = self.export_cancel_event.is_set()
        
        # Debug logging
        print(f"🔄 Refreshing buttons: state={export_state}, cancelling={is_cancelling}")
        
        try:
            if export_state == "running":
                # ===== EXPORTING: Show CANCEL button =====
                
                if is_cancelling:
                    # User clicked cancel - button should be disabled
                    self.cancel_button.configure(
                        state="disabled",
                        text="🛑 Cancelling..."
                    )
                else:
                    # Export is running - button should be ENABLED and clickable
                    self.cancel_button.configure(
                        state="normal",
                        text="🛑 Cancel Export"
                    )
                
                # Show cancel button
                self.cancel_button.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 5))
                self.cancel_button.lift()
                
                # Hide export button
                self.export_button.grid_remove()
                
            else:
                # ===== IDLE or CANCELLING: Show EXPORT button =====
                
                # Show export button FIRST (no gap)
                self.export_button.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 5))
                self.export_button.lift()
                
                # Hide cancel button
                self.cancel_button.grid_remove()
                self.cancel_button.configure(state="disabled", text="🛑 Cancel Export")
                self.cancel_button.lower()
                
                # Update export button enabled/disabled state
                self._update_export_button_state()
            
            # Force UI update
            self.update_idletasks()
            
            print(f"✅ Buttons refreshed successfully")
            
        except Exception as e:
            print(f"⚠️ Button visibility error: {e}")
            
    def _create_header(self):
        """Create header section with title and login status"""
        header_frame = ctk.CTkFrame(self, height=80, corner_radius=0)
        header_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        header_frame.grid_propagate(False)
        
        # Left side - Title
        left_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        left_frame.pack(side="left", fill="both", expand=True, padx=20, pady=10)
        
        title_label = ctk.CTkLabel(
            left_frame,
            text="📊 Salesforce Report Exporter",
            font=ctk.CTkFont(size=22, weight="bold")
        )
        title_label.pack(anchor="w")
        
        self.subtitle_label = ctk.CTkLabel(
            left_frame,
            text="Select folders and reports to export • Ctrl+E to export • ESC to cancel",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        self.subtitle_label.pack(anchor="w", pady=(3, 0))
        
        # Right side - Login status and logout button
        right_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        right_frame.pack(side="right", padx=20, pady=10)
        
        # ✅ NEW: Status is now set based on session_info
        instance = self.session_info.get("instance_url", "").replace('https://', '')
        api_version = self.session_info.get("api_version", "")
        user_name = self.session_info.get("user_name", "")
        
        status_text = f"🟢 {instance}"
        if api_version:
            status_text += f" (API v{api_version})"
        
        self.status_label = ctk.CTkLabel(
            right_frame,
            text=status_text,
            font=ctk.CTkFont(size=12),
            text_color="green"
        )
        self.status_label.pack(pady=(0, 5))
        
        # ✅ NEW: Show logout button instead of login
        self.logout_button = ctk.CTkButton(
            right_frame,
            text="Logout",
            command=self._logout,
            width=150,
            height=32,
            fg_color="#d32f2f",
            hover_color="#9a2222"
        )
        self.logout_button.pack()
    
    def _create_main_content(self):
        """Create main content area with 3 panels: Available | Actions | Selected"""
        
        # Main content container
        content_frame = ctk.CTkFrame(self, corner_radius=0)
        content_frame.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        content_frame.grid_rowconfigure(0, weight=1)
        content_frame.grid_columnconfigure(0, weight=1)  # Left panel
        content_frame.grid_columnconfigure(1, weight=1)  # Right panel (removed middle)
        
        # LEFT PANEL - Available Items
        self._create_left_panel(content_frame)
        
        # RIGHT PANEL - Selected Items (changed column from 2 to 1)
        self._create_right_panel(content_frame)
    
    def _create_left_panel(self, parent):
        """Create left panel - Clean, compact layout with search button"""
        
        left_panel = ctk.CTkFrame(parent)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        
        # ✅ SIMPLIFIED: Only 2 rows now (search + tree)
        left_panel.grid_rowconfigure(0, weight=0)  # Search section (fixed)
        left_panel.grid_rowconfigure(1, weight=1)  # Tree view (expands)
        left_panel.grid_columnconfigure(0, weight=1)
        
        # ========== ROW 0: Search Section ==========
        search_container = ctk.CTkFrame(left_panel, fg_color="transparent")
        search_container.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 10))
        search_container.grid_columnconfigure(0, weight=1)
        
        # Header label (compact)
        header_label = ctk.CTkLabel(
            search_container,
            text="Available Reports/Folders",
            font=ctk.CTkFont(size=15, weight="bold"),
            anchor="w"
        )
        header_label.grid(row=0, column=0, sticky="w", pady=(0, 8))
        
        # Search box + button in one row
        search_frame = ctk.CTkFrame(search_container, fg_color="transparent")
        search_frame.grid(row=1, column=0, sticky="ew")
        search_frame.grid_columnconfigure(0, weight=1)  # Entry expands
        search_frame.grid_columnconfigure(1, weight=0)  # Button fixed
        
        # Search entry
        self.left_search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="🔍 Search folders and reports...",
            height=34
        )
        self.left_search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        
        # Search button
        self.search_button = ctk.CTkButton(
            search_frame,
            text="🔍 Search",
            command=self._on_search_button_clicked,
            width=95,
            height=34,
            fg_color="#1f6aa5",
            hover_color="#144870",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.search_button.grid(row=0, column=1)
        
        # Bind Enter key to search
        self.left_search_entry.bind("<Return>", lambda e: self._on_search_button_clicked())
        
        # ========== ROW 1: Tree View Container (expands fully) ==========
        self.tree_container = ctk.CTkScrollableFrame(
            left_panel,
            fg_color="#2b2b2b",
            corner_radius=5
        )
        self.tree_container.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.tree_container.grid_columnconfigure(0, weight=1)
        
        # Show helpful empty state (no auto-load)
        self._show_empty_search_state()
        
        # Initialize virtual tree (will be populated after search)
        self.virtual_tree = None
        self.tree_items: Dict[str, Dict] = {}
    
    
    def _create_right_panel(self, parent):
        """Create right panel - Compact layout"""
        
        right_panel = ctk.CTkFrame(parent)
        right_panel.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10) 
        
        # Configure rows (Row 2 gets the expansion)
        right_panel.grid_rowconfigure(0, weight=0)
        right_panel.grid_rowconfigure(1, weight=0)
        right_panel.grid_rowconfigure(2, weight=1) # List expands
        right_panel.grid_rowconfigure(3, weight=0)
        right_panel.grid_columnconfigure(0, weight=1)
        
        # Header - REDUCED PADDING
        header_label = ctk.CTkLabel(
            right_panel,
            text="Selected for Export",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        header_label.grid(row=0, column=0, sticky="w", padx=10, pady=(10, 2))  # ✅ REDUCED from pady=(10, 5)
        
        # Selection count - REDUCED PADDING
        self.selection_count_label = ctk.CTkLabel(
            right_panel,
            text="0 reports selected",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.selection_count_label.grid(row=1, column=0, sticky="w", padx=10, pady=(0, 3))  # ✅ REDUCED from pady=(0, 5)
        
        # Selected items list (Scrollable, expands)
        self.selected_container = ctk.CTkScrollableFrame(
            right_panel,
            fg_color="#2b2b2b",
            corner_radius=5
        )
        self.selected_container.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 5))  # ✅ REDUCED from pady=(0, 10)
        self.selected_container.grid_columnconfigure(0, weight=1)
        
        # Placeholder
        self.selected_placeholder = ctk.CTkLabel(
            self.selected_container,
            text="No reports selected.\nSelect from left panel.",
            text_color="gray",
            font=ctk.CTkFont(size=12),
            justify="center"
        )
        self.selected_placeholder.grid(row=0, column=0, pady=30)
        
        # Actions section - REDUCED PADDING
        actions_frame = ctk.CTkFrame(right_panel, fg_color="transparent")
        actions_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=(0, 8))  # ✅ REDUCED from pady=(0, 10)
        actions_frame.grid_columnconfigure(0, weight=1)
        
        actions_label = ctk.CTkLabel(
            actions_frame,
            text="Actions",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        actions_label.grid(row=0, column=0, sticky="w", pady=(0, 2))
        
        # Quick remove all button - SMALLER HEIGHT
        self.clear_selected_button = ctk.CTkButton(
            actions_frame,
            text="Clear All Selected",
            command=self._clear_all_selected,
            height=28,  # ✅ REDUCED from 30
            fg_color="#d32f2f",
            hover_color="#9a2222",
            state="disabled"
        )
        self.clear_selected_button.grid(row=1, column=0, sticky="ew", pady=(0, 3))  # ✅ REDUCED from pady=(0, 5)
    
    def _create_bottom_section(self):
        """Create bottom section with file naming, progress, export button, and log"""
        
        bottom_frame = ctk.CTkFrame(self, corner_radius=0)
        bottom_frame.grid(row=2, column=0, sticky="ew", padx=0, pady=0)
        bottom_frame.grid_columnconfigure(0, weight=1)
        
        # File naming section
        file_frame = ctk.CTkFrame(bottom_frame)
        file_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        file_frame.grid_columnconfigure(1, weight=1)
        
        # ZIP Filename label
        zip_label = ctk.CTkLabel(
            file_frame,
            text="ZIP Filename:",
            font=ctk.CTkFont(size=12, weight="bold"),
            width=120
        )
        zip_label.grid(row=0, column=0, padx=(15, 10), pady=10, sticky="w")
        
        # Filename entry
        self.filename_entry = ctk.CTkEntry(
            file_frame,
            placeholder_text="salesforce_reports_20251126_0026.zip",
            height=35
        )
        self.filename_entry.grid(row=0, column=1, sticky="ew", padx=(0, 10), pady=10)
        
        # Auto-generate timestamp filename
        self._generate_default_filename()
        
        # Save location section
        location_frame = ctk.CTkFrame(bottom_frame)
        location_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 5))
        location_frame.grid_columnconfigure(1, weight=1)
        
        location_label = ctk.CTkLabel(
            location_frame,
            text="Save Location:",
            font=ctk.CTkFont(size=12, weight="bold"),
            width=120
        )
        location_label.grid(row=0, column=0, padx=(15, 10), pady=10, sticky="w")
        
        self.location_entry = ctk.CTkEntry(
            location_frame,
            placeholder_text="Click Browse to select save location...",
            height=35,
            state="readonly"
        )
        self.location_entry.grid(row=0, column=1, sticky="ew", padx=(0, 10), pady=10)
        
        self.browse_button = ctk.CTkButton(
            location_frame,
            text="Browse...",
            command=self._browse_save_location,
            width=100,
            height=35
        )
        self.browse_button.grid(row=0, column=2, padx=(0, 15), pady=10)
        
        # Export button
        self.export_button = ctk.CTkButton(
            bottom_frame,
            text="🚀 Export Reports",
            command=self._start_export_safe,  # ← Use safe wrapper
            height=45,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color="#1f6aa5",
            hover_color="#144870",
            state="disabled"
        )
        self.export_button.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 5))
        
        # Cancel button (hidden by default)
        self.cancel_button = ctk.CTkButton(
            bottom_frame,
            text="🛑 Cancel Export",
            command=self._cancel_export,
            height=38,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#d32f2f",
            hover_color="#9a2222",
            state="disabled"
        )
        self.cancel_button.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 4))
        self.cancel_button.grid_remove()  # Hide initially
        self.cancel_button.lower()
         
        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(bottom_frame, height=20)
        self.progress_bar.grid(row=3, column=0, sticky="ew", padx=10, pady=(0, 5))
        self.progress_bar.set(0)
        
        # Progress label
        self.progress_label = ctk.CTkLabel(
            bottom_frame,
            text="Ready to export",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        self.progress_label.grid(row=4, column=0, sticky="w", padx=15, pady=(0, 5))
        
        # Activity Log section
        log_frame = ctk.CTkFrame(bottom_frame, height=150)
        log_frame.grid(row=5, column=0, sticky="ew", padx=10, pady=(5, 10))
        log_frame.grid_propagate(False)
        log_frame.grid_rowconfigure(1, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)
        
        log_header_frame = ctk.CTkFrame(log_frame, fg_color="transparent")
        log_header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        
        log_header_label = ctk.CTkLabel(
            log_header_frame,
            text="📋 Activity Log",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        log_header_label.pack(side="left")
        
        clear_log_btn = ctk.CTkButton(
            log_header_frame,
            text="Clear Log",
            command=self._clear_log,
            width=80,
            height=25,
            font=ctk.CTkFont(size=11)
        )
        clear_log_btn.pack(side="right")
        
        # Log textbox
        self.log_textbox = ctk.CTkTextbox(
            log_frame,
            wrap="word",
            font=ctk.CTkFont(family="Consolas", size=10),
            fg_color="#1a1a1a"
        )
        self.log_textbox.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.log_textbox.configure(state="disabled")
    
    def _generate_default_filename(self):
        """Generate default filename with timestamp"""
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M')
        default_name = f"salesforce_reports_{timestamp}.zip"
        self.filename_entry.delete(0, "end")
        self.filename_entry.insert(0, default_name)
    
    
    # ===== LOGGING =====
    
    def _log(self, message: str):
        """Add message to log"""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        log_msg = f"[{timestamp}] {message}\n"
        
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", log_msg)
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")
    
    def _clear_log(self):
        """Clear the log"""
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", "end")
        self.log_textbox.configure(state="disabled")
    
    # ===== LOGIN OPERATIONS =====
    
    def _logout(self):
        """Logout and return to login window - WORKS DURING LOADING"""
        
        # Check if busy
        if self._is_ui_busy():
            # Better message based on what's happening
            if self.is_loading:
                message = "Search is in progress. Cancel search and logout?"
            elif self.is_exporting:
                message = "Export is in progress. Cancel export and logout?"
            else:
                message = "An operation is in progress. Cancel and logout?"
            
            result = messagebox.askyesno(
                "Operation in Progress",
                message,
                icon='warning'
            )
            
            if not result:
                return
            
            # Set cancel event to stop loading/exporting
            self._log("🛑 Cancelling operations for logout...")
            self.export_cancel_event.set()
            
            # Give threads 500ms to see the cancel event, then force logout
            self.after(500, self._force_logout_after_cancel)
            return
        
        # Normal logout (no operations running)
        result = messagebox.askyesno(
            "Confirm Logout",
            "Are you sure you want to logout?\n\nYou will return to the login screen.",
            icon='question'
        )
        
        if not result:
            return
        
        self._log("🔴 Logging out...")
        
        # ✅ NEW: Clear session manager
        self.session_manager.clear()
        
        # Release grab before calling parent callback
        try:
            self.grab_release()
        except:
            pass
        
        # Call parent's logout handler
        if self.on_logout_callback:
            try:
                self.on_logout_callback()
            except Exception as e:
                print(f"⚠️ Error in logout callback: {e}")
                try:
                    self.destroy()
                except:
                    pass
        else:
            try:
                self.destroy()
            except:
                pass

    def _force_logout_after_cancel(self):
        """Force logout after cancelling operations"""
        self._log("🔴 Logging out...")
        
        # Reset states
        self._set_ui_state("idle")
        self.is_loading = False
        self.is_exporting = False
        
        try:
            self.grab_release()
        except:
            pass
        
        if self.on_logout_callback:
            try:
                self.on_logout_callback()
            except Exception as e:
                print(f"⚠️ Error in logout callback: {e}")
                try:
                    self.destroy()
                except:
                    pass
        else:
            try:
                self.destroy()
            except:
                pass
    
    # ===== LOAD FOLDERS AND REPORTS =====
    
    def _show_welcome_message(self):
        """
        Show welcome message and search instructions on startup.
        No data is loaded until user performs a search.
        """
        if not self.session_info:
            self._log("⚠️ No session info available")
            return
        
        # Extract session info
        instance = self.session_info.get("instance_url", "").replace("https://", "")
        api_version = self.session_info.get("api_version", "")
        user_name = self.session_info.get("user_name", "")
        
        # Log welcome message
        self._log("=" * 50)
        self._log("✅ CONNECTED TO SALESFORCE")
        self._log(f"🌐 Instance: {instance}")
        self._log(f"🔌 API Version: v{api_version}")
        if user_name:
            self._log(f"👤 User: {user_name}")
        self._log("=" * 50)
        self._log("")
        self._log("🔍 Ready to search!")
        self._log("💡 Enter keywords like 'Sales', 'Account', 'Q4 2024', etc.")
        self._log("💡 Press Enter or click Search button to find reports")
        self._log("")
        
        # Show empty search state in tree
        self._show_empty_search_state()
        
        # ✅ NEW: Check for existing checkpoint
        self.after(2000, self._check_for_existing_checkpoint)

    # main_app.py - Add this NEW method after _show_welcome_message()

    def _check_for_existing_checkpoint(self):
        """
        Check if there's an existing checkpoint from a previous export.
        If found, offer to resume.
        """
        try:
            # Look for checkpoint files in user's temp directory
            import tempfile
            temp_dir = Path(tempfile.gettempdir())
            checkpoint_files = list(temp_dir.glob("sf_export_checkpoint_*.json"))
            
            if not checkpoint_files:
                return
            
            # Get most recent checkpoint
            checkpoint_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            latest_checkpoint = checkpoint_files[0]
            
            # Try to load it
            checkpoint = ExportCheckpoint(str(latest_checkpoint))
            if not checkpoint.load():
                return
            
            # Check if it's incomplete
            progress = checkpoint.get_progress()
            if progress["pending"] == 0:
                # Complete, delete it
                checkpoint.delete()
                return
            
            # We have an incomplete checkpoint!
            self.pending_checkpoint = {
                "path": str(latest_checkpoint),
                "checkpoint": checkpoint,
                "progress": progress,
                "output_path": checkpoint.get_output_path()
            }
            
            # Show resume prompt
            self.after(1000, self._show_resume_prompt)
            
        except Exception as e:
            print(f"⚠️ Error checking for checkpoint: {e}")

    def _show_resume_prompt(self):
        """Show dialog asking user if they want to resume previous export."""
        if not self.pending_checkpoint:
            return
        
        progress = self.pending_checkpoint["progress"]
        output_path = self.pending_checkpoint["output_path"]
        
        message = (
            f"Found an incomplete export:\n\n"
            f"📊 Progress:\n"
            f"  • Total: {progress['total']} reports\n"
            f"  • Completed: {progress['completed']}\n"
            f"  • Failed: {progress['failed']}\n"
            f"  • Pending: {progress['pending']}\n\n"
            f"📦 Destination: {output_path}\n\n"
            f"Would you like to resume this export?"
        )
        
        result = messagebox.askyesno(
            "Resume Previous Export?",
            message,
            icon='question'
        )
        
        if result:
            # User wants to resume
            self._resume_from_checkpoint()
        else:
            # User declined, delete checkpoint
            self.pending_checkpoint["checkpoint"].delete()
            self.pending_checkpoint = None
            self._log("🗑️ Previous checkpoint deleted")

    def _resume_from_checkpoint(self):
        """Resume export from existing checkpoint."""
        if not self.pending_checkpoint:
            return
        
        try:
            checkpoint = self.pending_checkpoint["checkpoint"]
            checkpoint_path = self.pending_checkpoint["path"]
            progress = self.pending_checkpoint["progress"]
            
            # Get session info from checkpoint
            stored_session = checkpoint.get_session_info()
            
            # Verify session is still valid (same instance)
            current_instance = self.session_info.get("instance_url", "")
            stored_instance = stored_session.get("instance_url", "")
            
            if current_instance != stored_instance:
                messagebox.showerror(
                    "Cannot Resume",
                    f"Checkpoint is for a different Salesforce instance:\n\n"
                    f"Current: {current_instance}\n"
                    f"Checkpoint: {stored_instance}\n\n"
                    f"Please login to the correct instance or start a new export."
                )
                self.pending_checkpoint = None
                return
            
            # Set resume mode
            self.resume_mode = True
            self.checkpoint_path = checkpoint_path
            
            # Set output path
            self.output_zip_path = checkpoint.get_output_path()
            
            # Update UI
            output_dir = str(Path(self.output_zip_path).parent)
            self.location_entry.configure(state="normal")
            self.location_entry.delete(0, "end")
            self.location_entry.insert(0, output_dir)
            self.location_entry.configure(state="readonly")
            
            filename = Path(self.output_zip_path).name
            self.filename_entry.delete(0, "end")
            self.filename_entry.insert(0, filename)
            
            # Log
            self._log("=" * 50)
            self._log("📂 RESUMING PREVIOUS EXPORT")
            self._log(f"✅ Already completed: {progress['completed']} reports")
            self._log(f"⏳ Remaining: {progress['pending']} reports")
            self._log(f"❌ Previously failed: {progress['failed']} reports")
            self._log("=" * 50)
            
            # Automatically start export
            self.after(500, self._start_export_from_resume)
            
        except Exception as e:
            self._log(f"❌ Failed to resume: {str(e)}")
            messagebox.showerror("Resume Failed", f"Could not resume export:\n\n{str(e)}")
            self.pending_checkpoint = None

    def _start_export_from_resume(self):
        """Start export in resume mode (called automatically after resume prompt)."""
        # Get pending report IDs from checkpoint
        checkpoint = self.pending_checkpoint["checkpoint"]
        pending_ids = checkpoint.get_pending_reports()
        
        # Build reports_metadata for pending reports
        reports_metadata = {}
        
        # Try to get metadata from already loaded data
        with self.data_lock:
            for folder_id, reports in self.reports_by_folder.items():
                for report in reports:
                    report_id = report.get("id")
                    if report_id in pending_ids:
                        reports_metadata[report_id] = {
                            "id": report_id,
                            "name": report.get("name", report_id),
                            "reportFormat": report.get("reportFormat", "TABULAR")
                        }
        
        # Start export (this will use resume mode)
        self._start_export_internal(
            report_ids=pending_ids,
            reports_metadata=reports_metadata,
            resume_mode=True
        )
    
        
    def _search_worker(self, keyword: str):
        """
        Background worker to search Salesforce by keyword.
        
        Uses the new search_by_keyword() method from exporter which:
        1. Searches folders matching keyword
        2. Searches reports matching keyword
        3. Fetches parent folders of matching reports
        4. Groups reports by folder
        5. Returns organized data ready for tree view
        
        Args:
            keyword: Search term entered by user
        """
        try:
            session_id = self.session_info.get("session_id")
            instance_url = self.session_info.get("instance_url")
            
            # Create exporter instance
            exporter = SalesforceReportExporter(session_id, instance_url)
            
            # Log search start
            self.update_queue.put(("log", f"🔍 Searching for: '{keyword}'"))
            
            # Check cancellation before search
            if self.export_cancel_event.is_set():
                self.update_queue.put(("search_cancelled", None))
                return
            
            # ✅ MAIN SEARCH: This does all the heavy lifting
            result = exporter.search_by_keyword(
                keyword=keyword,
                cancel_event=self.export_cancel_event
            )
            
            # Check cancellation after search
            if self.export_cancel_event.is_set():
                self.update_queue.put(("search_cancelled", None))
                return
            
            # Extract results
            folders = result.get("folders", [])
            reports_by_folder = result.get("reports_by_folder", {})
            
            # Calculate statistics
            total_folders = len(folders)
            total_reports = sum(len(reports) for reports in reports_by_folder.values())
            
            # Log results
            self.update_queue.put(("log", f"✅ Found {total_folders} folders with {total_reports} reports"))
            
            # Send organized data to UI
            self.update_queue.put(("search_complete", {
                "folders": folders,
                "reports_by_folder": reports_by_folder,
                "keyword": keyword
            }))
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            self.update_queue.put(("log", f"❌ Search error: {error_details}"))
            self.update_queue.put(("search_error", str(e)))


    def _on_search_complete(self, result: Dict):
        """
        Handle search completion and populate tree with results.
        
        ✅ FIXED: Preserves selections across different searches (no auto-clearing).
        """
        # Extract data
        folders = result.get("folders", [])
        reports_by_folder = result.get("reports_by_folder", {})
        keyword = result.get("keyword", "")
        
        # ✅ Cache the results
        keyword_lower = keyword.lower()
        self.search_cache[keyword_lower] = {
            "folders": folders,
            "reports_by_folder": reports_by_folder,
            "keyword": keyword
        }
        
        # ✅ Limit cache size (LRU-style)
        if len(self.search_cache) > self.search_cache_max_size:
            # Remove oldest entry
            oldest_key = next(iter(self.search_cache))
            del self.search_cache[oldest_key]
        
        # Update data storage
        with self.data_lock:
            self.available_folders = folders
            self.reports_by_folder = reports_by_folder
        
        # Calculate statistics
        total_folders = len(folders)
        total_reports = sum(len(reports) for reports in reports_by_folder.values())
        
        # Clear search loading state
        for widget in self.tree_container.winfo_children():
            widget.destroy()
        
        # Check if we got results
        if total_folders == 0 and total_reports == 0:
            # No results found
            self._show_no_results_state(keyword)
            
            # Re-enable search
            self.search_button.configure(state="normal", text="🔍 Search")
            self.left_search_entry.configure(state="normal")
            
            # Reset state
            self._set_ui_state("idle")
            
            self._log(f"ℹ️ No results found for '{keyword}'")
            return
        
        # Populate tree with results
        self._log(f"📊 Displaying {total_folders} folders with {total_reports} reports")
        
        # ✅ REMOVED: Don't filter out selections anymore!
        # Users might want to export reports from multiple searches
        # They can manually clear if needed using "Clear All Selected" button
        
        # Use existing populate_tree method
        self._populate_tree("")
        
        # Re-enable search
        self.search_button.configure(state="normal", text="🔍 Search")
        self.left_search_entry.configure(state="normal")
        
        # Reset state
        self._set_ui_state("idle")
        
        # Log summary
        self._log("=" * 50)
        self._log(f"✅ SEARCH COMPLETE")
        self._log(f"🔍 Keyword: '{keyword}'")
        self._log(f"📁 Folders: {total_folders}")
        self._log(f"📄 Reports: {total_reports}")
        
        # Show folder breakdown
        if total_folders > 0 and total_folders <= 10:
            for folder in folders[:10]:
                folder_id = folder.get("id")
                folder_name = folder.get("name")
                report_count = len(reports_by_folder.get(folder_id, []))
                self._log(f"  • {folder_name}: {report_count} reports")
        
        self._log("=" * 50)
        
        # Update export button state
        self._update_export_button_state()


    def _on_search_error(self, error_msg: str):
        """
        Handle search error with user-friendly messages.
        
        Args:
            error_msg: Error message from search worker
        """
        # Clear search loading state
        for widget in self.tree_container.winfo_children():
            widget.destroy()
        
        # Show error state in tree
        error_frame = ctk.CTkFrame(self.tree_container, fg_color="transparent")
        error_frame.grid(row=0, column=0, pady=30)
        
        icon_label = ctk.CTkLabel(
            error_frame,
            text="❌",
            font=ctk.CTkFont(size=48)
        )
        icon_label.pack(pady=(0, 10))
        
        title_label = ctk.CTkLabel(
            error_frame,
            text="Search Failed",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="red"
        )
        title_label.pack(pady=(0, 5))
        
        # Truncate long error messages
        display_error = error_msg[:200] + "..." if len(error_msg) > 200 else error_msg
        
        error_label = ctk.CTkLabel(
            error_frame,
            text=display_error,
            font=ctk.CTkFont(size=11),
            text_color="gray",
            wraplength=400,
            justify="center"
        )
        error_label.pack(pady=(0, 15))
        
        # Helpful suggestion
        suggestion = self._get_search_error_suggestion(error_msg)
        if suggestion:
            suggestion_label = ctk.CTkLabel(
                error_frame,
                text=f"💡 {suggestion}",
                font=ctk.CTkFont(size=10),
                text_color="#1f6aa5",
                wraplength=400,
                justify="center"
            )
            suggestion_label.pack()
        
        # Re-enable search
        self.search_button.configure(state="normal", text="🔍 Search")
        self.left_search_entry.configure(state="normal")
        
        # Reset state
        self._set_ui_state("idle")
        
        # Log error
        self._log(f"❌ Search failed: {error_msg}")
        
        # Show error dialog
        messagebox.showerror(
            "Search Failed",
            f"Failed to search Salesforce:\n\n{error_msg}\n\n{suggestion}"
        )

    def _get_search_error_suggestion(self, error_msg: str) -> str:
        """
        Get helpful suggestion based on search error message.
        
        Args:
            error_msg: Error message from search
            
        Returns:
            Helpful suggestion string
        """
        error_lower = error_msg.lower()
        
        if "session" in error_lower or "authentication" in error_lower or "invalid" in error_lower:
            return "Your session may have expired. Try logging out and back in."
        
        elif "network" in error_lower or "connection" in error_lower or "timeout" in error_lower:
            return "Check your internet connection and try again."
        
        elif "permission" in error_lower or "access" in error_lower:
            return "You may not have permission to search reports. Contact your Salesforce admin."
        
        elif "limit" in error_lower or "exceeded" in error_lower:
            return "Salesforce API limits reached. Try a more specific search keyword or wait a few minutes."
        
        elif "syntax" in error_lower or "query" in error_lower:
            return "Try a simpler search keyword (e.g., 'Sales' instead of special characters)."
        
        else:
            return "Try a different search keyword or check your connection."

    def _show_no_results_state(self, keyword: str):
        """
        Show friendly message when search returns no results.
        
        Args:
            keyword: The search keyword that returned no results
        """
        # Clear tree
        for widget in self.tree_container.winfo_children():
            widget.destroy()
        
        # Create no results frame
        no_results_frame = ctk.CTkFrame(self.tree_container, fg_color="transparent")
        no_results_frame.grid(row=0, column=0, pady=50)
        
        # Icon
        icon_label = ctk.CTkLabel(
            no_results_frame,
            text="🔍",
            font=ctk.CTkFont(size=48)
        )
        icon_label.pack(pady=(0, 10))
        
        # Title
        title_label = ctk.CTkLabel(
            no_results_frame,
            text="No Results Found",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.pack(pady=(0, 5))
        
        # Message
        message_label = ctk.CTkLabel(
            no_results_frame,
            text=f"No folders or reports match '{keyword}'",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        message_label.pack(pady=(0, 15))
        
        # Suggestions
        suggestions_label = ctk.CTkLabel(
            no_results_frame,
            text="💡 Try:\n• Different keywords (e.g., 'Account', 'Sales', 'Q4')\n• Shorter search terms\n• Check spelling",
            font=ctk.CTkFont(size=11),
            text_color="gray",
            justify="left"
        )
        suggestions_label.pack()
    
    def _on_search_cancelled(self):
        """Handle search cancellation (e.g., user logged out during search)"""
        
        # Clear search loading state
        for widget in self.tree_container.winfo_children():
            widget.destroy()
        
        # Show cancellation message
        placeholder = ctk.CTkLabel(
            self.tree_container,
            text="Search cancelled",
            text_color="gray",
            font=ctk.CTkFont(size=12)
        )
        placeholder.grid(row=0, column=0, pady=30)
        
        # Re-enable search
        self.search_button.configure(state="normal", text="🔍 Search")
        self.left_search_entry.configure(state="normal")
        
        # Reset UI state
        self._set_ui_state("idle")
        
        self._log("⚠️ Search cancelled")
    
    def _show_empty_search_state(self):
        """
        Show helpful empty state when no search has been performed yet.
        """
        # Clear tree
        for widget in self.tree_container.winfo_children():
            widget.destroy()
        
        # Create empty state message
        empty_frame = ctk.CTkFrame(self.tree_container, fg_color="transparent")
        empty_frame.grid(row=0, column=0, pady=50)
        
        icon_label = ctk.CTkLabel(
            empty_frame,
            text="🔍",
            font=ctk.CTkFont(size=48)
        )
        icon_label.pack(pady=(0, 10))
        
        title_label = ctk.CTkLabel(
            empty_frame,
            text="Search to Get Started",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.pack(pady=(0, 5))
        
        subtitle_label = ctk.CTkLabel(
            empty_frame,
            text="Enter keywords to search folders and reports\nExample: 'Sales', 'Account', 'Q4 2024'",
            font=ctk.CTkFont(size=11),
            text_color="gray",
            justify="center"
        )
        subtitle_label.pack()
    
    def _on_search_button_clicked(self):
        """
        Handle search button click with caching.
        """
        # Get search keyword
        keyword = self.left_search_entry.get().strip()
        
        # Validate input
        if not keyword:
            self._log("⚠️ Please enter a search keyword")
            messagebox.showwarning("No Keyword", "Please enter a search keyword.")
            return
        
        if len(keyword) < 2:
            self._log("⚠️ Search keyword must be at least 2 characters")
            messagebox.showwarning("Keyword Too Short", "Please enter at least 2 characters.")
            return
        
        # Check if already searching
        if self.is_loading:
            self._log("⚠️ Search already in progress, please wait...")
            return
        
        # Check if session is valid
        if not self.session_info:
            self._log("⚠️ No active session")
            messagebox.showerror("Not Logged In", "Please login first.")
            return
        
        # ✅ NEW: Check cache first
        keyword_lower = keyword.lower()
        if keyword_lower in self.search_cache:
            self._log(f"⚡ Using cached results for: '{keyword}'")
            cached_result = self.search_cache[keyword_lower]
            cached_result["keyword"] = keyword  # Update display keyword
            self._on_search_complete(cached_result)
            return
        
        # Not in cache - perform search
        self._log(f"🔍 Searching for: '{keyword}'")
        self._start_search(keyword)
        

    def _start_search(self, keyword: str):
        """
        Start search in background thread.
        
        Shows loading state and calls _search_worker() in separate thread
        to prevent UI freezing during Salesforce API calls.
        
        Args:
            keyword: Search term to find folders/reports
        """
        # Set loading state
        self._set_ui_state("loading")
        
        # Clear cancel event (fresh start)
        self.export_cancel_event.clear()
        
        # Disable search controls during search
        self.search_button.configure(state="disabled", text="🔄 Searching...")
        self.left_search_entry.configure(state="disabled")
        
        # Show loading indicator in tree
        for widget in self.tree_container.winfo_children():
            widget.destroy()
        
        loading_frame = ctk.CTkFrame(self.tree_container, fg_color="transparent")
        loading_frame.grid(row=0, column=0, pady=50)
        
        # Loading spinner icon
        loading_icon = ctk.CTkLabel(
            loading_frame,
            text="🔄",
            font=ctk.CTkFont(size=48)
        )
        loading_icon.pack(pady=(0, 10))
        
        # Loading message
        loading_label = ctk.CTkLabel(
            loading_frame,
            text="Searching Salesforce...",
            text_color="gray",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        loading_label.pack(pady=(0, 5))
        
        # Keyword display
        keyword_label = ctk.CTkLabel(
            loading_frame,
            text=f"Looking for: '{keyword}'",
            text_color="#1f6aa5",
            font=ctk.CTkFont(size=12)
        )
        keyword_label.pack()
        
        # Start search in background thread (prevents UI freeze)
        thread = threading.Thread(
            target=self._search_worker,
            args=(keyword,),
            daemon=True
        )
        thread.start()
    


    def _populate_tree_with_data(self, filtered_folders, total_reports_in_folders):
        """
        Populate tree after loading completes.
        ✅ NEW: Helper method to populate virtual tree.
        """
        # Remove temp message
        for widget in self.tree_container.winfo_children():
            widget.destroy()
        
        # Populate tree (virtual scrolling makes this instant!)
        self._populate_tree("")
        
        # Log results with statistics
        self._log("=" * 50)
        self._log(f"✅ DATA LOADING COMPLETE")
        self._log(f"📁 Folders Loaded: {len(filtered_folders)}")
        self._log(f"📄 Total Reports: {total_reports_in_folders}")
        
        if total_reports_in_folders > 0:
            avg_reports_per_folder = total_reports_in_folders / len(filtered_folders) if len(filtered_folders) > 0 else 0
            self._log(f"📊 Average Reports/Folder: {avg_reports_per_folder:.1f}")
        
        if total_reports_in_folders == 0:
            self._log("⚠️ WARNING: No reports found. Check folder permissions.")
        
        self._log("=" * 50)
        
    
    # ===== TREE VIEW POPULATION =====
    

    def _populate_tree(self, search_term: str = ""):
        """
        Populate the tree view with folders and reports.
        
        ✅ FIXED: Now uses virtual scrolling - NO UI FREEZING even with 10,000+ items!
        """
        
        # Clear existing tree
        if self.virtual_tree:
            self.virtual_tree.clear()
        
        for widget in self.tree_container.winfo_children():
            widget.destroy()
        
        self.tree_items.clear()
        
        if not self.available_folders:
            placeholder = ctk.CTkLabel(
                self.tree_container,
                text="No folders found",
                text_color="gray",
                font=ctk.CTkFont(size=12)
            )
            placeholder.grid(row=0, column=0, pady=30)
            return
        
        # Filter folders and reports by search term
        filtered_folders_data = []
        
        with self.data_lock:
            if search_term:
                search_lower = search_term.lower()
                
                for folder in self.available_folders:
                    folder_id = folder.get("id")
                    folder_name = folder.get("name", "")
                    
                    all_reports = self.reports_by_folder.get(folder_id, [])
                    
                    folder_matches = search_lower in folder_name.lower()
                    
                    if folder_matches:
                        filtered_folders_data.append({
                            "folder": folder,
                            "reports": all_reports
                        })
                    else:
                        matching_reports = [
                            r for r in all_reports
                            if search_lower in r.get("name", "").lower()
                        ]
                        
                        if matching_reports:
                            filtered_folders_data.append({
                                "folder": folder,
                                "reports": matching_reports
                            })
            else:
                for folder in self.available_folders:
                    folder_id = folder.get("id")
                    filtered_folders_data.append({
                        "folder": folder,
                        "reports": self.reports_by_folder.get(folder_id, [])
                    })
        
        if not filtered_folders_data and search_term:
            placeholder = ctk.CTkLabel(
                self.tree_container,
                text=f"No results found for '{search_term}'",
                text_color="gray",
                font=ctk.CTkFont(size=12)
            )
            placeholder.grid(row=0, column=0, pady=30)
            return
        
        # ✅ CRITICAL FIX: Create virtual tree with CORRECT parameter name
        if not self.virtual_tree:
            self.virtual_tree = VirtualTreeView(
                parent_frame=self.tree_container,
                item_height=50,
                buffer_items=5
            )
            
            # Setup callbacks
            self.virtual_tree.on_folder_checkbox = self._on_folder_checkbox_changed_virtual
            self.virtual_tree.on_report_checkbox = self._on_report_checkbox_changed_virtual
            self.virtual_tree.on_folder_expand = self._on_folder_expand_virtual

        # ✅ NEW: Pass current selection state to virtual tree
        selected_report_ids = set(self.selected_items.keys())
        self.virtual_tree.set_items(filtered_folders_data, selected_report_ids)
        
        # Store tree_items for compatibility with existing code
        for idx, folder_data in enumerate(filtered_folders_data):
            folder_id = folder_data["folder"].get("id")
            self.tree_items[folder_id] = {
                "folder": folder_data["folder"],
                "folder_name": folder_data["folder"].get("name", "Unknown"),
                "reports": folder_data["reports"],
                "row_index": idx,
                "report_checkboxes": {}
            }
    
    def _on_folder_checkbox_changed_virtual(self, folder_id: str, checkbox_var: ctk.BooleanVar):
        """
        Handle folder checkbox change from virtual tree.
        ✅ FIXED: Now syncs selection state back to virtual tree.
        """
        if folder_id not in self.tree_items:
            self._log(f"ERROR: Folder {folder_id} not found in tree_items")
            return
        
        is_checked = checkbox_var.get()
        tree_item = self.tree_items[folder_id]
        reports = tree_item.get("reports", [])
        folder_name = tree_item.get("folder_name", "Unknown")
        
        if not reports:
            self._log(f"⚠️ No reports in folder: {folder_name}")
            checkbox_var.set(False)
            return
        
        if is_checked:
            # Select all reports in this folder
            for report in reports:
                report_id = report.get("id")
                report_name = report.get("name", "Unnamed Report")
                
                self.selected_items[report_id] = {
                    "type": "report",
                    "name": report_name,
                    "folder_id": folder_id,
                    "folder_name": folder_name
                }
            
            self._log(f"✅ Selected folder: {folder_name} ({len(reports)} reports)")
        else:
            # Deselect all reports in this folder
            for report in reports:
                report_id = report.get("id")
                
                if report_id in self.selected_items:
                    del self.selected_items[report_id]
            
            self._log(f"❌ Deselected folder: {folder_name}")
        
        # ✅ Update virtual tree selection state
        if self.virtual_tree:
            selected_report_ids = set(self.selected_items.keys())
            self.virtual_tree.update_selection_state(selected_report_ids)
        
        # Update selected panel
        self._refresh_selected_panel()
        
        # Update export button state
        self._update_export_button_state()
    
    def _on_report_checkbox_changed_virtual(self, report_id: str, report_name: str, folder_id: str, checkbox_var: ctk.BooleanVar):
        """
        Handle individual report checkbox change from virtual tree.
        ✅ FIXED: Now syncs selection state back to virtual tree.
        """
        is_checked = checkbox_var.get()
        folder_name = self.tree_items.get(folder_id, {}).get("folder_name", "Unknown")
        
        if is_checked:
            # Add to selection
            self.selected_items[report_id] = {
                "type": "report",
                "name": report_name,
                "folder_id": folder_id,
                "folder_name": folder_name
            }
            self._log(f"✅ Selected: {report_name}")
        else:
            # Remove from selection
            if report_id in self.selected_items:
                del self.selected_items[report_id]
            self._log(f"❌ Deselected: {report_name}")
        
        # ✅ Update virtual tree selection state (updates folder checkbox too)
        if self.virtual_tree:
            selected_report_ids = set(self.selected_items.keys())
            self.virtual_tree.update_selection_state(selected_report_ids)
        
        # Update selected panel
        self._refresh_selected_panel()
        
        # Update export button state
        self._update_export_button_state()


    def _on_report_checkbox_changed(self, report_id: str, report_name: str, folder_id: str, checkbox_var: ctk.BooleanVar):
        """
        Handle individual report checkbox change - LEGACY METHOD.
        
        ✅ FIXED: Always redirects to virtual tree handler (no legacy code).
        This method exists only for backward compatibility.
        """
        # Always use virtual tree handler
        if self.virtual_tree:
            return self._on_report_checkbox_changed_virtual(report_id, report_name, folder_id, checkbox_var)
        
        # Fallback if virtual tree doesn't exist (should never happen)
        self._log("⚠️ Warning: Virtual tree not initialized")


    def _on_folder_expand_virtual(self, folder_id: str):
        """
        Handle folder expand/collapse from virtual tree.
        ✅ Callback for virtual tree view.
        """
        # Virtual tree handles the UI, we just log it
        if folder_id in self.tree_items:
            folder_name = self.tree_items[folder_id].get("folder_name", "Unknown")
            is_expanded = self.virtual_tree and folder_id in self.virtual_tree.expanded_folders
            
            if is_expanded:
                self._log(f"📂 Expanded: {folder_name}")
            else:
                self._log(f"📁 Collapsed: {folder_name}")
        
    
    def _on_folder_checkbox_changed(self, folder_id: str, checkbox_var: ctk.BooleanVar):
        """
        Handle folder checkbox change - LEGACY METHOD.
        
        ✅ FIXED: Always redirects to virtual tree handler (no legacy code).
        This method exists only for backward compatibility.
        """
        # Always use virtual tree handler
        if self.virtual_tree:
            return self._on_folder_checkbox_changed_virtual(folder_id, checkbox_var)
        
        # Fallback if virtual tree doesn't exist (should never happen)
        self._log("⚠️ Warning: Virtual tree not initialized")
    

    # ===== SELECTED PANEL MANAGEMENT =====
    
    def _refresh_selected_panel(self):
        """Refresh the selected items panel - COMPACT VERSION"""
        
        # Clear existing widgets
        for widget in self.selected_container.winfo_children():
            widget.destroy()
        
        if not self.selected_items:
            # Show placeholder
            self.selected_placeholder = ctk.CTkLabel(
                self.selected_container,
                text="No reports selected.\nSelect from left panel.",
                text_color="gray",
                font=ctk.CTkFont(size=11),
                justify="center"
            )
            self.selected_placeholder.grid(row=0, column=0, pady=20)
            
            # Update count
            self.selection_count_label.configure(text="0 reports selected", text_color="gray")
            
            # Disable buttons
            self.clear_selected_button.configure(state="disabled")
            self._update_export_button_state()
            return
        
        # Group items by folder
        items_by_folder = {}
        for item_id, item_data in self.selected_items.items():
            folder_name = item_data.get("folder_name", "Unknown")
            if folder_name not in items_by_folder:
                items_by_folder[folder_name] = []
            items_by_folder[folder_name].append({
                "id": item_id,
                "name": item_data.get("name", "Unnamed")
            })
        
        # Create items grouped by folder
        row = 0
        for folder_name, items in sorted(items_by_folder.items()):
            # Folder header - ULTRA COMPACT
            folder_header = ctk.CTkFrame(self.selected_container, fg_color="#333333", corner_radius=2)
            folder_header.grid(row=row, column=0, sticky="ew", padx=3, pady=(0, 0))  # ✅ MINIMAL padding
            folder_header.grid_columnconfigure(0, weight=1)
            
            folder_label = ctk.CTkLabel(
                folder_header,
                text=f"📁 {folder_name} ({len(items)})",
                font=ctk.CTkFont(size=10, weight="bold"),  # ✅ SMALLER font
                anchor="w"
            )
            folder_label.grid(row=0, column=0, sticky="ew", padx=6, pady=2)  # ✅ TIGHT padding
            
            row += 1
            
            # Report items - ULTRA COMPACT
            for item in sorted(items, key=lambda x: x["name"]):
                item_frame = ctk.CTkFrame(self.selected_container, fg_color="#2b2b2b", corner_radius=2)
                item_frame.grid(row=row, column=0, sticky="ew", padx=(8, 3), pady=0)  # ✅ NO vertical gap!
                item_frame.grid_columnconfigure(0, weight=1)
                
                item_label = ctk.CTkLabel(
                    item_frame,
                    text=f" 📄 {item['name'][:50]}{'...' if len(item['name']) > 50 else ''}",  # ✅ TRUNCATE long names
                    font=ctk.CTkFont(size=9),  # ✅ SMALLER font
                    anchor="w"
                )
                item_label.grid(row=0, column=0, sticky="ew", padx=6, pady=1)  # ✅ MINIMAL padding
                
                # Remove button - TINY
                remove_btn = ctk.CTkButton(
                    item_frame,
                    text="×",  # ✅ Single character
                    width=18,  # ✅ TINY
                    height=16,  # ✅ TINY
                    fg_color="transparent",
                    hover_color="#d32f2f",
                    font=ctk.CTkFont(size=12),
                    command=lambda item_id=item['id']: self._remove_item_from_selected(item_id)
                )
                remove_btn.grid(row=0, column=1, padx=2, pady=1)  # ✅ MINIMAL padding
                
                row += 1
        
        # Update count
        count = len(self.selected_items)
        self.selection_count_label.configure(
            text=f"{count} report{'s' if count != 1 else ''} selected",
            text_color="#1f6aa5"
        )
        
        # Enable buttons
        self.clear_selected_button.configure(state="normal")
        self._update_export_button_state()
            
    def _remove_item_from_selected(self, item_id: str):
        """
        Remove a single item from selected panel.
        
        ✅ FIXED: Now properly updates both report AND folder checkboxes in virtual tree.
        """
        if item_id not in self.selected_items:
            return
        
        item_data = self.selected_items[item_id]
        item_name = item_data.get("name", "Unknown")
        folder_id = item_data.get("folder_id")
        
        # Remove from selected items
        del self.selected_items[item_id]
        
        self._log(f"❌ Removed: {item_name}")
        
        # ✅ This now triggers the re-render via update_selection_state()
        if self.virtual_tree:
            selected_report_ids = set(self.selected_items.keys())
            self.virtual_tree.update_selection_state(selected_report_ids)
        
        # Refresh selected panel
        self._refresh_selected_panel()
        
        # Update export button state
        self._update_export_button_state()
    
    # ===== ACTION BUTTONS =====
    
    def _clear_all_selected(self):
        """
        Clear all selected items.
        
        ✅ FIXED: Works with virtual tree view (no direct checkbox access).
        """
        if not self.selected_items:
            return
        
        count = len(self.selected_items)
        
        # Clear selected items dictionary
        self.selected_items.clear()
        
        self._log(f"🗑️ Cleared all selections ({count} reports)")
        
        # ✅ Update virtual tree selection state (this will uncheck all checkboxes)
        if self.virtual_tree:
            self.virtual_tree.update_selection_state(set())  # Empty set = nothing selected
        
        # Refresh selected panel
        self._refresh_selected_panel()
        
        # Update export button state
        self._update_export_button_state()
    
    def _reset_all_selections(self):
        """Reset all selections - same as clear all"""
        if not self.selected_items:
            messagebox.showinfo("No Selection", "No reports are currently selected.")
            return
        
        result = messagebox.askyesno(
            "Reset Selection",
            f"Reset all selections? This will clear {len(self.selected_items)} selected report(s)."
        )
        
        if result:
            self._clear_all_selected()
    
    # ===== BROWSE SAVE LOCATION =====
    
    def _browse_save_location(self):
        """Browse for save location"""
        
        # Get filename from entry
        filename = self.filename_entry.get().strip()
        if not filename:
            filename = f"salesforce_reports_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.zip"
        
        if not filename.endswith('.zip'):
            filename += '.zip'
        
        # Open directory dialog
        directory = filedialog.askdirectory(
            title="Select Save Location"
        )
        
        if directory:
            # Build full path
            full_path = os.path.join(directory, filename)
            self.output_zip_path = full_path
            
            # Update location entry
            self.location_entry.configure(state="normal")
            self.location_entry.delete(0, "end")
            self.location_entry.insert(0, directory)
            self.location_entry.configure(state="readonly")
            
            self._log(f"💾 Save location: {directory}")
            self._log(f"📦 Full path: {full_path}")
            
            self._update_export_button_state()
    
    def _update_export_button_state(self):
        """
        Enable/disable export button based on conditions.
        
        IMPROVED: Uses atomic state checks and better error handling.
        """
        # ✅ IMPROVED: Atomic state checks
        with self.data_lock:
            has_session = self.session_info is not None
            has_path = self.output_zip_path is not None
            has_selection = len(self.selected_items) > 0
        
        # ✅ IMPROVED: Use atomic state getter
        export_state = self._get_export_state()
        is_busy = self._is_ui_busy() or self._is_export_busy()
        
        # Debug logging
        print(f"🔍 Export Button State Check:")
        print(f"   Session: {has_session}")
        print(f"   Path: {has_path}")
        print(f"   Selection: {has_selection} ({len(self.selected_items)} items)")
        print(f"   Export State: {export_state}")
        print(f"   Busy: {is_busy}")
        
        # Can only export if ALL conditions met AND not busy
        can_export = has_session and has_path and has_selection and not is_busy
        
        print(f"   ✅ Can Export: {can_export}")
        
        # Update button state on main thread
        def update_btn():
            try:
                # ✅ SAFETY: Double-check state hasn't changed
                current_state = self._get_export_state()
                if current_state != "idle":
                    # State changed while scheduling - button should stay disabled
                    self.export_button.configure(state="disabled")
                    print(f"   🔴 Export button DISABLED (state changed to {current_state})")
                    return
                
                if can_export:
                    self.export_button.configure(state="normal")
                    print(f"   🟢 Export button ENABLED")
                else:
                    self.export_button.configure(state="disabled")
                    print(f"   🔴 Export button DISABLED")
            except Exception as e:
                print(f"   ⚠️ Button update error: {e}")
        
        # Execute on main thread
        self._safe_ui_update(update_btn)
        
    # ===== EXPORT OPERATIONS =====
    
    # main_app.py - REPLACE _cancel_export (around line 1050)

    def _cancel_export(self):
        """
        Cancel the ongoing export operation.
        
        FIXED: Detects if export already completed.
        """
        # Check actual state
        export_state = self._get_export_state()
        
        print(f"🛑 Cancel clicked - current state: {export_state}")
        
        # ✅ NEW: If already idle, export already finished - just reset UI
        if export_state == "idle":
            print("⚠️ Export already completed or idle")
            self._reset_export_state()
            self._set_export_ui_state(True)
            self._refresh_button_visibility()
            return
        
        if export_state != "running":
            print(f"⚠️ Cannot cancel - export state is '{export_state}'")
            return
        
        # Check if already cancelling
        if self.export_cancel_event.is_set():
            print("⚠️ Export already cancelling")
            return
        
        # ✅ Set cancel event
        self.export_cancel_event.set()
        
        # ✅ Transition to "cancelling" state
        self._set_export_state("cancelling")
        
        self._log("🛑 Cancelling export...")
        
        # Update UI
        self.progress_label.configure(
            text="Cancelling export... Please wait.",
            text_color="orange"
        )
        
        # Update button
        self.cancel_button.configure(
            state="disabled",
            text="🛑 Cancelling..."
        )
        
        print("✅ Cancel event set")
        
    # main_app.py - REPLACE _start_export method (around line 1100)

    def _start_export(self):
        """
        Start the export process.
        
        IMPROVED: Proper state management with atomic transitions.
        """
        # ✅ GUARD: Set dialog flag atomically
        with self.state_lock:
            if self._showing_dialog:
                print("⚠️ Dialog already showing")
                return
            
            if self._is_export_busy():
                print("⚠️ Export already busy")
                return
            
            self._showing_dialog = True
        
        # Validation checks
        if not self.session_info:
            with self.state_lock:
                self._showing_dialog = False
            messagebox.showwarning("Not Logged In", "Please login first.")
            return
        
        if not self.output_zip_path:
            with self.state_lock:
                self._showing_dialog = False
            messagebox.showwarning("No Location", "Please select a save location.")
            return
        
        if not self.selected_items:
            with self.state_lock:
                self._showing_dialog = False
            messagebox.showwarning("No Selection", "Please select at least one report to export.")
            return
        
        # Get filename from entry
        filename = self.filename_entry.get().strip()
        if not filename:
            with self.state_lock:
                self._showing_dialog = False
            messagebox.showwarning("No Filename", "Please enter a filename.")
            return
        
        if not filename.endswith('.zip'):
            filename += '.zip'
        
        # Update full path with current filename
        directory = os.path.dirname(self.output_zip_path)
        self.output_zip_path = os.path.join(directory, filename)
        
        # Confirm export
        count = len(self.selected_items)
        result = messagebox.askyesno(
            "Confirm Export",
            f"Export {count} report(s) to:\n\n{self.output_zip_path}\n\nContinue?"
        )
        
        # ✅ CRITICAL: Clear dialog flag before checking result
        with self.state_lock:
            self._showing_dialog = False
        
        if not result:
            print("ℹ️ Export cancelled by user (dialog)")
            return
        
        # Get list of report IDs
        report_ids = list(self.selected_items.keys())
        
        # ✅ NEW: Generate checkpoint path
        import tempfile
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        self.checkpoint_path = os.path.join(
            tempfile.gettempdir(),
            f"sf_export_checkpoint_{timestamp}.json"
        )
        self.resume_mode = False
        
        # Build reports metadata
        reports_metadata = {}
        with self.data_lock:
            for folder_id, reports in self.reports_by_folder.items():
                for report in reports:
                    report_id = report.get("id")
                    if report_id in report_ids:
                        reports_metadata[report_id] = {
                            "id": report_id,
                            "name": report.get("name", report_id),
                            "reportFormat": report.get("reportFormat", "TABULAR")
                        }
        
        # Start export
        self._start_export_internal(report_ids, reports_metadata, resume_mode=False)

    def _start_export_internal(
        self,
        report_ids: List[str],
        reports_metadata: Dict[str, Dict],
        resume_mode: bool = False
    ):
        """
        Internal method to start export (used by both new exports and resume).
        
        ✅ NEW: Verifies session before starting.
        
        Args:
            report_ids: List of report IDs to export
            reports_metadata: Metadata for reports
            resume_mode: True if resuming from checkpoint
        """
        # ✅ NEW: Verify session before export
        self._log("🔍 Verifying session...")
        
        if not self.session_manager.verify_and_refresh_if_needed():
            self._log("❌ Session verification failed")
            messagebox.showerror(
                "Session Error",
                "Could not verify Salesforce session.\n\n"
                "Please log out and log back in."
            )
            return
        
        # Get potentially refreshed session info
        current_session = self.session_manager.get_session_info()
        if current_session:
            with self.data_lock:
                self.session_info["session_id"] = current_session.get("session_id")
        
        self._log("✅ Session verified")
        
        # ✅ CRITICAL: Transition to "running" state atomically
        self._set_export_state("running")
        
        # Clear cancel event (fresh start)
        self.export_cancel_event.clear()
        
        # Update UI
        self._set_export_ui_state(False)
        
        count = len(report_ids)
        action = "Resuming" if resume_mode else "Starting"
        self._log(f"🚀 {action} export of {count} selected reports...")
        self._log(f"📦 Destination: {self.output_zip_path}")
        
        if resume_mode:
            self._log(f"📂 Using checkpoint: {self.checkpoint_path}")
        
        # Initialize progress tracker
        if resume_mode and self.pending_checkpoint:
            # Start from where we left off
            completed_before = self.pending_checkpoint["progress"]["completed"]
            self.progress_tracker.start(self.pending_checkpoint["progress"]["total"])
            self.progress_tracker.completed = completed_before
        else:
            self.progress_tracker.start(len(report_ids))
        
        # ✅ Update buttons to show cancel button
        self._refresh_button_visibility()
        
        # Force update
        self.update_idletasks()
        
        # ✅ Start export in BACKGROUND THREAD (UI stays responsive)
        thread = threading.Thread(
            target=self._export_worker_with_checkpoint,
            args=(report_ids, reports_metadata, resume_mode),
            daemon=True
        )
        thread.start()
        
        print("✅ Export thread started")
 
    # main_app.py - Add this NEW method after _start_export_internal

    def _export_worker_with_checkpoint(
        self,
        report_ids: List[str],
        reports_metadata: Dict[str, Dict],
        resume_mode: bool = False
    ):
        """
        Background worker for export with checkpoint support.
        
        ✅ NEW: Passes checkpoint_path to exporter for crash recovery.
        ✅ NEW: Monitors session during export.
        
        Args:
            report_ids: List of report IDs to export
            reports_metadata: Metadata for reports
            resume_mode: True if resuming from checkpoint
        """
        try:
            # ✅ NEW: Check session before starting
            if not self.session_manager.verify_and_refresh_if_needed():
                raise Exception("Session verification failed before export")
            
            session_id = self.session_info.get("session_id")
            instance_url = self.session_info.get("instance_url")
            
            # ✅ NEW: Track last session check time
            last_session_check = time.time()
            SESSION_CHECK_INTERVAL = 300  # Check every 5 minutes
            
            def progress_callback(done, total, report_name=None):
                """Progress callback - called when report starts/completes"""
                nonlocal last_session_check
                
                # ✅ NEW: Periodically verify session during long exports
                current_time = time.time()
                if current_time - last_session_check > SESSION_CHECK_INTERVAL:
                    self.update_queue.put(("log", "🔍 Verifying session..."))
                    
                    if not self.session_manager.verify_and_refresh_if_needed():
                        self.update_queue.put(("log", "⚠️ Session verification failed during export"))
                        # Export will likely fail soon, but let it try
                    else:
                        self.update_queue.put(("log", "✅ Session still valid"))
                        
                        # Update session_id in case it was refreshed
                        new_session = self.session_manager.get_session_info()
                        if new_session:
                            session_id = new_session.get("session_id")
                    
                    last_session_check = current_time
                
                if report_name:
                    self.update_queue.put(("progress_with_name", (done, total, report_name)))
                    self.update_queue.put(("log", f"  📥 Downloading: {report_name}"))
                    return
                
                self.update_queue.put(("progress", (done, total)))
                
                if done > 0 and done <= total:
                    percentage = int((done / total) * 100)
                    speed = self.progress_tracker.get_speed()
                    
                    if speed > 0.5:
                        self.update_queue.put(("log", f"  ✅ Completed: {done}/{total} ({percentage}%) • {speed:.1f} reports/sec"))
                    else:
                        self.update_queue.put(("log", f"  ✅ Completed: {done}/{total} ({percentage}%)"))
            
            # ✅ NEW: Use current session_id (might be refreshed)
            exporter = SalesforceReportExporter(
                session_id,
                instance_url,
                progress_callback=progress_callback
            )
            
            # Log export start
            action = "Resuming" if resume_mode else "Starting"
            self.update_queue.put(("log", f"🚀 {action} concurrent export of {len(report_ids)} reports..."))
            
            if resume_mode:
                self.update_queue.put(("log", f"📂 Checkpoint: {self.checkpoint_path}"))
            
            # Check cancellation before export
            if self.export_cancel_event.is_set():
                self.update_queue.put(("export_cancelled", None))
                return
            
            # ✅ MAIN EXPORT: With checkpoint support
            result = exporter.export_selected_reports_to_zip_concurrent(
                self.output_zip_path,
                report_ids,
                max_workers=10,
                cancel_event=self.export_cancel_event,
                retry_attempts=3,
                reports_metadata=reports_metadata,
                checkpoint_path=self.checkpoint_path,  # ✅ Checkpoint enabled
                resume_mode=resume_mode  # ✅ Resume mode
            )
            
            self.update_queue.put(("export_complete", result))
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            self.update_queue.put(("log", f"❌ Export error:\n{error_details}"))
            self.update_queue.put(("export_error", str(e)))


    def _start_export_safe(self):
        """
        Safe wrapper for _start_export() to prevent double-triggering.
        Called by keyboard shortcuts and button clicks.
        
        IMPROVED: Uses atomic state checks.
        """
        # ✅ IMPROVED: Check if already busy or showing dialog
        if self._is_export_busy():
            print("⚠️ Export already running, ignoring duplicate trigger")
            return
        
        if self._is_ui_busy():
            print("⚠️ UI is busy, ignoring export trigger")
            return
        
        with self.state_lock:
            if self._showing_dialog:
                print("⚠️ Dialog already open, ignoring export trigger")
                return
        
        # All checks passed - proceed with export
        self._start_export()
        
    def _export_worker(self, report_ids: List[str]):
        """
        Background worker for export with concurrent downloads.
        
        ✅ OPTIMIZED: Passes report metadata to avoid redundant API calls.
        """
        try:
            session_id = self.session_info.get("session_id")
            instance_url = self.session_info.get("instance_url")
            
            # ✅ NEW: Build metadata dict from already-loaded data
            reports_metadata = {}
            
            with self.data_lock:
                # Extract metadata from reports_by_folder (already have this!)
                for folder_id, reports in self.reports_by_folder.items():
                    for report in reports:
                        report_id = report.get("id")
                        if report_id in report_ids:
                            reports_metadata[report_id] = {
                                "id": report_id,
                                "name": report.get("name", report_id),
                                "reportFormat": report.get("reportFormat", "TABULAR")
                            }
            
            def progress_callback(done, total, report_name=None):
                """Progress callback - called when report starts/completes"""
                if report_name:
                    self.update_queue.put(("progress_with_name", (done, total, report_name)))
                    self.update_queue.put(("log", f"  🔥 Downloading: {report_name}"))
                    return
                
                self.update_queue.put(("progress", (done, total)))
                
                if done > 0 and done <= total:
                    percentage = int((done / total) * 100)
                    speed = self.progress_tracker.get_speed()
                    
                    if speed > 0.5:
                        self.update_queue.put(("log", f"  ✅ Completed: {done}/{total} ({percentage}%) • {speed:.1f} reports/sec"))
                    else:
                        self.update_queue.put(("log", f"  ✅ Completed: {done}/{total} ({percentage}%)"))
            
            exporter = SalesforceReportExporter(
                session_id,
                instance_url,
                progress_callback=progress_callback
            )
            
            # Log export start
            self.update_queue.put(("log", f"🚀 Starting concurrent export of {len(report_ids)} reports..."))
            
            # Check cancellation before export
            if self.export_cancel_event.is_set():
                self.update_queue.put(("export_cancelled", None))
                return
            
            # ✅ OPTIMIZED: Pass metadata to avoid redundant API calls
            result = exporter.export_selected_reports_to_zip_concurrent(
                self.output_zip_path,
                report_ids,
                max_workers=10,
                cancel_event=self.export_cancel_event,
                retry_attempts=3,
                reports_metadata=reports_metadata  # ✅ NEW: Pass cached metadata
            )
            
            self.update_queue.put(("export_complete", result))
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            self.update_queue.put(("log", f"❌ Export error:\n{error_details}"))
            self.update_queue.put(("export_error", str(e)))
    
    def _on_export_progress(self, progress_data):
        """Handle export progress update - updates after EACH report"""
        done, total = progress_data
        
        # Always update tracker (for speed calculations)
        self.progress_tracker.update(done)
        
        # Update UI for EVERY report
        if total > 0:
            progress = done / total
            self.progress_bar.set(progress)
            
            # Get enhanced progress text with ETA and speed
            progress_text = self.progress_tracker.get_progress_text()
            self.progress_label.configure(
                text=progress_text,
                text_color="#1f6aa5"
            )
    
    
    def _on_export_progress_with_name(self, progress_data):
        """
        Handle progress update with report name (download starting).
        Shows which report is currently being downloaded.
        """
        done, total, report_name = progress_data
        
        # ✅ Show current report in progress label
        if total > 0:
            progress = done / total
            percentage = int(progress * 100)
            
            # Truncate long report names
            display_name = report_name[:40] + "..." if len(report_name) > 40 else report_name
            
            # Update progress label with current report
            self.progress_label.configure(
                text=f"📥 Downloading: {display_name} ({done}/{total} - {percentage}%)",
                text_color="#1f6aa5"
            )
    
    # main_app.py - REPLACE _on_export_complete method (around line 1350)

    # main_app.py - REPLACE ENTIRE _on_export_complete method (around line 1400)

    def _on_export_complete(self, result: Dict):
        """
        Handle export completion (including cancellation and resume).
        
        FIXED: Simplified guards to prevent blocking legitimate completions.
        """
        print("📥 Export completion handler called")
        print(f"   Result: {result.get('total')} total, {result.get('cancelled')} cancelled")
        
        # ✅ SIMPLIFIED: Only prevent double-processing, don't check state
        with self.state_lock:
            if self._showing_dialog:
                print("⚠️ Dialog already showing, ignoring duplicate")
                return
            
            # Set flag to prevent double-processing
            self._showing_dialog = True
        
        try:
            # Extract result data
            total = result.get("total", 0)
            failed = result.get("failed", [])
            successful = result.get("successful", [])
            zip_path = result.get("zip", "")
            was_cancelled = result.get("cancelled", False)
            completed = result.get("completed", len(successful))
            was_resumed = result.get("resumed", False)
            
            # ✅ CRITICAL: Also check if cancel event is set
            if not was_cancelled:
                was_cancelled = self.export_cancel_event.is_set()
            
            # ✅ Calculate statistics
            elapsed = self.progress_tracker.get_elapsed_seconds()
            elapsed_formatted = self.progress_tracker.format_time(elapsed)
            avg_speed = completed / elapsed if elapsed > 0 else 0
            
            # ✅ CRITICAL: Reset state FIRST (before showing dialog)
            self._reset_export_state()
            self._set_export_ui_state(True)
            
            # Update progress bar
            if was_cancelled:
                progress_value = completed / total if total > 0 else 0
                self.progress_bar.set(progress_value)
                self.progress_label.configure(
                    text=f"⚠️ Export cancelled. Saved {completed}/{total} reports",
                    text_color="orange"
                )
            else:
                self.progress_bar.set(1.0)
                completion_text = self.progress_tracker.get_completion_text()
                self.progress_label.configure(
                    text=completion_text,
                    text_color="green"
                )
            
            # Force UI update BEFORE dialog
            self.update_idletasks()
            
            # Log summary
            self._log("=" * 50)
            if was_cancelled:
                self._log(f"⚠️ EXPORT CANCELLED BY USER")
            elif was_resumed:
                self._log(f"✅ RESUMED EXPORT COMPLETED")
            else:
                self._log(f"✅ EXPORT COMPLETED SUCCESSFULLY")
            
            self._log(f"📊 Total: {total} reports")
            self._log(f"⏱️ Duration: {elapsed_formatted}")
            if avg_speed > 0:
                self._log(f"⚡ Speed: {avg_speed:.2f} reports/sec")
            self._log(f"✔️ Successful: {len(successful)}")
            self._log(f"❌ Failed: {len(failed)}")
            self._log(f"💾 ZIP: {zip_path}")
            self._log("=" * 50)
            
            # Clear pending checkpoint
            if was_resumed and self.pending_checkpoint:
                self.pending_checkpoint = None
            
            # ✅ Show appropriate dialog
            if was_cancelled:
                self._handle_cancelled_export(
                    completed, total, successful, failed, 
                    elapsed_formatted, avg_speed, zip_path, was_resumed
                )
            else:
                self._handle_successful_export(
                    total, successful, failed, 
                    elapsed_formatted, avg_speed, zip_path, was_resumed
                )
        
        finally:
            # ✅ CRITICAL: Always clear dialog flag in finally block
            with self.state_lock:
                self._showing_dialog = False
            
            print("✅ Completion handler finished")
    
    # main_app.py - REPLACE _handle_cancelled_export (around line 1500)

    def _handle_cancelled_export(self, completed, total, successful, failed, elapsed_formatted, avg_speed, zip_path, was_resumed):
        """
        Handle UI flow when export was cancelled.
        
        FIXED: Simpler dialog flow, always shows.
        """
        # Build message
        message = f"⚠️ Export was cancelled"
        if was_resumed:
            message += " (resumed export)"
        message += ".\n\n"
        
        message += f"📊 Statistics:\n"
        message += f"  • Completed: {completed}/{total} reports\n"
        message += f"  • Successful: {len(successful)}\n"
        message += f"  • Failed: {len(failed)}\n"
        message += f"  • Duration: {elapsed_formatted}\n"
        if avg_speed > 0:
            message += f"  • Speed: {avg_speed:.1f} reports/sec\n"
        message += f"\n💾 Partial export saved to:\n{zip_path}\n\n"
        
        if self.checkpoint_path:
            message += f"💡 Progress saved! You can resume later.\n\n"
        
        message += f"Keep this partial export?"
        
        # Ask user
        keep_result = messagebox.askyesno(
            "Export Cancelled",
            message,
            icon='warning'
        )
        
        if keep_result is False:  # Delete
            try:
                os.remove(zip_path)
                self._log(f"🗑️ Partial export deleted")
                
                if self.checkpoint_path and os.path.exists(self.checkpoint_path):
                    os.remove(self.checkpoint_path)
                    self._log(f"🗑️ Checkpoint deleted")
                
                messagebox.showinfo("Deleted", "Partial export deleted.")
            except Exception as e:
                messagebox.showerror("Error", f"Could not delete:\n{str(e)}")
        
        elif keep_result is True:  # Keep
            self._ask_open_folder(zip_path)
        
        print("✅ Cancelled handler finished")
    
    # main_app.py - REPLACE _handle_successful_export (around line 1550)

    def _handle_successful_export(self, total, successful, failed, elapsed_formatted, avg_speed, zip_path, was_resumed):
        """
        Handle UI flow when export completed successfully.
        
        FIXED: Simpler dialog flow, always shows.
        """
        success_rate = (len(successful) / total * 100) if total > 0 else 0
        
        # Build success message
        message = "✅ Export completed successfully"
        if was_resumed:
            message += " (resumed from checkpoint)"
        message += "!\n\n"
        
        message += f"📊 Statistics:\n"
        message += f"  • Total Reports: {total}\n"
        message += f"  • Successful: {len(successful)}\n"
        message += f"  • Failed: {len(failed)}\n"
        message += f"  • Success Rate: {success_rate:.1f}%\n"
        message += f"  • Duration: {elapsed_formatted}\n"
        if avg_speed > 0:
            message += f"  • Speed: {avg_speed:.1f} reports/sec\n"
        message += f"\n💾 ZIP saved to:\n{zip_path}"
        
        # Show success dialog
        messagebox.showinfo("Export Complete", message)
        
        # Delete checkpoint on success
        if self.checkpoint_path and os.path.exists(self.checkpoint_path):
            try:
                os.remove(self.checkpoint_path)
                self._log(f"🗑️ Checkpoint deleted")
            except:
                pass
        
        # Ask about opening folder
        self._ask_open_folder(zip_path)
        
        print("✅ Success handler finished")
    
    def _ask_open_folder(self, zip_path):
        """
        Ask user if they want to open the folder containing the export.
        
        IMPROVED: Better error handling.
        """
        import subprocess
        import platform
        import os
        
        result = messagebox.askyesno(
            "Open Folder?", 
            "Would you like to open the folder containing the exported file?"
        )
        
        if result:
            folder = os.path.dirname(zip_path)
            
            try:
                if platform.system() == "Windows":
                    os.startfile(folder)
                elif platform.system() == "Darwin":  # macOS
                    subprocess.Popen(["open", folder])
                else:  # Linux
                    subprocess.Popen(["xdg-open", folder])
                
                self._log(f"📂 Opened folder: {folder}")
                
            except Exception as e:
                self._log(f"❌ Could not open folder: {str(e)}")
                messagebox.showerror("Error", f"Could not open folder:\n{str(e)}")
    
    def _on_export_error(self, error_msg: str):
        """
        Handle export error with proper state cleanup.
        
        IMPROVED: Ensures state is reset even on errors.
        """
        print(f"❌ Export error handler called: {error_msg}")
        
        # ✅ CRITICAL: Reset state immediately
        self._reset_export_state()
        
        # Update UI
        self._set_export_ui_state(True)
        self._refresh_button_visibility()
        self.update_idletasks()
        
        self.progress_bar.set(0)
        
        # Get elapsed time
        elapsed = self.progress_tracker.get_elapsed_seconds()
        elapsed_formatted = self.progress_tracker.format_time(elapsed) if elapsed > 0 else "0s"
        
        self.progress_label.configure(
            text=f"❌ Export failed after {elapsed_formatted}",
            text_color="red"
        )
        
        self._log("=" * 50)
        self._log(f"❌ EXPORT FAILED")
        self._log(f"⏱️  Failed after: {elapsed_formatted}")
        self._log(f"📊 Error: {error_msg}")
        self._log("=" * 50)
        
        # Provide helpful error message
        helpful_msg = self._get_helpful_error_message(error_msg)
        
        # ✅ GUARD: Check if already showing dialog
        with self.state_lock:
            if self._showing_dialog:
                print("⚠️ Error dialog already showing")
                return
            self._showing_dialog = True
        
        try:
            messagebox.showerror(
                "Export Failed",
                f"Export failed:\n\n{error_msg}\n\n{helpful_msg}"
            )
        finally:
            # ✅ CRITICAL: Clear dialog flag
            with self.state_lock:
                self._showing_dialog = False
        
        print("✅ Error handler finished")
    
    def _get_helpful_error_message(self, error_msg: str) -> str:
        """Get helpful suggestion based on error message"""
        error_lower = error_msg.lower()
        
        if "session" in error_lower or "authentication" in error_lower:
            return "💡 Suggestion: Your session may have expired. Try logging out and back in."
        
        elif "network" in error_lower or "connection" in error_lower or "timeout" in error_lower:
            return "💡 Suggestion: Check your internet connection and try again."
        
        elif "permission" in error_lower or "access" in error_lower:
            return "💡 Suggestion: You may not have permission to access these reports. Check with your Salesforce admin."
        
        elif "limit" in error_lower or "exceeded" in error_lower:
            return "💡 Suggestion: Salesforce API limits may have been reached. Try exporting fewer reports at once or wait a few minutes."
        
        elif "cancelled" in error_lower:
            return "ℹ️ Export was cancelled by user."
        
        else:
            return "💡 Suggestion: Try exporting fewer reports at once, or check the activity log for more details."
    
    def _set_export_ui_state(self, enabled: bool):
        """
        Enable/disable UI during export.
        
        IMPROVED: Uses atomic state management and better button handling.
        """
        state = "normal" if enabled else "disabled"
        
        try:
            self.logout_button.configure(state=state)
            self.browse_button.configure(state=state)
            # self.all_folders_btn.configure(state=state)
            self.filename_entry.configure(state=state)
            
            if enabled:
                # ✅ Export finished - restore normal UI
                self.filename_entry.configure(state="normal")
                
                # ✅ CRITICAL: Use centralized button refresh
                self._refresh_button_visibility()
                
            else:
                # ✅ Export starting - disable everything
                self.filename_entry.configure(state="disabled")
                
                # Buttons handled by _refresh_button_visibility()
            
            # Force UI update
            self.update_idletasks()
            
        except Exception as e:
            print(f"⚠️ UI state update error: {e}")
    
    # ===== QUEUE PROCESSING =====
    def destroy(self):
        """
        Clean up resources before window destruction.
        ✅ NEW: Properly cleanup virtual tree.
        """
        try:
            # Clean up virtual tree
            if self.virtual_tree:
                self.virtual_tree.clear()
                self.virtual_tree = None
        except:
            pass
        
        # Call parent destroy
        super().destroy()  

    def _process_queue(self):
        """Process updates from background threads"""
        try:
            while True:
                item = self.update_queue.get_nowait()
                
                if isinstance(item, tuple):
                    event_type = item[0]
                    data = item[1] if len(item) > 1 else None
                    
                    if event_type == "search_complete":
                        self._on_search_complete(data)
                    elif event_type == "search_error":
                        self._on_search_error(data)
                    elif event_type == "search_cancelled":
                        self._on_search_cancelled()
                    elif event_type == "progress_with_name":
                        self._on_export_progress_with_name(data)
                    elif event_type == "progress":
                        self._on_export_progress(data)
                    elif event_type == "export_complete":
                        self._on_export_complete(data)
                    elif event_type == "export_error":
                        self._on_export_error(data)
                    elif event_type == "log":
                        self._log(data)
        
        except queue.Empty:
            pass
        
        # Schedule next check
        self.after(100, self._process_queue)

# ===== NO STANDALONE ENTRY POINT =====
# This app is now launched via main.py's AppLauncher
# Do not run this file directly

if __name__ == "__main__":
    print("⚠️  ERROR: Do not run main_app.py directly!")
    print("✅ Run main.py instead to start the application properly.")
    import sys
    sys.exit(1)