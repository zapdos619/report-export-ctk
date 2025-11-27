# login_window.py - TRULY RESPONSIVE VERSION
# All components resize proportionally based on window size

import customtkinter as ctk
import threading
from typing import Optional, Callable
from salesforce_auth import SalesforceAuth, SalesforceAuthError


class LoginWindow(ctk.CTkToplevel):
    """
    Fully responsive login window that adapts to ANY monitor.
    All components scale proportionally with window size.
    """
    
    def __init__(self, parent, on_login_success: Callable, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        
        self.on_login_success = on_login_success
        self.session_info = None
        
        # Initial setup
        self.title("Salesforce Login")
        
        # Make it modal
        self.transient(parent)
        self.grab_set()
        
        # Hide initially
        self.withdraw()
        self.update_idletasks()
        
        # Calculate size for current monitor
        self._calculate_responsive_size()
        
        # Setup UI with calculated sizes
        self._setup_ui()
        
        # Show and center
        self.deiconify()
        self.after(50, self._center_on_current_monitor)
    
    def _calculate_responsive_size(self):
        """Calculate responsive window and component sizes"""
        self.update_idletasks()
        
        # Get current monitor dimensions
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        
        # Determine window size based on screen height
        if screen_height <= 768:
            # Small screens
            window_height = int(screen_height * 0.75)
            self.compact_mode = True
        elif screen_height <= 900:
            # Medium screens
            window_height = int(screen_height * 0.70)
            self.compact_mode = True
        elif screen_height <= 1080:
            # HD screens
            window_height = int(screen_height * 0.62)
            self.compact_mode = False
        else:
            # Large screens (2K, 4K)
            window_height = int(screen_height * 0.55)
            self.compact_mode = False
        
        # Width is always proportional
        window_width = int(window_height * 0.85)  # Aspect ratio
        
        # Enforce limits
        window_width = max(400, min(window_width, 550))
        window_height = max(500, min(window_height, 650))
        
        # Store dimensions
        self.window_width = window_width
        self.window_height = window_height
        
        # Calculate component sizes proportionally
        self._calculate_component_sizes()
        
        # Apply geometry
        self.geometry(f"{window_width}x{window_height}")
        self.minsize(400, 500)
        self.maxsize(600, 700)
        
        print(f"🖥️  Screen: {screen_width}x{screen_height}")
        print(f"🪟  Login: {window_width}x{window_height}")
    
    def _calculate_component_sizes(self):
        """Calculate all component sizes based on window dimensions"""
        h = self.window_height
        
        # Proportional sizes based on window height
        self.header_font_size = max(18, int(h * 0.038))  # ~3.8% of height
        self.subtitle_font_size = max(10, int(h * 0.019))  # ~1.9% of height
        self.label_font_size = max(11, int(h * 0.021))  # ~2.1% of height
        self.input_height = max(30, int(h * 0.058))  # ~5.8% of height
        self.button_height = max(36, int(h * 0.065))  # ~6.5% of height
        self.padding_large = max(12, int(h * 0.025))  # ~2.5% of height
        self.padding_medium = max(8, int(h * 0.015))  # ~1.5% of height
        self.padding_small = max(5, int(h * 0.010))  # ~1.0% of height
        
        print(f"📏 Component sizes calculated for {h}px height")
    
    def _center_on_current_monitor(self):
        """Center window on current monitor"""
        self.update_idletasks()
        
        width = self.winfo_width()
        height = self.winfo_height()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        
        x = max(0, (screen_width - width) // 2)
        y = max(0, (screen_height - height) // 2)
        
        self.geometry(f'{width}x{height}+{x}+{y}')
    
    def _setup_ui(self):
        """Setup UI with proportional sizing"""
        
        # Main container (NOT scrollable - fits exactly)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.grid(row=0, column=0, sticky="nsew", 
                            padx=self.padding_large, 
                            pady=self.padding_large)
        self.main_frame.grid_columnconfigure(0, weight=1)
        
        # Configure rows with proportional weights
        total_weight = 100
        self.main_frame.grid_rowconfigure(0, weight=8)   # Header
        self.main_frame.grid_rowconfigure(1, weight=5)   # Subtitle
        self.main_frame.grid_rowconfigure(2, weight=35)  # Environment frame
        self.main_frame.grid_rowconfigure(3, weight=35)  # Credentials frame
        self.main_frame.grid_rowconfigure(4, weight=10)  # Login button
        self.main_frame.grid_rowconfigure(5, weight=7)   # Status
        
        row = 0
        
        # ===== HEADER =====
        self.header_label = ctk.CTkLabel(
            self.main_frame,
            text="🔐 Salesforce Login",
            font=ctk.CTkFont(size=self.header_font_size, weight="bold")
        )
        self.header_label.grid(row=row, column=0, sticky="ew")
        row += 1
        
        self.subtitle_label = ctk.CTkLabel(
            self.main_frame,
            text="Enter your Salesforce credentials",
            font=ctk.CTkFont(size=self.subtitle_font_size),
            text_color="gray"
        )
        self.subtitle_label.grid(row=row, column=0, sticky="ew")
        row += 1
        
        # ===== ENVIRONMENT FRAME =====
        self.env_frame = ctk.CTkFrame(self.main_frame)
        self.env_frame.grid(row=row, column=0, sticky="nsew", pady=(self.padding_medium, 0))
        self.env_frame.grid_columnconfigure(0, weight=1)
        self.env_frame.grid_rowconfigure(1, weight=1)
        self.env_frame.grid_rowconfigure(3, weight=1)
        row += 1
        
        ctk.CTkLabel(
            self.env_frame,
            text="Environment:",
            font=ctk.CTkFont(size=self.label_font_size, weight="bold"),
            anchor="w"
        ).grid(row=0, column=0, padx=self.padding_large, 
               pady=(self.padding_medium, self.padding_small), sticky="w")
        
        # Environment dropdown
        self.env_var = ctk.StringVar(value="Production")
        self.env_dropdown = ctk.CTkOptionMenu(
            self.env_frame,
            variable=self.env_var,
            values=["Production", "Sandbox"],
            height=self.input_height
        )
        self.env_dropdown.grid(row=1, column=0, sticky="ew", 
                              padx=self.padding_large, pady=self.padding_small)
        
        # Custom domain checkbox
        self.custom_domain_var = ctk.BooleanVar(value=False)
        self.custom_domain_check = ctk.CTkCheckBox(
            self.env_frame,
            text="Use Custom Domain",
            variable=self.custom_domain_var,
            command=self._on_custom_domain_toggle,
            font=ctk.CTkFont(size=self.subtitle_font_size)
        )
        self.custom_domain_check.grid(row=2, column=0, padx=self.padding_large, 
                                     pady=self.padding_small, sticky="w")
        
        # Custom domain entry
        self.custom_domain_entry = ctk.CTkEntry(
            self.env_frame,
            placeholder_text="mycompany.my.salesforce.com",
            state="disabled",
            height=self.input_height
        )
        self.custom_domain_entry.grid(row=3, column=0, sticky="ew", 
                                     padx=self.padding_large, 
                                     pady=(self.padding_small, self.padding_medium))
        
        # ===== CREDENTIALS FRAME =====
        self.cred_frame = ctk.CTkFrame(self.main_frame)
        self.cred_frame.grid(row=row, column=0, sticky="nsew", pady=(self.padding_medium, 0))
        self.cred_frame.grid_columnconfigure(0, weight=1)
        self.cred_frame.grid_rowconfigure(1, weight=1)
        self.cred_frame.grid_rowconfigure(2, weight=1)
        self.cred_frame.grid_rowconfigure(3, weight=1)
        row += 1
        
        ctk.CTkLabel(
            self.cred_frame,
            text="Credentials:",
            font=ctk.CTkFont(size=self.label_font_size, weight="bold"),
            anchor="w"
        ).grid(row=0, column=0, padx=self.padding_large, 
               pady=(self.padding_medium, self.padding_small), sticky="w")
        
        # Username
        self.username_entry = ctk.CTkEntry(
            self.cred_frame,
            placeholder_text="your.email@company.com",
            height=self.input_height
        )
        self.username_entry.grid(row=1, column=0, sticky="ew", 
                                padx=self.padding_large, pady=self.padding_small)
        
        # Password
        self.password_entry = ctk.CTkEntry(
            self.cred_frame,
            placeholder_text="Password",
            show="●",
            height=self.input_height
        )
        self.password_entry.grid(row=2, column=0, sticky="ew", 
                                padx=self.padding_large, pady=self.padding_small)
        
        # Security Token
        self.token_entry = ctk.CTkEntry(
            self.cred_frame,
            placeholder_text="Security Token (optional)",
            show="●",
            height=self.input_height
        )
        self.token_entry.grid(row=3, column=0, sticky="ew", 
                             padx=self.padding_large, pady=self.padding_small)
        
        # Token info
        ctk.CTkLabel(
            self.cred_frame,
            text="💡 Leave blank if IP whitelisted",
            font=ctk.CTkFont(size=max(9, self.subtitle_font_size - 1)),
            text_color="gray",
            anchor="w"
        ).grid(row=4, column=0, padx=self.padding_large, 
               pady=(self.padding_small, self.padding_medium), sticky="w")
        
        # ===== LOGIN BUTTON =====
        self.login_button = ctk.CTkButton(
            self.main_frame,
            text="Login to Salesforce",
            command=self._on_login_click,
            height=self.button_height,
            font=ctk.CTkFont(size=self.label_font_size + 2, weight="bold")
        )
        self.login_button.grid(row=row, column=0, sticky="ew", 
                              pady=(self.padding_medium, self.padding_small))
        row += 1
        
        # ===== STATUS LABEL =====
        self.status_label = ctk.CTkLabel(
            self.main_frame,
            text="",
            font=ctk.CTkFont(size=self.subtitle_font_size),
            text_color="gray",
            wraplength=self.window_width - 40,
            justify="center"
        )
        self.status_label.grid(row=row, column=0, sticky="ew")
        
        # Bindings
        self.bind('<Return>', lambda e: self._on_login_click())
        self.username_entry.focus()
    
    def _on_custom_domain_toggle(self):
        """Toggle custom domain entry"""
        if self.custom_domain_var.get():
            self.custom_domain_entry.configure(state="normal")
            self.env_dropdown.configure(state="disabled")
        else:
            self.custom_domain_entry.configure(state="disabled")
            self.env_dropdown.configure(state="normal")
    
    def _on_login_click(self):
        """Handle login"""
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        token = self.token_entry.get()
        
        if not username:
            self._show_status("❌ Please enter username", "red")
            self.username_entry.focus()
            return
        
        if not password:
            self._show_status("❌ Please enter password", "red")
            self.password_entry.focus()
            return
        
        if self.custom_domain_var.get():
            domain = self.custom_domain_entry.get().strip()
            if not domain:
                self._show_status("❌ Please enter custom domain", "red")
                self.custom_domain_entry.focus()
                return
        else:
            domain = "login" if self.env_var.get() == "Production" else "test"
        
        self._set_ui_enabled(False)
        self._show_status("🔄 Connecting...", "gray")
        
        thread = threading.Thread(
            target=self._login_worker,
            args=(username, password, token, domain),
            daemon=True
        )
        thread.start()
    
    def _login_worker(self, username: str, password: str, token: str, domain: str):
        """Background login"""
        try:
            auth = SalesforceAuth()
            result = auth.login(username, password, token, domain)
            self.after(0, self._on_login_success_callback, result)
        except SalesforceAuthError as e:
            self.after(0, self._on_login_error_callback, str(e))
        except Exception as e:
            self.after(0, self._on_login_error_callback, f"Error: {str(e)}")
    
    def _on_login_success_callback(self, session_info: dict):
        """Login success"""
        self.session_info = session_info
        instance = session_info.get("instance_url", "").replace('https://', '')
        api_version = session_info.get("api_version", "")
        
        msg = f"✅ Connected to {instance}"
        if api_version:
            msg += f" (v{api_version})"
        
        self._show_status(msg, "green")
        
        if self.on_login_success:
            self.on_login_success(session_info)
        
        self.after(1000, self.destroy)
    
    def _on_login_error_callback(self, error_msg: str):
        """Login error"""
        self._show_status(f"❌ {error_msg}", "red")
        self._set_ui_enabled(True)
    
    def _show_status(self, message: str, color: str = "gray"):
        """Update status"""
        self.status_label.configure(text=message, text_color=color)
    
    def _set_ui_enabled(self, enabled: bool):
        """Enable/disable UI"""
        state = "normal" if enabled else "disabled"
        self.username_entry.configure(state=state)
        self.password_entry.configure(state=state)
        self.token_entry.configure(state=state)
        self.login_button.configure(state=state)
        
        if not self.custom_domain_var.get():
            self.env_dropdown.configure(state=state)
        if self.custom_domain_var.get():
            self.custom_domain_entry.configure(state=state)