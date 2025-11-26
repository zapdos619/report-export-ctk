# main_app.py - Part 1: UPDATED Main Application Setup
# Changes:
# - Window centers on screen
# - Footer redesigned to 100px height with 2-column layout
# - Lazy loading for reports (only on tab click)
# - Loading indicators added

import customtkinter as ctk
import threading
import queue
import os
import datetime
from tkinter import filedialog, messagebox
from typing import Optional, List, Dict, Any
from login_window import LoginWindow
from exporter import SalesforceReportExporter


class SalesforceExporterApp(ctk.CTk):
    """
    Main application window for Salesforce Report Exporter.
    Built with CustomTkinter for modern UI.
    """
    
    def __init__(self):
        super().__init__()
        
        # Window setup
        self.title("Salesforce Report Exporter")
        self.geometry("900x700")
        
        # Set theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Center window on screen - NEW
        self.after(100, self._center_window)
        
        # Session data
        self.session_info: Optional[Dict] = None
        self.output_zip_path: Optional[str] = None
        self.available_folders: List[Dict] = []
        self.available_reports: List[Dict] = []
        self.selected_reports: set = set()
        self.is_exporting: bool = False
        self.reports_loaded: bool = False  # NEW - Track if reports are loaded
        
        # Queue for thread-safe UI updates
        self.update_queue = queue.Queue()
        
        # Setup UI
        self._setup_ui()
        
        # Start queue processor
        self._process_queue()
    
    def _center_window(self):
        """Center the main window on screen - NEW METHOD"""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')
        
    def _setup_ui(self):
        """Setup the main UI layout"""
        
        # Configure grid layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # Header
        self._create_header()
        
        # Main content area (tabview)
        self._create_main_content()
        
        # Footer with export controls - REDESIGNED
        self._create_footer()
        
    def _create_header(self):
        """Create header section with title and login status"""
        header_frame = ctk.CTkFrame(self, height=80)
        header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 0))
        header_frame.grid_propagate(False)
        
        # Left side - Title and subtitle
        left_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        left_frame.pack(side="left", fill="both", expand=True, padx=20, pady=10)
        
        title_label = ctk.CTkLabel(
            left_frame,
            text="📊 Salesforce Report Exporter",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.pack(anchor="w")
        
        subtitle_label = ctk.CTkLabel(
            left_frame,
            text="Export reports by folder or select specific reports",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        subtitle_label.pack(anchor="w", pady=(5, 0))
        
        # Right side - Login status and button
        right_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        right_frame.pack(side="right", padx=20, pady=10)
        
        self.status_label = ctk.CTkLabel(
            right_frame,
            text="🔴 Not logged in",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.status_label.pack(pady=(0, 5))
        
        self.login_button = ctk.CTkButton(
            right_frame,
            text="Login to Salesforce",
            command=self._open_login_window,
            width=150,
            height=32
        )
        self.login_button.pack()
        
    def _create_main_content(self):
        """Create main content area with tabs"""
        # Main content frame
        content_frame = ctk.CTkFrame(self)
        content_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        content_frame.grid_rowconfigure(0, weight=1)
        content_frame.grid_columnconfigure(0, weight=1)
        
        # Create tabview
        self.tabview = ctk.CTkTabview(content_frame)
        self.tabview.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        # Add tabs
        self.tabview.add("📁 Export by Folder")
        self.tabview.add("☑️ Select Reports")
        self.tabview.add("📋 Activity Log")
        
        # Disable tabs until logged in
        self.tabview.configure(state="disabled")
        
        # Bind tab change event - NEW for lazy loading
        self.tabview._segmented_button.configure(command=self._on_tab_changed)
        
        # Setup each tab
        self._setup_folder_tab()
        self._setup_reports_tab()
        self._setup_log_tab()
        
    def _create_footer(self):
        """Create footer with export controls - REDESIGNED TO 100px with 2-column layout"""
        footer_frame = ctk.CTkFrame(self, height=100)
        footer_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))
        footer_frame.grid_propagate(False)
        footer_frame.grid_columnconfigure(0, weight=1)
        footer_frame.grid_columnconfigure(1, weight=0)
        
        # LEFT COLUMN - Output location and progress
        left_column = ctk.CTkFrame(footer_frame, fg_color="transparent")
        left_column.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        left_column.grid_rowconfigure(1, weight=1)
        left_column.grid_columnconfigure(0, weight=1)
        
        # Output path row
        output_row = ctk.CTkFrame(left_column, fg_color="transparent")
        output_row.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        output_row.grid_columnconfigure(1, weight=1)
        
        output_label = ctk.CTkLabel(
            output_row,
            text="Output:",
            font=ctk.CTkFont(size=11, weight="bold"),
            width=50
        )
        output_label.grid(row=0, column=0, sticky="w", padx=(0, 8))
        
        self.output_path_label = ctk.CTkLabel(
            output_row,
            text="No file selected",
            font=ctk.CTkFont(size=10),
            text_color="gray",
            anchor="w"
        )
        self.output_path_label.grid(row=0, column=1, sticky="ew", padx=(0, 8))
        
        self.browse_button = ctk.CTkButton(
            output_row,
            text="Browse...",
            command=self._browse_output_path,
            width=90,
            height=28
        )
        self.browse_button.grid(row=0, column=2)
        
        # Progress section
        progress_frame = ctk.CTkFrame(left_column, fg_color="transparent")
        progress_frame.grid(row=1, column=0, sticky="nsew")
        progress_frame.grid_rowconfigure(0, weight=1)
        progress_frame.grid_columnconfigure(0, weight=1)
        
        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(progress_frame)
        self.progress_bar.grid(row=0, column=0, sticky="ew", pady=(0, 3))
        self.progress_bar.set(0)
        
        # Progress label
        self.progress_label = ctk.CTkLabel(
            progress_frame,
            text="Ready",
            font=ctk.CTkFont(size=10),
            text_color="gray"
        )
        self.progress_label.grid(row=1, column=0, sticky="w")
        
        # RIGHT COLUMN - Export button
        right_column = ctk.CTkFrame(footer_frame, fg_color="transparent")
        right_column.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
        
        self.export_button = ctk.CTkButton(
            right_column,
            text="🚀 Start Export",
            command=self._start_export,
            width=150,
            height=80,  # Full height of footer minus padding
            font=ctk.CTkFont(size=14, weight="bold"),
            state="disabled"
        )
        self.export_button.pack(fill="both", expand=True)
    
    # main_app.py - Part 2: Tab Setup Methods
# Add these methods to the SalesforceExporterApp class after _create_footer()

    def _setup_folder_tab(self):
        """Setup the folder export tab"""
        tab = self.tabview.tab("📁 Export by Folder")
        tab.grid_columnconfigure(0, weight=1)
        
        # Instructions
        info_frame = ctk.CTkFrame(tab)
        info_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        
        info_label = ctk.CTkLabel(
            info_frame,
            text="Select a folder to export all reports from that folder",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        info_label.pack(padx=15, pady=10)
        
        # Folder selection frame
        folder_frame = ctk.CTkFrame(tab)
        folder_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        folder_frame.grid_columnconfigure(0, weight=1)
        
        # Search box
        search_frame = ctk.CTkFrame(folder_frame, fg_color="transparent")
        search_frame.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 10))
        search_frame.grid_columnconfigure(1, weight=1)
        
        search_label = ctk.CTkLabel(search_frame, text="🔍 Search:", width=60)
        search_label.grid(row=0, column=0, padx=(0, 10))
        
        self.folder_search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="Type to filter folders..."
        )
        self.folder_search_entry.grid(row=0, column=1, sticky="ew")
        self.folder_search_entry.bind("<KeyRelease>", self._on_folder_search)
        
        # Folder dropdown with loading indicator
        dropdown_frame = ctk.CTkFrame(folder_frame, fg_color="transparent")
        dropdown_frame.grid(row=1, column=0, sticky="ew", padx=15, pady=(0, 10))
        dropdown_frame.grid_columnconfigure(0, weight=1)
        
        self.folder_var = ctk.StringVar(value="Please login first")
        self.folder_dropdown = ctk.CTkOptionMenu(
            dropdown_frame,
            variable=self.folder_var,
            values=["Please login first"],
            command=self._on_folder_selected,
            state="disabled"
        )
        self.folder_dropdown.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        
        self.refresh_folders_btn = ctk.CTkButton(
            dropdown_frame,
            text="🔄 Refresh",
            command=self._refresh_folders,
            width=100,
            state="disabled"
        )
        self.refresh_folders_btn.grid(row=0, column=1)
        
        # Folder info label with loading indicator support
        self.folder_info_label = ctk.CTkLabel(
            folder_frame,
            text="Please login to see available folders",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        self.folder_info_label.grid(row=2, column=0, sticky="w", padx=15, pady=(0, 15))
        
    def _setup_reports_tab(self):
        """Setup the select reports tab"""
        tab = self.tabview.tab("☑️ Select Reports")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(2, weight=1)
        
        # Instructions
        info_frame = ctk.CTkFrame(tab)
        info_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        
        info_label = ctk.CTkLabel(
            info_frame,
            text="Select specific reports to export",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        info_label.pack(padx=15, pady=10)
        
        # Controls frame
        controls_frame = ctk.CTkFrame(tab)
        controls_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        controls_frame.grid_columnconfigure(0, weight=1)
        
        # Search and buttons
        top_controls = ctk.CTkFrame(controls_frame, fg_color="transparent")
        top_controls.grid(row=0, column=0, sticky="ew", padx=15, pady=15)
        top_controls.grid_columnconfigure(0, weight=1)
        
        self.report_search_entry = ctk.CTkEntry(
            top_controls,
            placeholder_text="🔍 Search reports..."
        )
        self.report_search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.report_search_entry.bind("<KeyRelease>", self._on_report_search)
        
        self.refresh_reports_btn = ctk.CTkButton(
            top_controls,
            text="🔄 Refresh",
            command=self._refresh_reports,
            width=100,
            state="disabled"
        )
        self.refresh_reports_btn.grid(row=0, column=1, padx=(0, 10))
        
        self.select_all_btn = ctk.CTkButton(
            top_controls,
            text="✓ All",
            command=self._select_all_reports,
            width=80,
            state="disabled"
        )
        self.select_all_btn.grid(row=0, column=2, padx=(0, 10))
        
        self.clear_all_btn = ctk.CTkButton(
            top_controls,
            text="✗ Clear",
            command=self._clear_all_reports,
            width=80,
            state="disabled"
        )
        self.clear_all_btn.grid(row=0, column=3)
        
        # Selection counter
        self.selection_label = ctk.CTkLabel(
            controls_frame,
            text="Selected: 0 reports",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="gray"
        )
        self.selection_label.grid(row=1, column=0, sticky="w", padx=15, pady=(0, 10))
        
        # Scrollable report list
        self.reports_scrollable = ctk.CTkScrollableFrame(tab, label_text="Available Reports")
        self.reports_scrollable.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.reports_scrollable.grid_columnconfigure(0, weight=1)
        
        # Placeholder - will show loading indicator or login message
        self.reports_placeholder = ctk.CTkLabel(
            self.reports_scrollable,
            text="Please login to load reports",
            text_color="gray"
        )
        self.reports_placeholder.grid(row=0, column=0, pady=20)
        
    def _setup_log_tab(self):
        """Setup the activity log tab"""
        tab = self.tabview.tab("📋 Activity Log")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)
        
        # Controls
        controls_frame = ctk.CTkFrame(tab, fg_color="transparent")
        controls_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        
        log_label = ctk.CTkLabel(
            controls_frame,
            text="Activity Log:",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        log_label.pack(side="left", padx=(0, 10))
        
        clear_log_btn = ctk.CTkButton(
            controls_frame,
            text="Clear Log",
            command=self._clear_log,
            width=100
        )
        clear_log_btn.pack(side="right")
        
        # Log text area
        self.log_textbox = ctk.CTkTextbox(
            tab,
            wrap="word",
            font=ctk.CTkFont(family="Consolas", size=11)
        )
        self.log_textbox.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.log_textbox.configure(state="disabled")
    
    def _on_tab_changed(self, tab_name: str):
        """Handle tab change - LAZY LOAD REPORTS - NEW METHOD"""
        if "Select Reports" in tab_name or "☑️" in tab_name:
            # Only load reports if logged in and not already loaded
            if self.session_info and not self.reports_loaded:
                self._log("📊 Loading reports (first time)...")
                self._show_reports_loading()
                self._refresh_reports()
    
    def _show_reports_loading(self):
        """Show loading indicator in reports tab - NEW METHOD"""
        # Clear existing widgets
        for widget in self.reports_scrollable.winfo_children():
            widget.destroy()
        
        # Show loading message with spinner effect
        loading_label = ctk.CTkLabel(
            self.reports_scrollable,
            text="⏳ Loading reports, please wait...",
            text_color="gray",
            font=ctk.CTkFont(size=12)
        )
        loading_label.grid(row=0, column=0, pady=20)
        
        # Store reference for later removal
        self.reports_placeholder = loading_label
    
    # main_app.py - Part 3: Login and Folder Operations
# Add these methods to the SalesforceExporterApp class

    # ===== LOGIN OPERATIONS =====
    
    def _open_login_window(self):
        """Open login window"""
        login_win = LoginWindow(self, self._on_login_success)
        self.wait_window(login_win)
    
    def _on_login_success(self, session_info: dict):
        """Handle successful login - UPDATED: Only load folders, not reports"""
        self.session_info = session_info
        
        # Update status
        instance = session_info.get("instance_url", "")
        api_version = session_info.get("api_version", "")
        user_name = session_info.get("user_name", "")
        
        short_instance = instance.replace("https://", "")
        status_text = f"🟢 {short_instance}"
        if api_version:
            status_text += f" (API v{api_version})"
        
        self.status_label.configure(text=status_text, text_color="green")
        self.login_button.configure(text="Logout", command=self._logout)
        
        # Enable UI
        self.tabview.configure(state="normal")
        self.refresh_folders_btn.configure(state="normal")
        self.refresh_reports_btn.configure(state="normal")
        self.select_all_btn.configure(state="normal")
        self.clear_all_btn.configure(state="normal")
        
        # Log success
        self._log(f"✅ Login successful: {instance}")
        self._log(f"🔌 API Version: v{api_version}")
        if user_name:
            self._log(f"👤 User: {user_name}")
        
        # ONLY load folders on login (not reports - lazy load)
        self._log("🔄 Loading report folders...")
        self._refresh_folders()
        
        # Update reports tab placeholder
        if hasattr(self, 'reports_placeholder'):
            self.reports_placeholder.configure(
                text="Click this tab to load reports",
                text_color="gray"
            )
    
# ===== FIX 2: Replace the _logout method in Part 3 =====
# Find this method and replace it:

    def _logout(self):
        """Logout and clear session"""
        self.session_info = None
        self.available_folders = []
        self.available_reports = []  # Clear reports data
        self.selected_reports.clear()  # Clear selections
        self.reports_loaded = False  # Reset lazy load flag
        
        # Reset UI
        self.status_label.configure(text="🔴 Not logged in", text_color="gray")
        self.login_button.configure(text="Login to Salesforce", command=self._open_login_window)
        
        # Disable UI
        self.tabview.configure(state="disabled")
        self.folder_dropdown.configure(state="disabled", values=["Please login first"])
        self.folder_var.set("Please login first")
        self.folder_info_label.configure(text="Please login to see available folders", text_color="gray")
        self.refresh_folders_btn.configure(state="disabled")
        self.refresh_reports_btn.configure(state="disabled")
        self.select_all_btn.configure(state="disabled")
        self.clear_all_btn.configure(state="disabled")
        self.export_button.configure(state="disabled")
        
        # FIXED: Clear reports list completely
        for widget in self.reports_scrollable.winfo_children():
            widget.destroy()
        
        # Add placeholder back
        placeholder = ctk.CTkLabel(
            self.reports_scrollable,
            text="Please login to load reports",
            text_color="gray"
        )
        placeholder.grid(row=0, column=0, pady=20)
        self.reports_placeholder = placeholder
        
        # Reset selection counter
        self.selection_label.configure(text="Selected: 0 reports", text_color="gray")
        
        # Clear output path
        self.output_zip_path = None
        self.output_path_label.configure(text="No file selected", text_color="gray")
        
        # Reset progress
        self.progress_bar.set(0)
        self.progress_label.configure(text="Ready", text_color="gray")
        
        self._log("🔴 Logged out")

    
    # ===== FOLDER OPERATIONS =====
    
    def _refresh_folders(self):
        """Refresh folder list in background with loading indicator"""
        if not self.session_info:
            return
        
        self.refresh_folders_btn.configure(state="disabled", text="⏳ Loading...")
        self.folder_dropdown.configure(state="disabled")
        self.folder_info_label.configure(text="⏳ Loading folders...", text_color="gray")
        
        thread = threading.Thread(target=self._load_folders_worker, daemon=True)
        thread.start()
    
    def _load_folders_worker(self):
        """Background worker to load folders"""
        try:
            session_id = self.session_info.get("session_id")
            instance_url = self.session_info.get("instance_url")
            
            exporter = SalesforceReportExporter(session_id, instance_url)
            folders = exporter.list_report_folders()
            
            # Update UI via queue
            self.update_queue.put(("folders_loaded", folders))
            
        except Exception as e:
            self.update_queue.put(("folders_error", str(e)))
    
    def _on_folders_loaded(self, folders: List[Dict]):
        """Handle folders loaded"""
        # Filter out system folders
        filtered = [
            f for f in folders
            if f.get("name") and f.get("name") not in ["Automated Process", "System", "Hidden"]
            and not f.get("name").startswith("__")
        ]
        
        self.available_folders = filtered
        self._populate_folder_dropdown(filtered)
        
        self.refresh_folders_btn.configure(state="normal", text="🔄 Refresh")
        self._log(f"📁 Loaded {len(filtered)} folders")
    
    def _on_folders_error(self, error: str):
        """Handle folder loading error"""
        self.folder_dropdown.configure(values=["Error loading folders"])
        self.folder_var.set("Error loading folders")
        self.folder_info_label.configure(text=f"❌ Error: {error}", text_color="red")
        self.refresh_folders_btn.configure(state="normal", text="🔄 Refresh")
        self._log(f"❌ Error loading folders: {error}")
    
    def _populate_folder_dropdown(self, folders: List[Dict], search_term: str = ""):
        """Populate folder dropdown with folders"""
        if not folders:
            self.folder_dropdown.configure(values=["No folders found"], state="disabled")
            self.folder_var.set("No folders found")
            self.folder_info_label.configure(text="No report folders found", text_color="gray")
            return
        
        # Filter by search term
        if search_term:
            folders = [
                f for f in folders
                if search_term.lower() in f.get("name", "").lower()
            ]
        
        if not folders and search_term:
            self.folder_dropdown.configure(
                values=[f"No matches for '{search_term}'"],
                state="disabled"
            )
            self.folder_var.set(f"No matches for '{search_term}'")
            self.folder_info_label.configure(
                text=f"No matches for '{search_term}'",
                text_color="gray"
            )
            return
        
        # Build values list
        values = []
        folder_map = {}
        
        if not search_term:
            values.append("📚 All Reports (All Folders)")
            folder_map["📚 All Reports (All Folders)"] = "ALL"
        
        for folder in folders:
            name = folder.get("name", "Unnamed")
            folder_id = folder.get("id")
            folder_type = folder.get("type", "")
            
            icon = "📂"
            if folder_type == "Public":
                icon = "🌐"
            elif "My" in name:
                icon = "👤"
            
            display_name = f"{icon} {name}"
            values.append(display_name)
            folder_map[display_name] = folder_id
        
        # Store folder map as instance variable
        self.folder_map = folder_map
        
        # Update dropdown
        self.folder_dropdown.configure(values=values, state="normal")
        if values:
            self.folder_var.set(values[0])
        
        # Update info
        if search_term:
            self.folder_info_label.configure(
                text=f"Found {len(folders)} folders matching '{search_term}'",
                text_color="gray"
            )
        else:
            self.folder_info_label.configure(
                text=f"Found {len(folders)} folders available",
                text_color="gray"
            )
    
    def _on_folder_search(self, event):
        """Handle folder search"""
        search_term = self.folder_search_entry.get().strip()
        self._populate_folder_dropdown(self.available_folders, search_term)
    
    def _on_folder_selected(self, choice):
        """Handle folder selection"""
        if choice and hasattr(self, 'folder_map'):
            folder_id = self.folder_map.get(choice)
            if folder_id == "ALL":
                self.folder_info_label.configure(
                    text="Will export all reports from all folders",
                    text_color="gray"
                )
            elif folder_id:
                folder_name = choice.split(" ", 1)[1] if " " in choice else choice
                self.folder_info_label.configure(
                    text=f"Selected: {folder_name}",
                    text_color="gray"
                )
        
        self._update_export_button_state()
    
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
    
    # main_app.py - Part 4: Report Selection Operations
# Add these methods to the SalesforceExporterApp class

    # ===== REPORT SELECTION OPERATIONS =====
    
    def _refresh_reports(self):
        """Refresh reports list in background with loading indicator"""
        if not self.session_info:
            return
        
        self.refresh_reports_btn.configure(state="disabled", text="⏳ Loading...")
        self.select_all_btn.configure(state="disabled")
        self.clear_all_btn.configure(state="disabled")
        
        # Clear current selections
        self.selected_reports.clear()
        self._update_selection_counter()
        
        # Show loading indicator
        self._show_reports_loading()
        
        thread = threading.Thread(target=self._load_reports_worker, daemon=True)
        thread.start()
    
    def _load_reports_worker(self):
        """Background worker to load all reports"""
        try:
            session_id = self.session_info.get("session_id")
            instance_url = self.session_info.get("instance_url")
            
            exporter = SalesforceReportExporter(session_id, instance_url)
            reports = exporter.list_reports()
            
            # Update UI via queue
            self.update_queue.put(("reports_loaded", reports))
            
        except Exception as e:
            self.update_queue.put(("reports_error", str(e)))
    
    def _on_reports_loaded(self, reports: List[Dict]):
        """Handle reports loaded"""
        self.available_reports = reports
        self.reports_loaded = True  # Mark as loaded
        self._populate_reports_list(reports)
        
        self.refresh_reports_btn.configure(state="normal", text="🔄 Refresh")
        self.select_all_btn.configure(state="normal")
        self.clear_all_btn.configure(state="normal")
        
        self._log(f"📊 Loaded {len(reports)} reports")
    
    def _on_reports_error(self, error: str):
        """Handle report loading error"""
        self.reports_loaded = False  # Mark as not loaded on error
        
        # Clear loading indicator and show error
        for widget in self.reports_scrollable.winfo_children():
            widget.destroy()
        
        error_label = ctk.CTkLabel(
            self.reports_scrollable,
            text=f"❌ Error loading reports\n{error}",
            text_color="red"
        )
        error_label.grid(row=0, column=0, pady=20)
        
        self.refresh_reports_btn.configure(state="normal", text="🔄 Refresh")
        self.select_all_btn.configure(state="normal")
        self.clear_all_btn.configure(state="normal")
        
        self._log(f"❌ Error loading reports: {error}")
        messagebox.showerror("Error", f"Failed to load reports:\n\n{error}")
    
    def _populate_reports_list(self, reports: List[Dict], search_term: str = ""):
        """Populate the scrollable reports list with checkboxes"""
        # Clear existing widgets
        for widget in self.reports_scrollable.winfo_children():
            widget.destroy()
        
        if not reports:
            placeholder = ctk.CTkLabel(
                self.reports_scrollable,
                text="No reports found",
                text_color="gray"
            )
            placeholder.grid(row=0, column=0, pady=20)
            return
        
        # Filter by search term
        filtered_reports = reports
        if search_term:
            filtered_reports = [
                r for r in reports
                if search_term.lower() in r.get("name", "").lower()
            ]
        
        if not filtered_reports:
            placeholder = ctk.CTkLabel(
                self.reports_scrollable,
                text=f"No reports matching '{search_term}'",
                text_color="gray"
            )
            placeholder.grid(row=0, column=0, pady=20)
            return
        
        # Create checkboxes
        for idx, report in enumerate(filtered_reports):
            report_id = report.get("id")
            report_name = report.get("name", "Unnamed Report")
            folder_name = report.get("folderName", "Unknown Folder")
            
            # Create checkbox with report info
            checkbox_var = ctk.BooleanVar(
                value=report_id in self.selected_reports
            )
            
            checkbox = ctk.CTkCheckBox(
                self.reports_scrollable,
                text=f"{report_name} ({folder_name})",
                variable=checkbox_var,
                command=lambda rid=report_id, var=checkbox_var: self._on_report_checkbox_changed(rid, var)
            )
            checkbox.grid(row=idx, column=0, sticky="w", padx=10, pady=2)
        
        self._update_selection_counter()
    
    def _on_report_checkbox_changed(self, report_id: str, checkbox_var: ctk.BooleanVar):
        """Handle report checkbox change"""
        if checkbox_var.get():
            self.selected_reports.add(report_id)
        else:
            self.selected_reports.discard(report_id)
        
        self._update_selection_counter()
        self._update_export_button_state()
    
    def _on_report_search(self, event):
        """Handle report search"""
        search_term = self.report_search_entry.get().strip()
        self._populate_reports_list(self.available_reports, search_term)
    
    def _select_all_reports(self):
        """Select all visible reports"""
        search_term = self.report_search_entry.get().strip()
        
        # Get visible reports
        filtered_reports = self.available_reports
        if search_term:
            filtered_reports = [
                r for r in self.available_reports
                if search_term.lower() in r.get("name", "").lower()
            ]
        
        # Add all to selection
        for report in filtered_reports:
            self.selected_reports.add(report.get("id"))
        
        # Refresh UI
        self._populate_reports_list(self.available_reports, search_term)
        self._update_export_button_state()
    
    def _clear_all_reports(self):
        """Clear all report selections"""
        self.selected_reports.clear()
        
        # Refresh UI
        search_term = self.report_search_entry.get().strip()
        self._populate_reports_list(self.available_reports, search_term)
        self._update_export_button_state()
    
    def _update_selection_counter(self):
        """Update the selection counter label"""
        count = len(self.selected_reports)
        text = f"Selected: {count} report{'s' if count != 1 else ''}"
        
        if count > 0:
            self.selection_label.configure(text=text, text_color="#1f6aa5")
        else:
            self.selection_label.configure(text=text, text_color="gray")
    
    # ===== OUTPUT PATH =====
    
    def _browse_output_path(self):
        """Browse for output ZIP file location"""
        # Generate default filename
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M')
        
        # Determine filename based on current tab
        current_tab = self.tabview.get()
        if "Folder" in current_tab and hasattr(self, 'folder_map'):
            selected = self.folder_var.get()
            folder_id = self.folder_map.get(selected, "")
            if folder_id == "ALL":
                default_name = f"salesforce_reports_All_Reports_{timestamp}.zip"
            else:
                folder_name = selected.split(" ", 1)[1] if " " in selected else "reports"
                safe_name = "".join(c if c.isalnum() or c in " ._-" else "_" for c in folder_name)
                safe_name = safe_name.strip("_ ").replace(" ", "_")
                default_name = f"salesforce_reports_{safe_name}_{timestamp}.zip"
        else:
            default_name = f"salesforce_reports_selected_{timestamp}.zip"
        
        # Open file dialog
        filepath = filedialog.asksaveasfilename(
            title="Save ZIP File",
            defaultextension=".zip",
            filetypes=[("ZIP files", "*.zip"), ("All files", "*.*")],
            initialfile=default_name
        )
        
        if filepath:
            if not filepath.lower().endswith('.zip'):
                filepath += '.zip'
            
            self.output_zip_path = filepath
            
            # Update label (truncate if too long)
            display_path = filepath
            if len(filepath) > 70:
                display_path = "..." + filepath[-67:]
            
            self.output_path_label.configure(text=display_path, text_color="green")
            self._log(f"💾 Output: {filepath}")
            
            self._update_export_button_state()
    
    def _update_export_button_state(self):
        """Enable/disable export button based on conditions"""
        can_export = False
        
        if self.session_info and self.output_zip_path and not self.is_exporting:
            current_tab = self.tabview.get()
            
            if "Folder" in current_tab:
                # Folder mode: check if folder is selected
                if hasattr(self, 'folder_map'):
                    selected = self.folder_var.get()
                    folder_id = self.folder_map.get(selected)
                    can_export = folder_id is not None
            else:
                # Selected reports mode: check if reports are selected
                can_export = len(self.selected_reports) > 0
        
        if can_export:
            self.export_button.configure(state="normal")
        else:
            self.export_button.configure(state="disabled")
    
    # main_app.py - Part 5: Export Operations and Queue Processing
# Add these methods to the SalesforceExporterApp class

    # ===== EXPORT OPERATIONS =====
    
    def _start_export(self):
        """Start the export process"""
        if not self.session_info:
            messagebox.showwarning("Not Logged In", "Please login first.")
            return
        
        if not self.output_zip_path:
            messagebox.showwarning("No Output", "Please select output location.")
            return
        
        current_tab = self.tabview.get()
        
        if "Folder" in current_tab:
            # Folder export mode
            if not hasattr(self, 'folder_map'):
                messagebox.showwarning("No Folder", "Please select a folder first.")
                return
            
            selected = self.folder_var.get()
            folder_id = self.folder_map.get(selected)
            
            if not folder_id:
                messagebox.showwarning("No Folder", "Please select a folder to export.")
                return
            
            self.is_exporting = True
            self._set_export_ui_state(False)
            
            folder_name = selected.split(" ", 1)[1] if " " in selected else selected
            if folder_id == "ALL":
                self._log("🚀 Starting export of ALL reports from ALL folders...")
            else:
                self._log(f"🚀 Starting export from folder: {folder_name}")
            
            # Start export in background
            thread = threading.Thread(
                target=self._export_folder_worker,
                args=(folder_id,),
                daemon=True
            )
            thread.start()
        
        else:
            # Selected reports mode
            if len(self.selected_reports) == 0:
                messagebox.showwarning("No Reports", "Please select at least one report.")
                return
            
            self.is_exporting = True
            self._set_export_ui_state(False)
            
            self._log(f"🚀 Starting export of {len(self.selected_reports)} selected reports...")
            
            # Start export in background
            thread = threading.Thread(
                target=self._export_selected_worker,
                args=(list(self.selected_reports),),
                daemon=True
            )
            thread.start()
    
    def _export_folder_worker(self, folder_id: str):
        """Background worker for folder export"""
        try:
            session_id = self.session_info.get("session_id")
            instance_url = self.session_info.get("instance_url")
            
            def progress_callback(done, total):
                self.update_queue.put(("progress", (done, total)))
            
            exporter = SalesforceReportExporter(
                session_id,
                instance_url,
                progress_callback=progress_callback
            )
            
            if folder_id == "ALL":
                result = exporter.export_all_reports_to_zip(self.output_zip_path)
            else:
                result = exporter.export_reports_by_folder_to_zip(
                    self.output_zip_path,
                    folder_id
                )
            
            self.update_queue.put(("export_complete", result))
            
        except Exception as e:
            self.update_queue.put(("export_error", str(e)))
    
# ===== FIX 1: Replace the _export_selected_worker method in Part 5 =====
# Find this method and replace it:

    def _export_selected_worker(self, report_ids: List[str]):
        """Background worker for selected reports export"""
        try:
            session_id = self.session_info.get("session_id")
            instance_url = self.session_info.get("instance_url")
            
            def progress_callback(done, total):
                self.update_queue.put(("progress", (done, total)))
            
            exporter = SalesforceReportExporter(
                session_id,
                instance_url,
                progress_callback=progress_callback
            )
            
            result = exporter.export_selected_reports_to_zip(
                self.output_zip_path,
                report_ids
            )
            
            self.update_queue.put(("export_complete", result))
            
        except Exception as e:
            self.update_queue.put(("export_error", str(e)))

    def _on_export_progress(self, progress_data):
        """Handle export progress update"""
        done, total = progress_data
        
        if total > 0:
            progress = done / total
            self.progress_bar.set(progress)
            
            percentage = int(progress * 100)
            self.progress_label.configure(
                text=f"⏳ {done}/{total} reports ({percentage}%)",
                text_color="gray"
            )
            
            # Only log every 5 reports or at milestones to avoid spam
            if done % 5 == 0 or done == total:
                self.update_queue.put(("log", f"📦 Exported {done}/{total}"))
    
    def _on_export_complete(self, result: Dict):
        """Handle export completion"""
        self.is_exporting = False
        self._set_export_ui_state(True)
        
        total = result.get("total", 0)
        failed = result.get("failed", [])
        successful = result.get("successful", [])
        zip_path = result.get("zip", "")
        folder_name = result.get("folder_name", "")
        
        # Update progress
        self.progress_bar.set(1.0)
        self.progress_label.configure(
            text=f"✅ Done! {len(successful)}/{total} reports",
            text_color="green"
        )
        
        # Log summary
        self._log(f"✅ Export completed!")
        self._log(f"📊 Total: {total} reports")
        self._log(f"✓ Successful: {len(successful)}")
        self._log(f"✗ Failed: {len(failed)}")
        self._log(f"💾 Saved to: {zip_path}")
        
        if failed:
            self._log("⚠️ Failed reports:")
            for f in failed[:5]:
                self._log(f"  • {f.get('name')}: {f.get('error')[:50]}")
            if len(failed) > 5:
                self._log(f"  ... and {len(failed) - 5} more (see summary file)")
        
        # Show completion message
        message = f"Export completed!\n\n"
        message += f"Source: {folder_name}\n"
        message += f"Total: {total} reports\n"
        message += f"Successful: {len(successful)}\n"
        message += f"Failed: {len(failed)}\n\n"
        message += f"ZIP saved to:\n{zip_path}"
        
        messagebox.showinfo("Export Complete", message)
    
    def _on_export_error(self, error_msg: str):
        """Handle export error"""
        self.is_exporting = False
        self._set_export_ui_state(True)
        
        self.progress_bar.set(0)
        self.progress_label.configure(text="❌ Error", text_color="red")
        
        self._log(f"❌ Export failed: {error_msg}")
        messagebox.showerror("Export Failed", f"Export failed:\n\n{error_msg}")
    
    def _set_export_ui_state(self, enabled: bool):
        """Enable/disable UI during export"""
        state = "normal" if enabled else "disabled"
        
        self.login_button.configure(state=state)
        self.browse_button.configure(state=state)
        self.refresh_folders_btn.configure(state=state)
        self.refresh_reports_btn.configure(state=state)
        self.select_all_btn.configure(state=state)
        self.clear_all_btn.configure(state=state)
        
        if enabled:
            self._update_export_button_state()
        else:
            self.export_button.configure(state="disabled")
    
    # ===== QUEUE PROCESSING =====
    
    def _process_queue(self):
        """Process updates from background threads"""
        try:
            while True:
                item = self.update_queue.get_nowait()
                
                if isinstance(item, tuple):
                    event_type = item[0]
                    data = item[1] if len(item) > 1 else None
                    
                    if event_type == "folders_loaded":
                        self._on_folders_loaded(data)
                    elif event_type == "folders_error":
                        self._on_folders_error(data)
                    elif event_type == "reports_loaded":
                        self._on_reports_loaded(data)
                    elif event_type == "reports_error":
                        self._on_reports_error(data)
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


# ===== ENTRY POINT =====

def main():
    """Main entry point for the application"""
    app = SalesforceExporterApp()
    app.mainloop()


if __name__ == "__main__":
    main()