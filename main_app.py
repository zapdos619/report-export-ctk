# main_app.py - REDESIGNED VERSION
# Salesforce Report Exporter with Tree View and Dual-Panel Selection

import customtkinter as ctk
import threading
import queue
import os
import datetime
from tkinter import filedialog, messagebox, ttk
from typing import Optional, List, Dict, Any
from login_window import LoginWindow
from exporter import SalesforceReportExporter


class SalesforceExporterApp(ctk.CTk):
    """
    Main application window for Salesforce Report Exporter.
    Redesigned with folder/report tree view and dual-panel selection.
    """
    
    def __init__(self):
        super().__init__()
        
        # Window setup - CHANGED: 1400x900 -> 1200x800
        self.title("Salesforce Report Exporter")
        self.geometry("1200x800")
        
        # Set theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        
        # Session data
        self.session_info: Optional[Dict] = None
        self.output_zip_path: Optional[str] = None
        self.available_folders: List[Dict] = []
        self.available_reports: List[Dict] = []
        self.reports_by_folder: Dict[str, List[Dict]] = {}
        
        # Selection tracking
        self.selected_items: Dict[str, Dict] = {}
        self.is_exporting: bool = False
        self.search_timer = None 
        
        # Queue for thread-safe UI updates
        self.update_queue = queue.Queue()
        
        # Setup UI
        self._setup_ui()
        
        # Center window on screen - ADDED
        self.after(100, self._center_window)
        
        # Start queue processor
        self._process_queue()
    
    # ADD THIS NEW METHOD anywhere in your class
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
        
    def _create_header(self):
        """Create header section with title and login status"""
        # CHANGED: height=80 -> height=60
        header_frame = ctk.CTkFrame(self, height=60, corner_radius=0)
        header_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        header_frame.grid_propagate(False)
        
        # Left side - Title
        left_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        left_frame.pack(side="left", fill="both", expand=True, padx=15, pady=8)
        
        title_label = ctk.CTkLabel(
            left_frame,
            text="📊 Salesforce Report Exporter",
            font=ctk.CTkFont(size=18, weight="bold")  # CHANGED: 22 -> 18
        )
        title_label.pack(anchor="w")
        
        subtitle_label = ctk.CTkLabel(
            left_frame,
            text="Select folders and reports to export",
            font=ctk.CTkFont(size=11),  # CHANGED: 12 -> 11
            text_color="gray"
        )
        subtitle_label.pack(anchor="w", pady=(3, 0))  # CHANGED: 5 -> 3
        
        # Right side - Login status and button
        right_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        right_frame.pack(side="right", padx=15, pady=8)
        
        self.status_label = ctk.CTkLabel(
            right_frame,
            text="🔴 Not logged in",
            font=ctk.CTkFont(size=11),  # CHANGED: 12 -> 11
            text_color="gray"
        )
        self.status_label.pack(pady=(0, 4))  # CHANGED: 5 -> 4
        
        self.login_button = ctk.CTkButton(
            right_frame,
            text="Login to Salesforce",
            command=self._open_login_window,
            width=140,  # CHANGED: 150 -> 140
            height=28   # CHANGED: 32 -> 28
        )
        self.login_button.pack()

    
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
        """Create left panel - Available folders and reports"""
        
        left_panel = ctk.CTkFrame(parent)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(8, 4), pady=8)  # CHANGED: padx
        left_panel.grid_rowconfigure(3, weight=1)  # CHANGED: row 2 -> 3
        left_panel.grid_columnconfigure(0, weight=1)
        
        # Header
        header_label = ctk.CTkLabel(
            left_panel,
            text="Available Items",
            font=ctk.CTkFont(size=14, weight="bold")  # CHANGED: 16 -> 14
        )
        header_label.grid(row=0, column=0, sticky="w", padx=12, pady=(12, 8))  # CHANGED: padx, pady
        
        # "All Folders" button
        self.all_folders_btn = ctk.CTkButton(
            left_panel,
            text="📁 All Folders",
            command=self._load_all_folders,
            height=32,  # CHANGED: 35 -> 32
            fg_color="#1f6aa5",
            hover_color="#144870",
            state="disabled"
        )
        self.all_folders_btn.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 8))  # CHANGED: padx, pady
        
        # Search box
        search_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        search_frame.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 8))  # CHANGED: padx, pady
        search_frame.grid_columnconfigure(0, weight=1)
        
        self.left_search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="🔍 Search folders and reports...",
            height=28  # CHANGED: 32 -> 28
        )
        self.left_search_entry.grid(row=0, column=0, sticky="ew")
        self.left_search_entry.bind("<KeyRelease>", self._on_left_search)
        
        # Tree view container
        self.tree_container = ctk.CTkScrollableFrame(
            left_panel,
            fg_color="#2b2b2b",
            corner_radius=5
        )
        self.tree_container.grid(row=3, column=0, sticky="nsew", padx=12, pady=(0, 12))  # CHANGED: padx, pady
        self.tree_container.grid_columnconfigure(0, weight=1)
        
        # Placeholder
        self.tree_placeholder = ctk.CTkLabel(
            self.tree_container,
            text="Please login to load folders and reports",
            text_color="gray",
            font=ctk.CTkFont(size=11)  # CHANGED: 12 -> 11
        )
        self.tree_placeholder.grid(row=0, column=0, pady=20)
        
        # Store reference to tree items
        self.tree_items: Dict[str, Dict] = {}
    
    
    def _create_right_panel(self, parent):
        """Create right panel - Selected items for export"""
        
        right_panel = ctk.CTkFrame(parent)
        right_panel.grid(row=0, column=1, sticky="nsew", padx=(4, 8), pady=8)  # CHANGED: padx
        right_panel.grid_rowconfigure(2, weight=1)
        right_panel.grid_columnconfigure(0, weight=1)
        
        # Header
        header_label = ctk.CTkLabel(
            right_panel,
            text="Selected for Export",
            font=ctk.CTkFont(size=14, weight="bold")  # CHANGED: 16 -> 14
        )
        header_label.grid(row=0, column=0, sticky="w", padx=12, pady=(12, 8))  # CHANGED: padx, pady
        
        # Selection count
        self.selection_count_label = ctk.CTkLabel(
            right_panel,
            text="0 reports selected",
            font=ctk.CTkFont(size=11),  # CHANGED: 12 -> 11
            text_color="gray"
        )
        self.selection_count_label.grid(row=1, column=0, sticky="w", padx=12, pady=(0, 8))  # CHANGED: padx, pady
        
        # Selected items list
        self.selected_container = ctk.CTkScrollableFrame(
            right_panel,
            fg_color="#2b2b2b",
            corner_radius=5
        )
        self.selected_container.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 12))  # CHANGED: padx, pady
        self.selected_container.grid_columnconfigure(0, weight=1)
        
        # Placeholder
        self.selected_placeholder = ctk.CTkLabel(
            self.selected_container,
            text="No reports selected.\nSelect folders or reports from the left panel.",
            text_color="gray",
            font=ctk.CTkFont(size=11),  # CHANGED: 12 -> 11
            justify="center"
        )
        self.selected_placeholder.grid(row=0, column=0, pady=20)
        
        # Actions section
        actions_frame = ctk.CTkFrame(right_panel, fg_color="transparent")
        actions_frame.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 12))  # CHANGED: padx, pady
        actions_frame.grid_columnconfigure(0, weight=1)
        
        actions_label = ctk.CTkLabel(
            actions_frame,
            text="Actions",
            font=ctk.CTkFont(size=12, weight="bold")  # CHANGED: 13 -> 12
        )
        actions_label.grid(row=0, column=0, sticky="w", pady=(0, 4))  # CHANGED: 5 -> 4
        
        # Clear all button
        self.clear_selected_button = ctk.CTkButton(
            actions_frame,
            text="Clear All Selected",
            command=self._clear_all_selected,
            height=32,  # CHANGED: 35 -> 32
            fg_color="#d32f2f",
            hover_color="#9a2222",
            state="disabled"
        )
        self.clear_selected_button.grid(row=1, column=0, sticky="ew", pady=(0, 4))  # CHANGED: 5 -> 4
        
    
    def _create_bottom_section(self):
        """Create bottom section with file naming, progress, export button, and log"""
        
        bottom_frame = ctk.CTkFrame(self, corner_radius=0)
        bottom_frame.grid(row=2, column=0, sticky="ew", padx=0, pady=0)
        bottom_frame.grid_columnconfigure(0, weight=1)
        
        # File naming section
        file_frame = ctk.CTkFrame(bottom_frame)
        file_frame.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))  # CHANGED: padx, pady
        file_frame.grid_columnconfigure(1, weight=1)
        
        zip_label = ctk.CTkLabel(
            file_frame,
            text="ZIP Filename:",
            font=ctk.CTkFont(size=11, weight="bold"),  # CHANGED: 12 -> 11
            width=110  # CHANGED: 120 -> 110
        )
        zip_label.grid(row=0, column=0, padx=(12, 8), pady=8, sticky="w")  # CHANGED: padx
        
        self.filename_entry = ctk.CTkEntry(
            file_frame,
            placeholder_text="salesforce_reports_20251126_0026.zip",
            height=30  # CHANGED: 35 -> 30
        )
        self.filename_entry.grid(row=0, column=1, sticky="ew", padx=(0, 8), pady=8)
        
        self._generate_default_filename()
        
        # Save location section
        location_frame = ctk.CTkFrame(bottom_frame)
        location_frame.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 4))  # CHANGED: padx, pady
        location_frame.grid_columnconfigure(1, weight=1)
        
        location_label = ctk.CTkLabel(
            location_frame,
            text="Save Location:",
            font=ctk.CTkFont(size=11, weight="bold"),  # CHANGED: 12 -> 11
            width=110  # CHANGED: 120 -> 110
        )
        location_label.grid(row=0, column=0, padx=(12, 8), pady=8, sticky="w")  # CHANGED: padx
        
        self.location_entry = ctk.CTkEntry(
            location_frame,
            placeholder_text="Click Browse to select save location...",
            height=30,  # CHANGED: 35 -> 30
            state="readonly"
        )
        self.location_entry.grid(row=0, column=1, sticky="ew", padx=(0, 8), pady=8)
        
        self.browse_button = ctk.CTkButton(
            location_frame,
            text="Browse...",
            command=self._browse_save_location,
            width=90,  # CHANGED: 100 -> 90
            height=30  # CHANGED: 35 -> 30
        )
        self.browse_button.grid(row=0, column=2, padx=(0, 12), pady=8)  # CHANGED: padx
        
        # Export button
        self.export_button = ctk.CTkButton(
            bottom_frame,
            text="🚀 Export Reports",
            command=self._start_export,
            height=38,  # CHANGED: 45 -> 38
            font=ctk.CTkFont(size=14, weight="bold"),  # CHANGED: 15 -> 14
            fg_color="#1f6aa5",
            hover_color="#144870",
            state="disabled"
        )
        self.export_button.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 4))  # CHANGED: padx, pady
        
        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(bottom_frame, height=16)  # CHANGED: 20 -> 16
        self.progress_bar.grid(row=3, column=0, sticky="ew", padx=8, pady=(0, 4))  # CHANGED: padx, pady
        self.progress_bar.set(0)
        
        # Progress label
        self.progress_label = ctk.CTkLabel(
            bottom_frame,
            text="Ready to export",
            font=ctk.CTkFont(size=10),  # CHANGED: 11 -> 10
            text_color="gray"
        )
        self.progress_label.grid(row=4, column=0, sticky="w", padx=12, pady=(0, 4))  # CHANGED: padx, pady
        
        # Activity Log section - REDUCED HEIGHT
        log_frame = ctk.CTkFrame(bottom_frame, height=120)  # CHANGED: 150 -> 120
        log_frame.grid(row=5, column=0, sticky="ew", padx=8, pady=(4, 8))  # CHANGED: padx, pady
        log_frame.grid_propagate(False)
        log_frame.grid_rowconfigure(1, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)
        
        log_header_frame = ctk.CTkFrame(log_frame, fg_color="transparent")
        log_header_frame.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))  # CHANGED: padx, pady
        
        log_header_label = ctk.CTkLabel(
            log_header_frame,
            text="📋 Activity Log",
            font=ctk.CTkFont(size=12, weight="bold")  # CHANGED: 13 -> 12
        )
        log_header_label.pack(side="left")
        
        clear_log_btn = ctk.CTkButton(
            log_header_frame,
            text="Clear Log",
            command=self._clear_log,
            width=70,  # CHANGED: 80 -> 70
            height=22,  # CHANGED: 25 -> 22
            font=ctk.CTkFont(size=10)  # CHANGED: 11 -> 10
        )
        clear_log_btn.pack(side="right")
        
        # Log textbox
        self.log_textbox = ctk.CTkTextbox(
            log_frame,
            wrap="word",
            font=ctk.CTkFont(family="Consolas", size=9),  # CHANGED: 10 -> 9
            fg_color="#1a1a1a"
        )
        self.log_textbox.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))  # CHANGED: padx
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
    
    def _open_login_window(self):
        """Open login window"""
        login_win = LoginWindow(self, self._on_login_success)
        self.wait_window(login_win)
    
    def _on_login_success(self, session_info: dict):
        """Handle successful login"""
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
        
        # Enable buttons - ADD THESE LINES
        self.all_folders_btn.configure(state="normal")
        
        # Log success
        self._log(f"✅ Login successful: {instance}")
        self._log(f"🔌 API Version: v{api_version}")
        if user_name:
            self._log(f"👤 User: {user_name}")
        
        # Auto-load folders and reports
        self._log("🔄 Loading report folders and reports...")
        self._load_all_folders()
    
    def _logout(self):
        """Logout and clear session"""
        self.session_info = None
        self.available_folders = []
        self.available_reports = []
        self.reports_by_folder = {}
        self.selected_items.clear()
        self.tree_items.clear()
        
        # Reset UI
        self.status_label.configure(text="🔴 Not logged in", text_color="gray")
        self.login_button.configure(text="Login to Salesforce", command=self._open_login_window)
        
        # Disable buttons (ONLY the ones that exist)
        self.all_folders_btn.configure(state="disabled")
        self.export_button.configure(state="disabled")
        self.clear_selected_button.configure(state="disabled")
        
        # Clear tree completely
        for widget in self.tree_container.winfo_children():
            widget.destroy()
        
        self.tree_placeholder = ctk.CTkLabel(
            self.tree_container,
            text="Please login to load folders and reports",
            text_color="gray",
            font=ctk.CTkFont(size=11)
        )
        self.tree_placeholder.grid(row=0, column=0, pady=20)
        
        # Clear selected panel completely
        for widget in self.selected_container.winfo_children():
            widget.destroy()
        
        self.selected_placeholder = ctk.CTkLabel(
            self.selected_container,
            text="No reports selected.\nSelect folders or reports from the left panel.",
            text_color="gray",
            font=ctk.CTkFont(size=11),
            justify="center"
        )
        self.selected_placeholder.grid(row=0, column=0, pady=30)
        
        # Reset selection count
        self.selection_count_label.configure(text="0 reports selected", text_color="gray")
        
        # Clear output path
        self.output_zip_path = None
        self.location_entry.configure(state="normal")
        self.location_entry.delete(0, "end")
        self.location_entry.configure(state="readonly")
        
        # Reset progress
        self.progress_bar.set(0)
        self.progress_label.configure(text="Ready to export", text_color="gray")
        
        # Reset filename
        self._generate_default_filename()
        
        self._log("🔴 Logged out")
    
    # ===== LOAD FOLDERS AND REPORTS =====
    
    def _load_all_folders(self):
        """Load all folders and reports in background"""
        if not self.session_info:
            return
        
        # Disable button and show loading
        self.all_folders_btn.configure(state="disabled", text="⏳ Loading...")
        
        # Show loading indicator in tree
        for widget in self.tree_container.winfo_children():
            widget.destroy()
        
        loading_label = ctk.CTkLabel(
            self.tree_container,
            text="⏳ Loading folders and reports...\nThis may take a moment.",
            text_color="gray",
            font=ctk.CTkFont(size=12)
        )
        loading_label.grid(row=0, column=0, pady=30)
        
        self._log("🔄 Fetching folders and reports from Salesforce...")
        
        thread = threading.Thread(target=self._load_data_worker, daemon=True)
        thread.start()
    
    def _load_data_worker(self):
        """Background worker to load folders and reports"""
        try:
            session_id = self.session_info.get("session_id")
            instance_url = self.session_info.get("instance_url")
            
            exporter = SalesforceReportExporter(session_id, instance_url)
            
            # Step 1: Load folders
            folders = exporter.list_report_folders()
            self.update_queue.put(("log", f"Loaded {len(folders)} folders"))
            
            # Step 2: Load ALL reports (not filtered by folder)
            all_reports = exporter.list_reports()
            self.update_queue.put(("log", f"Loaded {len(all_reports)} total reports"))
            
            # Step 3: For each folder, get reports in that folder using SOQL
            reports_by_folder_id = {}
            
            for folder in folders:
                folder_id = folder.get("id")
                folder_name = folder.get("name")
                
                try:
                    # Query reports specifically for this folder
                    folder_reports = exporter.list_reports(folder_id=folder_id)
                    reports_by_folder_id[folder_id] = folder_reports
                    
                    if folder_reports:
                        self.update_queue.put(("log", f"  Folder '{folder_name}': {len(folder_reports)} reports"))
                except Exception as e:
                    self.update_queue.put(("log", f"  Error loading reports for '{folder_name}': {str(e)}"))
                    reports_by_folder_id[folder_id] = []
            
            # Update UI via queue
            self.update_queue.put(("data_loaded", {
                "folders": folders,
                "reports": all_reports,
                "reports_by_folder": reports_by_folder_id
            }))
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            self.update_queue.put(("log", f"ERROR: {error_details}"))
            self.update_queue.put(("data_error", str(e)))
    
    def _on_data_loaded(self, data: Dict):
        """Handle data loaded successfully"""
        self.available_folders = data.get("folders", [])
        self.available_reports = data.get("reports", [])
        self.reports_by_folder = data.get("reports_by_folder", {})
        
        # Filter out system folders
        filtered_folders = [
            f for f in self.available_folders
            if f.get("name") and f.get("name") not in ["Automated Process", "System", "Hidden"]
            and not f.get("name").startswith("__")
        ]
        
        self.available_folders = filtered_folders
        
        # Count total reports
        total_reports_in_folders = sum(len(reports) for reports in self.reports_by_folder.values())
        
        # Clear loading indicator
        for widget in self.tree_container.winfo_children():
            widget.destroy()
        
        # Populate tree
        self._populate_tree()
        
        # Re-enable button
        self.all_folders_btn.configure(state="normal", text="📁 All Folders")
        
        # Log results
        self._log(f"✅ Loaded {len(filtered_folders)} folders")
        self._log(f"✅ Found {total_reports_in_folders} reports across all folders")
        
        if total_reports_in_folders == 0:
            self._log("⚠️ No reports found. Check folder permissions.")
        
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
        
    def _create_folder_item(self, row: int, folder: Dict, reports_to_show: List[Dict]):
        """Create a folder item in the tree"""
        
        folder_id = folder.get("id")
        folder_name = folder.get("name", "Unnamed Folder")
        folder_type = folder.get("type", "")
        
        # Use the filtered reports passed in (not from self.reports_by_folder)
        reports_in_folder = reports_to_show
        
        # Main folder frame
        folder_frame = ctk.CTkFrame(self.tree_container, fg_color="#333333", corner_radius=5)
        folder_frame.grid(row=row * 2, column=0, sticky="ew", padx=5, pady=3)
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
        
        # Reports container (initially hidden)
        reports_frame = ctk.CTkFrame(self.tree_container, fg_color="#2b2b2b")
        reports_frame.grid(row=row * 2 + 1, column=0, sticky="ew", padx=(30, 5), pady=(0, 3))
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
            "report_checkboxes": {}  # Initialize empty dict
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
            no_reports_label.grid(row=0, column=0, padx=20, pady=10)
    
    def _create_report_items(self, parent_frame, folder_id: str, reports: List[Dict]):
        """Create report checkboxes inside a folder's reports frame"""
        
        for idx, report in enumerate(reports):
            report_id = report.get("id")
            report_name = report.get("name", "Unnamed Report")
            
            # Report item frame
            report_frame = ctk.CTkFrame(parent_frame, fg_color="transparent")
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
            
            # Store report checkbox reference in tree_items
            if "report_checkboxes" not in self.tree_items[folder_id]:
                self.tree_items[folder_id]["report_checkboxes"] = {}
            
            self.tree_items[folder_id]["report_checkboxes"][report_id] = {
                "checkbox": report_checkbox,
                "checkbox_var": report_checkbox_var,
                "name": report_name
            }
    
    def _toggle_folder_expansion(self, folder_id: str):
        """Toggle folder expansion to show/hide reports"""
        
        if folder_id not in self.tree_items:
            return
        
        tree_item = self.tree_items[folder_id]
        reports_frame = tree_item["reports_frame"]
        expand_btn = tree_item["expand_btn"]
        is_expanded = tree_item["expanded"]
        
        if is_expanded:
            # Collapse
            reports_frame.grid_remove()
            expand_btn.configure(text="▶")
            tree_item["expanded"] = False
        else:
            # Expand
            reports_frame.grid()
            expand_btn.configure(text="▼")
            tree_item["expanded"] = True
    
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
        """Refresh the selected items panel"""
        
        # Clear existing widgets
        for widget in self.selected_container.winfo_children():
            widget.destroy()
        
        if not self.selected_items:
            # Show placeholder
            self.selected_placeholder = ctk.CTkLabel(
                self.selected_container,
                text="No reports selected.\nSelect folders or reports from the left panel.",
                text_color="gray",
                font=ctk.CTkFont(size=12),
                justify="center"
            )
            self.selected_placeholder.grid(row=0, column=0, pady=30)
            
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
            # Folder header
            folder_header = ctk.CTkFrame(self.selected_container, fg_color="#333333", corner_radius=3)
            folder_header.grid(row=row, column=0, sticky="ew", padx=5, pady=(5, 2))
            folder_header.grid_columnconfigure(0, weight=1)
            
            folder_label = ctk.CTkLabel(
                folder_header,
                text=f"📁 {folder_name} ({len(items)} reports)",
                font=ctk.CTkFont(size=11, weight="bold"),
                anchor="w"
            )
            folder_label.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
            
            row += 1
            
            # Report items under this folder
            for item in sorted(items, key=lambda x: x["name"]):
                item_frame = ctk.CTkFrame(self.selected_container, fg_color="#2b2b2b", corner_radius=3)
                item_frame.grid(row=row, column=0, sticky="ew", padx=(15, 5), pady=1)
                item_frame.grid_columnconfigure(0, weight=1)
                
                item_label = ctk.CTkLabel(
                    item_frame,
                    text=f"  📄 {item['name']}",
                    font=ctk.CTkFont(size=10),
                    anchor="w"
                )
                item_label.grid(row=0, column=0, sticky="ew", padx=10, pady=4)
                
                # Remove button
                remove_btn = ctk.CTkButton(
                    item_frame,
                    text="✕",
                    width=25,
                    height=20,
                    fg_color="transparent",
                    hover_color="#d32f2f",
                    font=ctk.CTkFont(size=12),
                    command=lambda item_id=item['id']: self._remove_item_from_selected(item_id)
                )
                remove_btn.grid(row=0, column=1, padx=5, pady=4)
                
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
        
        can_export = (
            self.session_info is not None and
            self.output_zip_path is not None and
            len(self.selected_items) > 0 and
            not self.is_exporting
        )
        
        if can_export:
            self.export_button.configure(state="normal")
        else:
            self.export_button.configure(state="disabled")
    
    # ===== EXPORT OPERATIONS =====
    
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
        
        # Start export in background
        thread = threading.Thread(
            target=self._export_worker,
            args=(report_ids,),
            daemon=True
        )
        thread.start()
    
    def _export_worker(self, report_ids: List[str]):
        """Background worker for export"""
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
                text=f"Exporting: {done}/{total} reports ({percentage}%)",
                text_color="#1f6aa5"
            )
            
            if done % 5 == 0 or done == total:  # Log every 5 reports
                self.update_queue.put(("log", f"📦 Exported {done}/{total} reports"))
    
    def _on_export_complete(self, result: Dict):
        """Handle export completion"""
        self.is_exporting = False
        self._set_export_ui_state(True)
        
        total = result.get("total", 0)
        failed = result.get("failed", [])
        successful = result.get("successful", [])
        zip_path = result.get("zip", "")
        
        # Update progress
        self.progress_bar.set(1.0)
        self.progress_label.configure(
            text=f"✅ Export completed! {len(successful)}/{total} reports exported",
            text_color="green"
        )
        
        # Log summary
        self._log(f"✅ Export completed!")
        self._log(f"📊 Total: {total} reports")
        self._log(f"✔ Successful: {len(successful)}")
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
        message += f"Total: {total} reports\n"
        message += f"Successful: {len(successful)}\n"
        message += f"Failed: {len(failed)}\n\n"
        message += f"ZIP saved to:\n{zip_path}"
        
        messagebox.showinfo("Export Complete", message)
        
        # Ask if user wants to open folder
        result = messagebox.askyesno("Open Folder?", "Would you like to open the folder containing the exported file?")
        if result:
            import subprocess
            import platform
            
            folder = os.path.dirname(zip_path)
            if platform.system() == "Windows":
                os.startfile(folder)
            elif platform.system() == "Darwin":  # macOS
                subprocess.Popen(["open", folder])
            else:  # Linux
                subprocess.Popen(["xdg-open", folder])
    
    def _on_export_error(self, error_msg: str):
        """Handle export error"""
        self.is_exporting = False
        self._set_export_ui_state(True)
        
        self.progress_bar.set(0)
        self.progress_label.configure(text="❌ Export failed", text_color="red")
        
        self._log(f"❌ Export failed: {error_msg}")
        messagebox.showerror("Export Failed", f"Export failed:\n\n{error_msg}")
    
    def _set_export_ui_state(self, enabled: bool):
        """Enable/disable UI during export"""
        state = "normal" if enabled else "disabled"
        
        # Only manage buttons that actually exist
        self.login_button.configure(state=state)
        self.browse_button.configure(state=state)
        self.all_folders_btn.configure(state=state)
        
        # Clear Selected button
        if enabled and len(self.selected_items) > 0:
            self.clear_selected_button.configure(state="normal")
        else:
            self.clear_selected_button.configure(state="disabled")
        
        # Filename entry
        if enabled:
            self.filename_entry.configure(state="normal")
            self._update_export_button_state()
        else:
            self.filename_entry.configure(state="disabled")
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
                    
                    if event_type == "data_loaded":
                        self._on_data_loaded(data)
                    elif event_type == "data_error":
                        self._on_data_error(data)
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