# main_app.py - REDESIGNED VERSION
# Salesforce Report Exporter with Tree View and Dual-Panel Selection

import customtkinter as ctk
import threading
import queue
import os
import subprocess
import platform
import datetime
import time
from login_window import LoginWindow
from tkinter import filedialog, messagebox, ttk
from typing import Optional, List, Dict, Any, Callable
from login_window import LoginWindow
from exporter import SalesforceReportExporter

class VirtualTreeView:
    """
    Virtual scrolling tree view for handling 10,000+ items.
    Only renders visible items to prevent UI freezing.
    """
    
    def __init__(
        self,
        parent_frame: ctk.CTkScrollableFrame,
        item_height: int = 40,
        visible_items: int = 15
    ):
        self.parent_frame = parent_frame
        self.item_height = item_height
        self.visible_items = visible_items
        
        # Data storage
        self.all_items = []  # List of all folder items
        self.visible_widgets = {}  # Currently rendered widgets
        self.expanded_folders = set()  # Track expanded folder IDs
        
        # Scroll tracking
        self.last_scroll_pos = 0
        self.render_buffer = 5  # Extra items to render above/below view
        
        # Setup scroll monitoring
        self.parent_frame.bind("<Configure>", self._on_scroll)
        
    def set_items(self, items: List[Dict]):
        """Set all items to be displayed"""
        self.all_items = items
        self._render_visible_items()
    
    def _on_scroll(self, event=None):
        """Handle scroll event - render visible items"""
        # Get current scroll position
        try:
            # For CTkScrollableFrame, we need to check the canvas
            canvas = self.parent_frame._parent_canvas
            scroll_pos = canvas.yview()[0]
            
            # Only re-render if scroll changed significantly
            if abs(scroll_pos - self.last_scroll_pos) > 0.05:
                self.last_scroll_pos = scroll_pos
                self._render_visible_items()
        except:
            pass
    
    def _render_visible_items(self):
        """Render only the visible items in the viewport"""
        if not self.all_items:
            return
        
        # Calculate visible range
        try:
            canvas = self.parent_frame._parent_canvas
            canvas_height = canvas.winfo_height()
            scroll_y = canvas.yview()[0]
            
            total_height = len(self.all_items) * self.item_height
            visible_start_y = scroll_y * total_height
            visible_end_y = visible_start_y + canvas_height
            
            # Calculate item indices
            start_idx = max(0, int(visible_start_y / self.item_height) - self.render_buffer)
            end_idx = min(len(self.all_items), int(visible_end_y / self.item_height) + self.render_buffer + 1)
            
        except:
            # Fallback: render first visible_items
            start_idx = 0
            end_idx = min(len(self.all_items), self.visible_items + self.render_buffer)
        
        # Track which widgets should exist
        should_exist = set(range(start_idx, end_idx))
        current_exist = set(self.visible_widgets.keys())
        
        # Remove widgets that are out of view
        to_remove = current_exist - should_exist
        for idx in to_remove:
            if idx in self.visible_widgets:
                widget = self.visible_widgets[idx]
                widget.destroy()
                del self.visible_widgets[idx]
        
        # Create widgets that should be visible but don't exist
        to_create = should_exist - current_exist
        for idx in sorted(to_create):
            if idx < len(self.all_items):
                self._create_item_widget(idx)
    
    def _create_item_widget(self, idx: int):
        """Create widget for item at index - Override in parent class"""
        pass
    
    def toggle_folder(self, folder_id: str):
        """Toggle folder expansion state"""
        if folder_id in self.expanded_folders:
            self.expanded_folders.remove(folder_id)
        else:
            self.expanded_folders.add(folder_id)
    
    def is_expanded(self, folder_id: str) -> bool:
        """Check if folder is expanded"""
        return folder_id in self.expanded_folders
    
    def clear(self):
        """Clear all items and widgets"""
        for widget in self.visible_widgets.values():
            try:
                widget.destroy()
            except:
                pass
        
        self.visible_widgets.clear()
        self.all_items.clear()
        self.expanded_folders.clear()
        self.last_scroll_pos = 0


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
    
    def __init__(
        self,
        master,  # ← Required master parameter
        session_info: Dict,
        on_logout: Optional[Callable] = None
    ):
        # ← CHANGED: Pass master to Toplevel
        super().__init__(master)
        
        # Store session info and logout callback
        self.session_info = session_info
        self.on_logout_callback = on_logout
        
        # Window setup
        self.title("Salesforce Report Exporter")
        self.geometry("1200x800")
        
        # ← NEW: Make this window modal-like (grab focus)
        self.grab_set()
        
        # Set theme (already set in launcher, but doesn't hurt)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Thread Safety
        self.data_lock = threading.RLock()
        self.ui_lock = threading.RLock()
        self.export_cancel_event = threading.Event()
        
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
        self.is_exporting: bool = False
        self.is_loading: bool = False
        self.search_timer = None 
        
        # Progress tracker
        self.progress_tracker = ExportProgressTracker()
        
        # Queue for thread-safe UI updates
        self.update_queue = queue.Queue()
        
        # Setup UI
        self._setup_ui()
        
        # Center window on screen
        self.after(100, self._center_window)
        
        # Start queue processor
        self._process_queue()
        
        # Bind window close event
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        # Keyboard shortcuts
        self.bind('<Control-e>', lambda e: self._start_export() if not self._is_ui_busy() else None)
        self.bind('<Escape>', lambda e: self._cancel_export() if self.is_exporting else None)
        
        # Window configuration tracking
        self.bind('<Configure>', self._on_window_configure)
        self._last_window_geometry = None
        self._last_export_state = None
        self._configure_timer = None
        
        # Auto-load data after UI is ready
        self.after(500, self._auto_load_data_on_startup)
        
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
        """
        def wrapper():
            with self.ui_lock:
                try:
                    callback(*args, **kwargs)
                except Exception as e:
                    self._log(f"⚠️ UI update error: {str(e)}")
        
        # If we're on main thread, execute immediately
        try:
            if threading.current_thread() is threading.main_thread():
                wrapper()
            else:
                # Schedule on main thread
                self.after(0, wrapper)
        except:
            # Fallback: use queue
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
        """
        # Only process events for the main window (not child widgets)
        if event and event.widget != self:
            return
        
        # ✅ FIX 1: Cancel any pending configure updates (debouncing)
        if hasattr(self, '_configure_timer') and self._configure_timer:
            self.after_cancel(self._configure_timer)
        
        # ✅ FIX 2: Schedule update after window settles (300ms delay)
        self._configure_timer = self.after(300, self._apply_window_configure)

    def _apply_window_configure(self):
        """
        Apply window configuration changes after debounce delay.
        Only updates UI if state actually changed.
        """
        try:
            # Get current geometry
            current_geometry = self.geometry()
            
            # ✅ FIX 3: Only compare size, not position (ignore x,y coordinates)
            # Format: "WIDTHxHEIGHT+X+Y" -> extract "WIDTHxHEIGHT"
            current_size = current_geometry.split('+')[0] if '+' in current_geometry else current_geometry
            last_size = self._last_window_geometry.split('+')[0] if hasattr(self, '_last_window_geometry') and self._last_window_geometry and '+' in self._last_window_geometry else None
            
            # Only act if SIZE actually changed (ignore position changes)
            if current_size == last_size:
                return
            
            self._last_window_geometry = current_geometry
            
            # ✅ FIX 4: Only update button visibility if export state changed
            with self.ui_lock:
                current_export_state = self.is_exporting
            
            # Check if we need to update buttons at all
            if not hasattr(self, '_last_export_state'):
                self._last_export_state = None
            
            # Only update if export state changed OR first run
            if current_export_state == self._last_export_state:
                return  # State unchanged, no need to update buttons
            
            self._last_export_state = current_export_state
            
            # Now update button visibility based on state
            if current_export_state:
                # Should show CANCEL button only
                self.export_button.grid_remove()
                self.cancel_button.grid()
                if self.cancel_button.cget("state") == "disabled":
                    self.cancel_button.configure(text="🛑 Cancelling...")
                else:
                    self.cancel_button.configure(text="🛑 Cancel Export")
            else:
                # Should show EXPORT button only
                self.cancel_button.grid_remove()
                self.cancel_button.configure(state="disabled")
                self.export_button.grid()
                
                # Update export button state
                self._update_export_button_state()
            
            # Force UI refresh
            self.update_idletasks()
            
        except Exception as e:
            # Silently ignore errors during configure (window might be closing)
            pass
        finally:
            # Clear timer reference
            if hasattr(self, '_configure_timer'):
                self._configure_timer = None
            
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
        """Create left panel - Compact layout with fixed search"""
        
        left_panel = ctk.CTkFrame(parent)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        
        # KEY FIX: Row 3 gets weight 1 (expands). Others get weight 0 (fixed).
        left_panel.grid_rowconfigure(0, weight=0) # Header
        left_panel.grid_rowconfigure(1, weight=0) # Button
        left_panel.grid_rowconfigure(2, weight=0) # Search
        left_panel.grid_rowconfigure(3, weight=1) # Tree View (The big list)
        left_panel.grid_columnconfigure(0, weight=1)
        
        # Header (Reduced padding)
        header_label = ctk.CTkLabel(
            left_panel,
            text="Available Items",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        header_label.grid(row=0, column=0, sticky="w", padx=10, pady=(10, 5))
        
        # "All Folders" button (Reduced padding)
        self.all_folders_btn = ctk.CTkButton(
            left_panel,
            text="📁 All Folders",
            command=self._load_all_folders,
            height=30, # Slightly shorter
            fg_color="#1f6aa5",
            hover_color="#144870",
            state="disabled"
        )
        self.all_folders_btn.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 5))
        
        # Search box (Fixed below button)
        search_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        search_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 5))
        search_frame.grid_columnconfigure(0, weight=1)
        
        self.left_search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="🔍 Search folders and reports...",
            height=30
        )
        self.left_search_entry.grid(row=0, column=0, sticky="ew")
        self.left_search_entry.bind("<KeyRelease>", self._on_left_search)
        
        # Tree view container (This will now expand fully)
        self.tree_container = ctk.CTkScrollableFrame(
            left_panel,
            fg_color="#2b2b2b",
            corner_radius=5
        )
        self.tree_container.grid(row=3, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.tree_container.grid_columnconfigure(0, weight=1)
        
        # Placeholder
        self.tree_placeholder = ctk.CTkLabel(
            self.tree_container,
            text="Please login to load folders and reports",
            text_color="gray",
            font=ctk.CTkFont(size=11)
        )
        self.tree_placeholder.grid(row=0, column=0, pady=20)
        
        self.tree_items: Dict[str, Dict] = {}
        # NOTE: Removed VirtualTreeView initialization to fix scrollbar
    
    
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
            command=self._start_export,
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
        """
        Logout and return to login window.
        
        KEY FIX: Releases grab and lets parent handle window destruction.
        """
        
        # Check if busy
        if self._is_ui_busy():
            result = messagebox.askyesno(
                "Operation in Progress",
                "An operation is in progress. Cancel and logout?",
                icon='warning'
            )
            if not result:
                return
            
            # Cancel operations
            self.export_cancel_event.set()
            self.after(500, self._logout)  # Retry after cancellation
            return
        
        # Confirm logout
        result = messagebox.askyesno(
            "Confirm Logout",
            "Are you sure you want to logout?\n\nYou will return to the login screen.",
            icon='question'
        )
        
        if not result:
            return
        
        self._log("🔴 Logging out...")
        
        # ← KEY FIX: Release grab before calling parent callback
        try:
            self.grab_release()
        except:
            pass
        
        # Call parent's logout handler
        # Parent (AppLauncher) will destroy this window and show login
        if self.on_logout_callback:
            try:
                self.on_logout_callback()
            except Exception as e:
                print(f"⚠️ Error in logout callback: {e}")
                # Fallback: destroy ourselves
                try:
                    self.destroy()
                except:
                    pass
        else:
            # No callback provided - just destroy ourselves
            try:
                self.destroy()
            except:
                pass
    
    # ===== LOAD FOLDERS AND REPORTS =====
    
    def _auto_load_data_on_startup(self):
        """Auto-load folders and reports when app starts (user is already logged in)"""
        if not self.session_info:
            self._log("⚠️ No session info available")
            return
        
        # Log session info
        instance = self.session_info.get("instance_url", "")
        api_version = self.session_info.get("api_version", "")
        user_name = self.session_info.get("user_name", "")
        
        self._log(f"✅ Connected to {instance}")
        self._log(f"🔌 API Version: v{api_version}")
        if user_name:
            self._log(f"👤 User: {user_name}")
        
        # Auto-load folders and reports
        self._log("🔄 Loading report folders and reports...")
        self._load_all_folders()
    
    
    def _load_all_folders(self):
        """Load all folders and reports in background with progress"""
        if not self.session_info:
            return
        
        # Check if already loading
        if self.is_loading:
            self._log("⚠️ Already loading data, please wait...")
            return
        
        # Set state
        self._set_ui_state("loading")
        
        # Disable button and show loading
        self.all_folders_btn.configure(state="disabled", text="⏳ Loading...")
        
        # Show loading indicator in tree
        for widget in self.tree_container.winfo_children():
            widget.destroy()
        
        # Create loading frame with progress
        loading_frame = ctk.CTkFrame(self.tree_container, fg_color="transparent")
        loading_frame.grid(row=0, column=0, pady=30)
        
        loading_label = ctk.CTkLabel(
            loading_frame,
            text="⏳ Loading folders and reports...",
            text_color="gray",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        loading_label.pack(pady=(0, 10))
        
        self.loading_progress_label = ctk.CTkLabel(
            loading_frame,
            text="Connecting to Salesforce...",
            text_color="gray",
            font=ctk.CTkFont(size=11)
        )
        self.loading_progress_label.pack(pady=(0, 10))
        
        self.loading_progress_bar = ctk.CTkProgressBar(loading_frame, width=300)
        self.loading_progress_bar.pack()
        self.loading_progress_bar.set(0)
        
        self._log("🔄 Fetching folders and reports from Salesforce...")
        
        thread = threading.Thread(target=self._load_data_worker, daemon=True)
        thread.start()
    
    def _load_data_worker(self):
        """Background worker to load folders and reports with progress"""
        try:
            session_id = self.session_info.get("session_id")
            instance_url = self.session_info.get("instance_url")
            
            exporter = SalesforceReportExporter(session_id, instance_url)
            
            # Step 1: Load folders
            self.update_queue.put(("loading_progress", (0.1, "Fetching folders...")))
            folders = exporter.list_report_folders()
            self.update_queue.put(("log", f"📁 Found {len(folders)} folders"))
            
            # Step 2: Load ALL reports (for total count)
            self.update_queue.put(("loading_progress", (0.2, "Fetching all reports...")))
            all_reports = exporter.list_reports()
            self.update_queue.put(("log", f"📄 Found {len(all_reports)} total reports"))
            
            # Step 3: For each folder, get reports with progress
            self.update_queue.put(("loading_progress", (0.3, "Loading reports by folder...")))
            
            reports_by_folder_id = {}
            total_folders = len(folders)
            
            for idx, folder in enumerate(folders):
                folder_id = folder.get("id")
                folder_name = folder.get("name")
                
                try:
                    # Update progress
                    progress = 0.3 + (0.6 * (idx / max(total_folders, 1)))
                    status = f"Loading folder {idx + 1}/{total_folders}: {folder_name[:30]}..."
                    self.update_queue.put(("loading_progress", (progress, status)))
                    
                    # Query reports for this folder (with pagination)
                    folder_reports = exporter.list_reports(folder_id=folder_id)
                    reports_by_folder_id[folder_id] = folder_reports
                    
                    if folder_reports:
                        self.update_queue.put(("log", f"  ✓ {folder_name}: {len(folder_reports)} reports"))
                    
                except Exception as e:
                    self.update_queue.put(("log", f"  ✗ Error loading '{folder_name}': {str(e)}"))
                    reports_by_folder_id[folder_id] = []
            
            # Final progress
            self.update_queue.put(("loading_progress", (0.9, "Preparing tree view...")))
            
            # Update UI via queue
            self.update_queue.put(("data_loaded", {
                "folders": folders,
                "reports": all_reports,
                "reports_by_folder": reports_by_folder_id
            }))
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            self.update_queue.put(("log", f"❌ ERROR: {error_details}"))
            self.update_queue.put(("data_error", str(e)))
    
    def _on_loading_progress(self, progress_data):
        """Update loading progress in tree panel"""
        progress_value, status_text = progress_data
        
        try:
            if hasattr(self, 'loading_progress_bar'):
                self.loading_progress_bar.set(progress_value)
            
            if hasattr(self, 'loading_progress_label'):
                self.loading_progress_label.configure(text=status_text)
        except:
            pass  # Widgets might be destroyed
    
    def _on_data_loaded(self, data: Dict):
        """Handle data loaded successfully - with chunked tree population"""
        
        with self.data_lock:
            self.available_folders = data.get("folders", [])
            self.available_reports = data.get("reports", [])
            self.reports_by_folder = data.get("reports_by_folder", {})
        
        # Filter out system folders
        filtered_folders = [
            f for f in self.available_folders
            if f.get("name") and f.get("name") not in ["Automated Process", "System", "Hidden"]
            and not f.get("name").startswith("__")
        ]
        
        with self.data_lock:
            self.available_folders = filtered_folders
        
        # Count total reports
        total_reports_in_folders = sum(len(reports) for reports in self.reports_by_folder.values())
        
        # Clear loading indicator
        for widget in self.tree_container.winfo_children():
            widget.destroy()
        
        # Show temporary message
        temp_label = ctk.CTkLabel(
            self.tree_container,
            text=f"📊 Rendering {len(filtered_folders)} folders with {total_reports_in_folders} reports...\nPlease wait...",
            text_color="gray",
            font=ctk.CTkFont(size=11)
        )
        temp_label.grid(row=0, column=0, pady=20)
        
        # Populate tree in chunks (non-blocking)
        self._populate_tree_chunked()
        
        # Re-enable button
        self.all_folders_btn.configure(state="normal", text="📁 All Folders")
        
        # Reset state
        self._set_ui_state("idle")
        
            # ✅ NEW: Update export button state after loading
        self._update_export_button_state()
        
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
        
    def _on_data_error(self, error: str):
        """Handle data loading error"""
        self.all_folders_btn.configure(state="normal", text="📁 All Folders")
        self._log(f"❌ Error loading data: {error}")
        messagebox.showerror("Error", f"Failed to load folders and reports:\n\n{error}")
    
    # ===== TREE VIEW POPULATION =====
    
    def _populate_tree(self, search_term: str = ""):
        """Populate the tree view with folders and reports"""
        
        # Clear existing tree
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
        
        if search_term:
            search_lower = search_term.lower()
            
            for folder in self.available_folders:
                folder_id = folder.get("id")
                folder_name = folder.get("name", "")
                
                # Get all reports in this folder
                all_reports = self.reports_by_folder.get(folder_id, [])
                
                # Check if folder name matches
                folder_matches = search_lower in folder_name.lower()
                
                if folder_matches:
                    # Folder matches - include ALL reports in this folder
                    filtered_folders_data.append({
                        "folder": folder,
                        "reports": all_reports
                    })
                else:
                    # Folder doesn't match - check if any reports match
                    matching_reports = [
                        r for r in all_reports
                        if search_lower in r.get("name", "").lower()
                    ]
                    
                    if matching_reports:
                        # Include folder with only matching reports
                        filtered_folders_data.append({
                            "folder": folder,
                            "reports": matching_reports
                        })
        else:
            # No search - show all folders with all reports
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
        
        # Create tree items for each folder
        for idx, folder_data in enumerate(filtered_folders_data):
            self._create_folder_item(
                idx, 
                folder_data["folder"], 
                folder_data["reports"]
            )
            
    def _populate_tree_chunked(self, search_term: str = ""):
        """
        Standard tree population. 
        Fixes scrollbar issues by creating actual widgets.
        """
        
        # Clear existing tree
        for widget in self.tree_container.winfo_children():
            widget.destroy()
        
        self.tree_items.clear()
        
        # Filter folders and reports by search term
        filtered_folders_data = []
        
        with self.data_lock:
            # (Logic to filter data same as before...)
            if search_term:
                search_lower = search_term.lower()
                for folder in self.available_folders:
                    folder_id = folder.get("id")
                    folder_name = folder.get("name", "")
                    all_reports = self.reports_by_folder.get(folder_id, [])
                    
                    folder_matches = search_lower in folder_name.lower()
                    if folder_matches:
                        filtered_folders_data.append({"folder": folder, "reports": all_reports})
                    else:
                        matching_reports = [r for r in all_reports if search_lower in r.get("name", "").lower()]
                        if matching_reports:
                            filtered_folders_data.append({"folder": folder, "reports": matching_reports})
            else:
                for folder in self.available_folders:
                    folder_id = folder.get("id")
                    filtered_folders_data.append({"folder": folder, "reports": self.reports_by_folder.get(folder_id, [])})
        
        if not filtered_folders_data:
            msg = f"No results for '{search_term}'" if search_term else "No folders found"
            ctk.CTkLabel(self.tree_container, text=msg, text_color="gray").grid(row=0, column=0, pady=20)
            return

        # RENDER DIRECTLY (Fixes Scrollbar)
        # We process in small batches to not freeze UI, but we create REAL widgets
        chunk_size = 20
        total_folders = len(filtered_folders_data)
        
        def render_chunk(start_idx):
            end_idx = min(start_idx + chunk_size, total_folders)
            
            for i in range(start_idx, end_idx):
                folder_data = filtered_folders_data[i]
                # Pass 'i' as the row index
                self._create_folder_item(i, folder_data["folder"], folder_data["reports"])
            
            # If more to render, schedule next batch
            if end_idx < total_folders:
                self.after(5, lambda: render_chunk(end_idx))
            else:
                self._log(f"✅ Tree view loaded: {total_folders} folders")
        
        render_chunk(0)
        
        
    def _populate_tree_chunked(self, search_term: str = ""):
        """
        Populate tree in chunks to prevent UI freezing.
        Renders 20 folders at a time with small delays.
        """
        
        # Clear existing tree
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
        
        # Render in chunks
        chunk_size = 20  # Render 20 folders at a time
        total_folders = len(filtered_folders_data)
        
        def render_chunk(start_idx):
            end_idx = min(start_idx + chunk_size, total_folders)
            
            for i in range(start_idx, end_idx):
                folder_data = filtered_folders_data[i]
                # Use row = i * 2 to leave space for reports
                self._create_folder_item(i, folder_data["folder"], folder_data["reports"])
            
            # If more folders to render, schedule next chunk
            if end_idx < total_folders:
                # Update progress
                progress_pct = int((end_idx / total_folders) * 100)
                self._log(f"🔄 Rendering folders: {end_idx}/{total_folders} ({progress_pct}%)")
                
                # Schedule next chunk after 10ms delay
                self.after(10, lambda: render_chunk(end_idx))
            else:
                self._log(f"✅ Tree view ready: {total_folders} folders displayed")
        
        # Start rendering first chunk
        if total_folders > chunk_size:
            self._log(f"🔄 Rendering tree view in chunks ({chunk_size} folders at a time)...")
        
        render_chunk(0)
        
    def _create_folder_item(self, row: int, folder: Dict, reports_to_show: List[Dict]):
        """Create a folder item in the tree, now with tighter padding"""
        
        folder_id = folder.get("id")
        folder_name = folder.get("name", "Unnamed Folder")
        folder_type = folder.get("type", "")
        
        reports_in_folder = reports_to_show
        
        # Main folder frame
        folder_frame = ctk.CTkFrame(self.tree_container, fg_color="#333333", corner_radius=5)
        # KEY FIX: Reduced pady from 3 to 2 for tighter vertical blocks
        folder_frame.grid(row=row * 2, column=0, sticky="ew", padx=5, pady=(2, 2))
        folder_frame.grid_columnconfigure(2, weight=1)
        
        # Folder checkbox
        folder_checkbox_var = ctk.BooleanVar(value=False)
        folder_checkbox = ctk.CTkCheckBox(
            folder_frame,
            text="",
            variable=folder_checkbox_var,
            width=20,
            checkbox_width=18,
            checkbox_height=18,
            command=lambda: self._on_folder_checkbox_changed(folder_id, folder_checkbox_var)
        )
        # KEY FIX: Reduced internal pady from 10 to 5
        folder_checkbox.grid(row=0, column=0, padx=(10, 5), pady=5, sticky="w")
        
        # Expand/collapse button
        expand_btn = ctk.CTkButton(
            folder_frame,
            text="▶",
            width=25,
            height=25,
            fg_color="transparent",
            hover_color="#444444",
            font=ctk.CTkFont(size=12),
            command=lambda: self._toggle_folder_expansion(folder_id)
        )
        # KEY FIX: Reduced internal pady from 10 to 5
        expand_btn.grid(row=0, column=1, padx=(0, 5), pady=5, sticky="w")
        
        # Folder icon and name
        icon = "🌐" if folder_type == "Public" else "👤" if "My" in folder_name else "📂"
        folder_label = ctk.CTkLabel(
            folder_frame,
            text=f"{icon} {folder_name} ({len(reports_in_folder)} reports)",
            font=ctk.CTkFont(size=12),
            anchor="w"
        )
        # KEY FIX: Reduced internal pady from 10 to 5
        folder_label.grid(row=0, column=2, sticky="ew", padx=(0, 10), pady=5)
        
        # Reports container (initially hidden)
        reports_frame = ctk.CTkFrame(self.tree_container, fg_color="#2b2b2b")
        # KEY FIX: Reduced pady for reports container separation
        reports_frame.grid(row=row * 2 + 1, column=0, sticky="ew", padx=(30, 5), pady=(0, 2))
        reports_frame.grid_remove()  # Hide initially
        reports_frame.grid_columnconfigure(0, weight=1)
        
        # Store tree item data
        self.tree_items[folder_id] = {
            "frame": folder_frame,
            "checkbox": folder_checkbox,
            "checkbox_var": folder_checkbox_var,
            "expand_btn": expand_btn,
            "reports_frame": reports_frame,
            "expanded": False,
            "reports": reports_in_folder,
            "folder_name": folder_name,
            "report_checkboxes": {}
        }
        
        # Create report items inside reports_frame
        if reports_in_folder:
            self._create_report_items(reports_frame, folder_id, reports_in_folder)
        else:
            no_reports_label = ctk.CTkLabel(
                reports_frame,
                text="No reports in this folder",
                text_color="gray",
                font=ctk.CTkFont(size=11)
            )
            no_reports_label.grid(row=0, column=0, padx=10, pady=5)
            
    
    def _create_folder_item_virtual(self, row: int, folder: Dict, reports_to_show: List[Dict]):
        """
        Create a folder item optimized for virtual scrolling.
        Only creates checkbox and header, reports loaded on-demand.
        """
        
        folder_id = folder.get("id")
        folder_name = folder.get("name", "Unnamed Folder")
        folder_type = folder.get("type", "")
        reports_in_folder = reports_to_show
        
        # Update tree_items with lazy-loaded data
        if folder_id not in self.tree_items:
            self.tree_items[folder_id] = {
                "folder": folder,
                "folder_name": folder_name,
                "reports": reports_in_folder,
                "expanded": False,
                "row_index": row,
                "report_checkboxes": {}
            }
        
        # Main folder frame
        folder_frame = ctk.CTkFrame(self.tree_container, fg_color="#333333", corner_radius=5)
        folder_frame.grid(row=row * 2, column=0, sticky="ew", padx=5, pady=3)
        folder_frame.grid_columnconfigure(2, weight=1)
        
        # Folder checkbox (lazy create)
        if self.tree_items[folder_id].get("checkbox_var") is None:
            self.tree_items[folder_id]["checkbox_var"] = ctk.BooleanVar(value=False)
        
        folder_checkbox_var = self.tree_items[folder_id]["checkbox_var"]
        folder_checkbox = ctk.CTkCheckBox(
            folder_frame,
            text="",
            variable=folder_checkbox_var,
            width=20,
            checkbox_width=18,
            checkbox_height=18,
            command=lambda: self._on_folder_checkbox_changed(folder_id, folder_checkbox_var)
        )
        folder_checkbox.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="w")
        
        # Expand/collapse button
        expand_btn = ctk.CTkButton(
            folder_frame,
            text="▶",
            width=25,
            height=25,
            fg_color="transparent",
            hover_color="#444444",
            font=ctk.CTkFont(size=12),
            command=lambda: self._toggle_folder_expansion(folder_id)
        )
        expand_btn.grid(row=0, column=1, padx=(0, 5), pady=10, sticky="w")
        
        # Folder icon and name
        icon = "🌐" if folder_type == "Public" else "👤" if "My" in folder_name else "📂"
        folder_label = ctk.CTkLabel(
            folder_frame,
            text=f"{icon} {folder_name} ({len(reports_in_folder)} reports)",
            font=ctk.CTkFont(size=12),
            anchor="w"
        )
        folder_label.grid(row=0, column=2, sticky="ew", padx=(0, 10), pady=10)
        
        # Reports container (created but hidden initially)
        reports_frame = ctk.CTkFrame(self.tree_container, fg_color="#2b2b2b")
        reports_frame.grid(row=row * 2 + 1, column=0, sticky="ew", padx=(30, 5), pady=(0, 3))
        reports_frame.grid_remove()  # Hide initially
        reports_frame.grid_columnconfigure(0, weight=1)
        
        # Update tree_items with widget references
        self.tree_items[folder_id].update({
            "frame": folder_frame,
            "checkbox": folder_checkbox,
            "expand_btn": expand_btn,
            "reports_frame": reports_frame,
            "reports_loaded": False  # Track if reports are rendered
        })
    
    def _create_report_items(self, parent_frame, folder_id: str, reports: List[Dict]):
        """Create report checkboxes inside a folder's reports frame"""
        
        for idx, report in enumerate(reports):
            report_id = report.get("id")
            report_name = report.get("name", "Unnamed Report")
            
            # Report item frame
            report_frame = ctk.CTkFrame(parent_frame, fg_color="transparent")
            report_frame.grid(row=idx, column=0, sticky="ew", padx=10, pady=2)
            report_frame.grid_columnconfigure(1, weight=1)
            
            # ✅ FIX: Check if this report is already selected
            is_selected = report_id in self.selected_items
            
            # Report checkbox - set initial value based on selection state
            report_checkbox_var = ctk.BooleanVar(value=is_selected)  # ← FIXED
            report_checkbox = ctk.CTkCheckBox(
                report_frame,
                text="",
                variable=report_checkbox_var,
                width=20,
                checkbox_width=16,
                checkbox_height=16,
                command=lambda rid=report_id, rname=report_name, fid=folder_id, var=report_checkbox_var: 
                    self._on_report_checkbox_changed(rid, rname, fid, var)
            )
            report_checkbox.grid(row=0, column=0, padx=(5, 5), pady=5, sticky="w")
            
            # Report name
            report_label = ctk.CTkLabel(
                report_frame,
                text=f"📄 {report_name}",
                font=ctk.CTkFont(size=11),
                anchor="w"
            )
            report_label.grid(row=0, column=1, sticky="ew", padx=(0, 10), pady=5)
            
            # Store report checkbox reference in tree_items
            if "report_checkboxes" not in self.tree_items[folder_id]:
                self.tree_items[folder_id]["report_checkboxes"] = {}
            
            self.tree_items[folder_id]["report_checkboxes"][report_id] = {
                "checkbox": report_checkbox,
                "checkbox_var": report_checkbox_var,
                "name": report_name
            }
            
            
    def _load_reports_for_folder(self, folder_id: str, reports_frame, reports: List[Dict]):
        """
        Lazy load report checkboxes for a folder.
        Only called when user expands the folder.
        """
        
        # Load in chunks for smooth rendering
        chunk_size = 50
        total_reports = len(reports)
        
        def load_chunk(start_idx):
            end_idx = min(start_idx + chunk_size, total_reports)
            
            for idx in range(start_idx, end_idx):
                report = reports[idx]
                report_id = report.get("id")
                report_name = report.get("name", "Unnamed Report")
                
                # Report item frame
                report_frame = ctk.CTkFrame(reports_frame, fg_color="transparent")
                report_frame.grid(row=idx, column=0, sticky="ew", padx=10, pady=2)
                report_frame.grid_columnconfigure(1, weight=1)
                
                # Report checkbox
                report_checkbox_var = ctk.BooleanVar(value=False)
                report_checkbox = ctk.CTkCheckBox(
                    report_frame,
                    text="",
                    variable=report_checkbox_var,
                    width=20,
                    checkbox_width=16,
                    checkbox_height=16,
                    command=lambda rid=report_id, rname=report_name, fid=folder_id, var=report_checkbox_var: 
                        self._on_report_checkbox_changed(rid, rname, fid, var)
                )
                report_checkbox.grid(row=0, column=0, padx=(5, 5), pady=5, sticky="w")
                
                # Report name
                report_label = ctk.CTkLabel(
                    report_frame,
                    text=f"📄 {report_name}",
                    font=ctk.CTkFont(size=11),
                    anchor="w"
                )
                report_label.grid(row=0, column=1, sticky="ew", padx=(0, 10), pady=5)
                
                # Store report checkbox reference
                if "report_checkboxes" not in self.tree_items[folder_id]:
                    self.tree_items[folder_id]["report_checkboxes"] = {}
                
                self.tree_items[folder_id]["report_checkboxes"][report_id] = {
                    "checkbox": report_checkbox,
                    "checkbox_var": report_checkbox_var,
                    "name": report_name
                }
            
            # Load next chunk if needed
            if end_idx < total_reports:
                self.after(10, lambda: load_chunk(end_idx))
        
        # Start loading first chunk
        load_chunk(0)
    
    def _toggle_folder_expansion(self, folder_id: str):
        """Toggle folder expansion with lazy loading of reports"""
        
        if folder_id not in self.tree_items:
            return
        
        tree_item = self.tree_items[folder_id]
        reports_frame = tree_item["reports_frame"]
        expand_btn = tree_item["expand_btn"]
        is_expanded = tree_item["expanded"]
        reports_loaded = tree_item.get("reports_loaded", False)
        reports = tree_item.get("reports", [])
        
        if is_expanded:
            # Collapse
            reports_frame.grid_remove()
            expand_btn.configure(text="▶")
            tree_item["expanded"] = False
        else:
            # Expand
            expand_btn.configure(text="▼")
            tree_item["expanded"] = True
            
            # Lazy load reports if not already loaded
            if not reports_loaded and reports:
                self._load_reports_for_folder(folder_id, reports_frame, reports)
                tree_item["reports_loaded"] = True
                
                # ✅ FIX: After loading, sync checkbox states with selected_items
                self._sync_folder_checkboxes(folder_id)
                
            elif not reports:
                # Show empty message
                no_reports_label = ctk.CTkLabel(
                    reports_frame,
                    text="No reports in this folder",
                    text_color="gray",
                    font=ctk.CTkFont(size=11)
                )
                no_reports_label.grid(row=0, column=0, padx=20, pady=10)
                tree_item["reports_loaded"] = True
            else:
                # ✅ FIX: Reports already loaded, but might need syncing
                self._sync_folder_checkboxes(folder_id)
            
            reports_frame.grid()
    
    def _sync_folder_checkboxes(self, folder_id: str):
        """
        Sync report checkboxes with actual selection state.
        Call this after lazy-loading reports or when selection changes.
        """
        if folder_id not in self.tree_items:
            return
        
        tree_item = self.tree_items[folder_id]
        report_checkboxes = tree_item.get("report_checkboxes", {})
        
        # Update each report checkbox to match selection state
        for report_id, checkbox_data in report_checkboxes.items():
            is_selected = report_id in self.selected_items
            checkbox_var = checkbox_data.get("checkbox_var")
            
            if checkbox_var:
                # Only update if state is different (prevent unnecessary events)
                current_value = checkbox_var.get()
                if current_value != is_selected:
                    checkbox_var.set(is_selected)
    
    def _on_folder_checkbox_changed(self, folder_id: str, checkbox_var: ctk.BooleanVar):
        """Handle folder checkbox change - select/deselect all reports in folder"""
        
        if folder_id not in self.tree_items:
            self._log(f"ERROR: Folder {folder_id} not found in tree_items")
            return
        
        is_checked = checkbox_var.get()
        tree_item = self.tree_items[folder_id]
        reports = tree_item.get("reports", [])
        folder_name = tree_item.get("folder_name", "Unknown")
        
        if not reports:
            self._log(f"⚠️ No reports in folder: {folder_name}")
            checkbox_var.set(False)  # Uncheck since there's nothing to select
            return
        
        # Get report checkboxes
        report_checkboxes = tree_item.get("report_checkboxes", {})
        
        if is_checked:
            # Select all reports in this folder
            for report in reports:
                report_id = report.get("id")
                report_name = report.get("name", "Unnamed Report")
                
                # Add to selected items
                self.selected_items[report_id] = {
                    "type": "report",
                    "name": report_name,
                    "folder_id": folder_id,
                    "folder_name": folder_name
                }
                
                # Check the report checkbox if it exists
                if report_id in report_checkboxes:
                    report_checkboxes[report_id]["checkbox_var"].set(True)
            
            self._log(f"✅ Selected folder: {folder_name} ({len(reports)} reports)")
        else:
            # Deselect all reports in this folder
            for report in reports:
                report_id = report.get("id")
                
                # Remove from selected items
                if report_id in self.selected_items:
                    del self.selected_items[report_id]
                
                # Uncheck the report checkbox if it exists
                if report_id in report_checkboxes:
                    report_checkboxes[report_id]["checkbox_var"].set(False)
            
            self._log(f"❌ Deselected folder: {folder_name}")
        
        # Update selected panel
        self._refresh_selected_panel()
    
    def _on_report_checkbox_changed(self, report_id: str, report_name: str, folder_id: str, checkbox_var: ctk.BooleanVar):
        """Handle individual report checkbox change"""
        
        is_checked = checkbox_var.get()
        folder_name = self.tree_items.get(folder_id, {}).get("folder_name", "Unknown")
        
        if is_checked:
            # Add to selected items
            self.selected_items[report_id] = {
                "type": "report",
                "name": report_name,
                "folder_id": folder_id,
                "folder_name": folder_name
            }
            self._log(f"✅ Selected: {report_name}")
        else:
            # Remove from selected items
            if report_id in self.selected_items:
                del self.selected_items[report_id]
            self._log(f"❌ Deselected: {report_name}")
            
            # Uncheck folder checkbox if it was checked
            if folder_id in self.tree_items:
                self.tree_items[folder_id]["checkbox_var"].set(False)
        
        # Update selected panel
        self._refresh_selected_panel()
    
    def _on_left_search(self, event):
        """Handle search in left panel with debouncing"""
        
        # Cancel previous timer if it exists
        if self.search_timer is not None:
            self.after_cancel(self.search_timer)
        
        # Set new timer - wait 300ms after user stops typing
        self.search_timer = self.after(300, self._execute_search)

    def _execute_search(self):
        """Execute the actual search after debounce delay"""
        search_term = self.left_search_entry.get().strip()
        self._populate_tree(search_term)  # ✅ Passes search_term
        self.search_timer = None
    
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
        """Remove a single item from selected panel"""
        
        if item_id not in self.selected_items:
            return
        
        item_data = self.selected_items[item_id]
        folder_id = item_data.get("folder_id")
        
        # Remove from selected items
        del self.selected_items[item_id]
        
        # Uncheck the checkbox in tree
        if folder_id in self.tree_items:
            report_checkboxes = self.tree_items[folder_id].get("report_checkboxes", {})
            if item_id in report_checkboxes:
                report_checkboxes[item_id]["checkbox_var"].set(False)
            
            # Also uncheck folder checkbox
            self.tree_items[folder_id]["checkbox_var"].set(False)
        
        self._log(f"❌ Removed: {item_data.get('name', 'Unknown')}")
        
        # Refresh panel
        self._refresh_selected_panel()
    
    # ===== ACTION BUTTONS =====
    
    def _clear_all_selected(self):
        """Clear all selected items"""
        if not self.selected_items:
            return
        
        count = len(self.selected_items)
        
        # Uncheck all checkboxes in tree
        for item_id, item_data in list(self.selected_items.items()):
            folder_id = item_data.get("folder_id")
            
            if folder_id in self.tree_items:
                # Uncheck report checkbox
                report_checkboxes = self.tree_items[folder_id].get("report_checkboxes", {})
                if item_id in report_checkboxes:
                    report_checkboxes[item_id]["checkbox_var"].set(False)
                
                # Uncheck folder checkbox
                self.tree_items[folder_id]["checkbox_var"].set(False)
        
        # Clear selected items
        self.selected_items.clear()
        
        self._log(f"🗑️ Cleared all selections ({count} reports)")
        
        # Refresh panel
        self._refresh_selected_panel()
    
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
        """Enable/disable export button based on conditions"""
        
        # Check all conditions
        with self.data_lock:
            has_session = self.session_info is not None
            has_path = self.output_zip_path is not None
            has_selection = len(self.selected_items) > 0
        
        with self.ui_lock:
            is_busy = self.is_exporting or self.is_loading
            ui_state = self.ui_state
        
        # Debug logging (keep for now, can remove later)
        print(f"🔍 Export Button State Check:")
        print(f"   Session: {has_session}")
        print(f"   Path: {has_path}")
        print(f"   Selection: {has_selection} ({len(self.selected_items)} items)")
        print(f"   UI State: {ui_state}")
        print(f"   Busy: {is_busy}")
        
        # Can only export if ALL conditions met AND not busy
        can_export = has_session and has_path and has_selection and not is_busy
        
        print(f"   ✅ Can Export: {can_export}")
        
        # Update button state - use after() to ensure main thread
        def update_btn():
            try:
                if can_export:
                    self.export_button.configure(state="normal")
                    print(f"   🟢 Export button ENABLED")
                else:
                    self.export_button.configure(state="disabled")
                    print(f"   🔴 Export button DISABLED")
            except Exception as e:
                print(f"   ⚠️ Button update error: {e}")
        
        # Execute on main thread
        try:
            if threading.current_thread() is threading.main_thread():
                update_btn()
            else:
                self.after(0, update_btn)
        except:
            self.after(0, update_btn)
        
    # ===== EXPORT OPERATIONS =====
    
    def _cancel_export(self):
        """Cancel the ongoing export operation"""
        
        if not self.is_exporting:
            return
        
        result = messagebox.askyesno(
            "Cancel Export",
            "Cancel the export?\n\n"
            "You can choose to save the reports that have already been exported.",
            icon='warning'
        )
        
        if result:
            self._log("🛑 Cancelling export...")
            self.export_cancel_event.set()
            
            # Update UI
            self.cancel_button.configure(state="disabled", text="🛑 Cancelling...")
            self.progress_label.configure(text="Cancelling export...", text_color="orange")
    
    
    def _start_export(self):
        """Start the export process"""
        
        if not self.session_info:
            messagebox.showwarning("Not Logged In", "Please login first.")
            return
        
        if not self.output_zip_path:
            messagebox.showwarning("No Location", "Please select a save location.")
            return
        
        if not self.selected_items:
            messagebox.showwarning("No Selection", "Please select at least one report to export.")
            return
        
        # Get filename from entry
        filename = self.filename_entry.get().strip()
        if not filename:
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
        
        if not result:
            return
        
        # Start export
        self.is_exporting = True
        self._set_export_ui_state(False)
        
        self._log(f"🚀 Starting export of {count} selected reports...")
        self._log(f"📦 Destination: {self.output_zip_path}")
        
        # Get list of report IDs
        report_ids = list(self.selected_items.keys())
        
        # Clear cancel event
        self.export_cancel_event.clear()
        
        # Initialize progress tracker
        self.progress_tracker.start(len(report_ids))
        
        # Show cancel button, hide export button
        self.export_button.grid_remove()
        self.cancel_button.grid()
        self.cancel_button.configure(state="normal", text="🛑 Cancel Export")
        self.cancel_button.lift()  # ✅ NEW: Bring cancel button to front
        
        # ✅ Force update to ensure proper visibility
        self.update_idletasks()
        
        # Start export in background
        thread = threading.Thread(
            target=self._export_worker,
            args=(report_ids,),
            daemon=True
        )
        thread.start()
    
    def _export_worker(self, report_ids: List[str]):
        """Background worker for export with concurrent downloads"""
        try:
            session_id = self.session_info.get("session_id")
            instance_url = self.session_info.get("instance_url")
            
            def progress_callback(done, total, report_name=None):
                """
                ✅ FIX: Real-time progress updates with report names
                Args:
                    done: Number of reports completed
                    total: Total reports to export
                    report_name: Optional name of report being downloaded
                """
                # If report_name provided, it means download is STARTING
                if report_name:
                    # Send special progress update with report name
                    self.update_queue.put(("progress_with_name", (done, total, report_name)))
                    return
                
                # Otherwise, normal progress update (report COMPLETED)
                self.update_queue.put(("progress", (done, total)))
                
                # ✅ Log every report download immediately
                if done > 0 and done <= total:
                    percentage = int((done / total) * 100)
                    
                    # Show speed after first few reports
                    if done > 2:
                        speed = self.progress_tracker.get_speed()
                        if speed > 0.1:  # Only show speed if meaningful
                            self.update_queue.put(("log", f"  ✓ Report {done}/{total} ({percentage}%) • {speed:.1f}/sec"))
                        else:
                            self.update_queue.put(("log", f"  ✓ Report {done}/{total} ({percentage}%)"))
                    else:
                        # First few reports - don't show speed yet
                        self.update_queue.put(("log", f"  ✓ Report {done}/{total} ({percentage}%)"))
            
            exporter = SalesforceReportExporter(
                session_id,
                instance_url,
                progress_callback=progress_callback
            )
            
            # Use concurrent export method
            result = exporter.export_selected_reports_to_zip_concurrent(
                self.output_zip_path,
                report_ids,
                max_workers=5,  # 5 parallel downloads
                cancel_event=self.export_cancel_event,
                retry_attempts=3  # Retry 3 times on failure
            )
            
            self.update_queue.put(("export_complete", result))
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            self.update_queue.put(("log", f"❌ Export error:\n{error_details}"))
            self.update_queue.put(("export_error", str(e)))
    
    def _on_export_progress(self, progress_data):
        """Handle export progress update with ETA and speed"""
        done, total = progress_data
        
        # ✅ FIX: Throttle UI updates to prevent freezing
        current_time = time.time()
        
        # Initialize throttle timer on first call
        if not hasattr(self, '_last_progress_ui_update'):
            self._last_progress_ui_update = 0
        
        # Calculate time since last UI update
        time_since_last_update = current_time - self._last_progress_ui_update
        
        # ✅ SMART THROTTLING: Always update first and last, throttle middle
        should_update_ui = (
            done == 1 or                          # Always update first report
            done == total or                       # Always update last report
            time_since_last_update >= 0.5          # Throttle to max 2 updates/sec
        )
        
        # Always update the tracker (for speed calculations)
        self.progress_tracker.update(done)
        
        # Only update UI widgets if throttle allows
        if should_update_ui and total > 0:
            progress = done / total
            self.progress_bar.set(progress)
            
            # Get enhanced progress text with ETA and speed
            progress_text = self.progress_tracker.get_progress_text()
            self.progress_label.configure(
                text=progress_text,
                text_color="#1f6aa5"
            )
            
            # Update throttle timer
            self._last_progress_ui_update = current_time
    
    
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
    
    def _on_export_complete(self, result: Dict):
        """Handle export completion (including cancellation)"""
        import subprocess
        import platform
        
        self.is_exporting = False
        self._set_export_ui_state(True)
        
        total = result.get("total", 0)
        failed = result.get("failed", [])
        successful = result.get("successful", [])
        zip_path = result.get("zip", "")
        was_cancelled = result.get("cancelled", False)
        completed = result.get("completed", len(successful))
        
        # Hide cancel button, show export button properly
        self.cancel_button.grid_remove()
        self.cancel_button.configure(state="disabled")
        self.cancel_button.lower()
        
        self.export_button.grid()
        self.export_button.lift()
        
        # Update button state based on conditions
        self._update_export_button_state()
        
        # Force UI update
        self.update_idletasks()
        
        # Update progress with statistics
        if was_cancelled:
            progress_value = completed / total if total > 0 else 0
            self.progress_bar.set(progress_value)
            
            elapsed = self.progress_tracker.get_elapsed_seconds()
            elapsed_formatted = self.progress_tracker.format_time(elapsed)
            
            self.progress_label.configure(
                text=f"⚠️ Export cancelled after {elapsed_formatted}. Saved {completed}/{total} reports",
                text_color="orange"
            )
        else:
            self.progress_bar.set(1.0)
            
            # Get completion statistics
            completion_text = self.progress_tracker.get_completion_text()
            self.progress_label.configure(
                text=completion_text,
                text_color="green"
            )
        
        # Log summary with statistics
        self._log("=" * 50)
        
        if was_cancelled:
            self._log(f"⚠️ EXPORT CANCELLED BY USER")
            self._log(f"📊 Completed: {completed}/{total} reports")
        else:
            self._log(f"✅ EXPORT COMPLETED SUCCESSFULLY")
            self._log(f"📊 Total: {total} reports")
        
        # Export statistics
        elapsed = self.progress_tracker.get_elapsed_seconds()
        elapsed_formatted = self.progress_tracker.format_time(elapsed)
        avg_speed = completed / elapsed if elapsed > 0 else 0
        
        self._log(f"⏱️  Duration: {elapsed_formatted}")
        if avg_speed > 0:
            self._log(f"⚡ Average Speed: {avg_speed:.2f} reports/sec")
        
        self._log(f"✔️  Successful: {len(successful)}")
        self._log(f"❌ Failed: {len(failed)}")
        
        if len(failed) > 0:
            success_rate = (len(successful) / total * 100) if total > 0 else 0
            self._log(f"📈 Success Rate: {success_rate:.1f}%")
        
        self._log(f"💾 Saved to: {zip_path}")
        self._log("=" * 50)
        
        if failed:
            self._log("⚠️ Failed reports:")
            for f in failed[:5]:
                error_msg = f.get('error', 'Unknown error')
                self._log(f"  • {f.get('name')}: {error_msg[:50]}")
            if len(failed) > 5:
                self._log(f"  ... and {len(failed) - 5} more (see summary file)")
        
        # Show completion message with statistics
        elapsed = self.progress_tracker.get_elapsed_seconds()
        elapsed_formatted = self.progress_tracker.format_time(elapsed)
        avg_speed = completed / elapsed if elapsed > 0 else 0
        
        if was_cancelled:
            # Ask user about partial export
            message = f"Export was cancelled.\n\n"
            message += f"📊 Statistics:\n"
            message += f"  • Completed: {completed}/{total} reports\n"
            message += f"  • Successful: {len(successful)}\n"
            message += f"  • Failed: {len(failed)}\n"
            message += f"  • Duration: {elapsed_formatted}\n"
            if avg_speed > 0:
                message += f"  • Average Speed: {avg_speed:.1f} reports/sec\n"
            message += f"\nPartial export saved to:\n{zip_path}\n\n"
            message += f"Do you want to keep this partial export?"
            
            keep_result = messagebox.askyesnocancel(
                "Export Cancelled",
                message,
                icon='warning'
            )
            
            if keep_result is False:  # User chose "No" - delete
                try:
                    os.remove(zip_path)
                    self._log(f"🗑️ Partial export deleted")
                    messagebox.showinfo("Deleted", "Partial export has been deleted.")
                    return
                except Exception as e:
                    self._log(f"❌ Failed to delete: {str(e)}")
            elif keep_result is None:  # User chose "Cancel" - do nothing
                return
            # If True, continue to open folder option
        else:
            success_rate = (len(successful) / total * 100) if total > 0 else 0
            
            message = f"Export completed successfully!\n\n"
            message += f"📊 Statistics:\n"
            message += f"  • Total Reports: {total}\n"
            message += f"  • Successful: {len(successful)}\n"
            message += f"  • Failed: {len(failed)}\n"
            message += f"  • Success Rate: {success_rate:.1f}%\n"
            message += f"  • Duration: {elapsed_formatted}\n"
            if avg_speed > 0:
                message += f"  • Average Speed: {avg_speed:.1f} reports/sec\n"
            message += f"\n💾 ZIP saved to:\n{zip_path}"
            
            messagebox.showinfo("Export Complete", message)
        
        # Ask if user wants to open folder
        result = messagebox.askyesno("Open Folder?", "Would you like to open the folder containing the exported file?")
        if result:
            folder = os.path.dirname(zip_path)
            
            # ✅ FIX: Safer platform-specific folder opening
            try:
                if platform.system() == "Windows":
                    os.startfile(folder)
                elif platform.system() == "Darwin":  # macOS
                    subprocess.Popen(["open", folder])
                else:  # Linux
                    subprocess.Popen(["xdg-open", folder])
            except Exception as e:
                self._log(f"❌ Could not open folder: {str(e)}")
                messagebox.showerror("Error", f"Could not open folder:\n{str(e)}")
    
    def _on_export_error(self, error_msg: str):
        """Handle export error with helpful messages"""
        self.is_exporting = False
        self._set_export_ui_state(True)
        
        # Hide cancel button, show export button properly
        self.cancel_button.grid_remove()
        self.cancel_button.configure(state="disabled")
        self.cancel_button.lower()  # ✅ NEW: Push cancel button to back
        
        self.export_button.grid()
        self.export_button.lift()  # ✅ NEW: Bring export button to front
        
        # Update button state based on conditions
        self._update_export_button_state()
        
        # Force UI update
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
        
        messagebox.showerror(
            "Export Failed",
            f"Export failed:\n\n{error_msg}\n\n{helpful_msg}"
        )
    
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
        """Enable/disable UI during export"""
        state = "normal" if enabled else "disabled"
        
        self.logout_button.configure(state=state)
        self.browse_button.configure(state=state)
        self.all_folders_btn.configure(state=state)
        self.filename_entry.configure(state=state)
        
        if enabled:
            # Export finished - restore normal UI
            self.filename_entry.configure(state="normal")
            
            # ✅ CRITICAL: Properly restore button visibility
            self.cancel_button.grid_remove()
            self.cancel_button.configure(state="disabled")
            self.cancel_button.lower()  # ✅ NEW: Push to back
            
            self.export_button.grid()
            self.export_button.lift()  # ✅ NEW: Bring to front
            
            # Update export button state based on current conditions
            self._update_export_button_state()
            
            # Force UI refresh
            self.update_idletasks()
        else:
            # Export starting - disable everything
            self.filename_entry.configure(state="disabled")
            self.export_button.configure(state="disabled")
            
            # Don't touch cancel button here - handled in _start_export()
    
    # ===== QUEUE PROCESSING =====
    
    def _process_queue(self):
        """Process updates from background threads"""
        try:
            while True:
                item = self.update_queue.get_nowait()
                
                if isinstance(item, tuple):
                    event_type = item[0]
                    data = item[1] if len(item) > 1 else None
                    
                    if event_type == "data_loaded":
                        self._on_data_loaded(data)
                    elif event_type == "loading_progress":
                        self._on_loading_progress(data)
                    elif event_type == "data_error":
                        self._on_data_error(data)
                    elif event_type == "progress_with_name":
                        # ✅ NEW: Handle progress update with report name
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