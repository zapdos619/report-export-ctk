# login_window.py - UPDATED VERSION
# Salesforce Login Window using CustomTkinter
# Changes: Increased height to 580px, better padding, improved centering

import customtkinter as ctk
import threading
from typing import Optional, Callable
from salesforce_auth import SalesforceAuth, SalesforceAuthError


class LoginWindow(ctk.CTkToplevel):
    """
    Separate login window for Salesforce authentication.
    Supports Production, Sandbox, and Custom Domain login.
    """
    
    def __init__(self, parent, on_login_success: Callable, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        
        self.on_login_success = on_login_success
        self.session_info = None
        
        # Window setup - INCREASED HEIGHT
        self.title("Salesforce Login")
        self.geometry("500x580")
        self.resizable(False, False)
        
        # Center the window
        self.after(100, self._center_window)
        
        # Make it modal
        self.transient(parent)
        self.grab_set()
        
        self._setup_ui()
        
    def _center_window(self):
        """Center the window on screen"""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')
    
    def _setup_ui(self):
        """Setup the login UI"""
        
        # Main container with MORE PADDING
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=25, pady=25)
        
        # Header
        header_label = ctk.CTkLabel(
            main_frame,
            text="🔐 Salesforce Login",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        header_label.pack(pady=(0, 10))
        
        subtitle_label = ctk.CTkLabel(
            main_frame,
            text="Enter your Salesforce credentials",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        subtitle_label.pack(pady=(0, 25))
        
        # Environment selection frame - IMPROVED SPACING
        env_frame = ctk.CTkFrame(main_frame)
        env_frame.pack(fill="x", pady=(0, 20))
        
        env_label = ctk.CTkLabel(
            env_frame,
            text="Environment:",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        env_label.pack(anchor="w", padx=15, pady=(15, 8))
        
        # Environment dropdown
        self.env_var = ctk.StringVar(value="Production")
        self.env_dropdown = ctk.CTkOptionMenu(
            env_frame,
            variable=self.env_var,
            values=["Production", "Sandbox"],
            command=self._on_env_change
        )
        self.env_dropdown.pack(fill="x", padx=15, pady=(0, 12))
        
        # Custom domain checkbox
        self.custom_domain_var = ctk.BooleanVar(value=False)
        self.custom_domain_check = ctk.CTkCheckBox(
            env_frame,
            text="Use Custom Domain",
            variable=self.custom_domain_var,
            command=self._on_custom_domain_toggle
        )
        self.custom_domain_check.pack(anchor="w", padx=15, pady=(0, 8))
        
        # Custom domain entry
        self.custom_domain_entry = ctk.CTkEntry(
            env_frame,
            placeholder_text="mycompany.my.salesforce.com",
            state="disabled"
        )
        self.custom_domain_entry.pack(fill="x", padx=15, pady=(0, 15))
        
        # Credentials frame - IMPROVED SPACING
        cred_frame = ctk.CTkFrame(main_frame)
        cred_frame.pack(fill="x", pady=(0, 20))
        
        cred_label = ctk.CTkLabel(
            cred_frame,
            text="Credentials:",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        cred_label.pack(anchor="w", padx=15, pady=(15, 8))
        
        # Username
        self.username_entry = ctk.CTkEntry(
            cred_frame,
            placeholder_text="your.email@company.com",
            height=35
        )
        self.username_entry.pack(fill="x", padx=15, pady=(5, 12))
        
        # Password
        self.password_entry = ctk.CTkEntry(
            cred_frame,
            placeholder_text="Password",
            show="●",
            height=35
        )
        self.password_entry.pack(fill="x", padx=15, pady=(0, 12))
        
        # Security Token
        self.token_entry = ctk.CTkEntry(
            cred_frame,
            placeholder_text="Security Token (optional if IP whitelisted)",
            show="●",
            height=35
        )
        self.token_entry.pack(fill="x", padx=15, pady=(0, 12))
        
        # Token info label
        token_info = ctk.CTkLabel(
            cred_frame,
            text="💡 Leave token blank if your IP is whitelisted",
            font=ctk.CTkFont(size=10),
            text_color="gray"
        )
        token_info.pack(anchor="w", padx=15, pady=(0, 15))
        
        # Login button - SLIGHTLY TALLER
        self.login_button = ctk.CTkButton(
            main_frame,
            text="Login to Salesforce",
            command=self._on_login_click,
            height=42,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.login_button.pack(fill="x", pady=(0, 12))
        
        # Status label - MORE SPACE
        self.status_label = ctk.CTkLabel(
            main_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="gray",
            wraplength=450
        )
        self.status_label.pack(pady=(5, 0))
        
        # Bind Enter key to login
        self.bind('<Return>', lambda e: self._on_login_click())
        
    def _on_env_change(self, choice):
        """Handle environment dropdown change"""
        pass
    
    def _on_custom_domain_toggle(self):
        """Toggle custom domain entry"""
        if self.custom_domain_var.get():
            self.custom_domain_entry.configure(state="normal")
            self.env_dropdown.configure(state="disabled")
        else:
            self.custom_domain_entry.configure(state="disabled")
            self.env_dropdown.configure(state="normal")
    
    def _on_login_click(self):
        """Handle login button click"""
        # Validate inputs
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
        
        # Determine domain
        if self.custom_domain_var.get():
            domain = self.custom_domain_entry.get().strip()
            if not domain:
                self._show_status("❌ Please enter custom domain", "red")
                self.custom_domain_entry.focus()
                return
        else:
            env = self.env_var.get()
            domain = "login" if env == "Production" else "test"
        
        # Disable UI during login
        self._set_ui_enabled(False)
        self._show_status("🔄 Connecting to Salesforce...", "gray")
        
        # Start login in background thread
        thread = threading.Thread(
            target=self._login_worker,
            args=(username, password, token, domain),
            daemon=True
        )
        thread.start()
    
    def _login_worker(self, username: str, password: str, token: str, domain: str):
        """Background worker for login"""
        try:
            auth = SalesforceAuth()
            result = auth.login(username, password, token, domain)
            
            # Update UI on main thread
            self.after(0, self._on_login_success_callback, result)
            
        except SalesforceAuthError as e:
            self.after(0, self._on_login_error_callback, str(e))
        except Exception as e:
            self.after(0, self._on_login_error_callback, f"Unexpected error: {str(e)}")
    
    def _on_login_success_callback(self, session_info: dict):
        """Called when login succeeds"""
        self.session_info = session_info
        
        instance = session_info.get("instance_url", "")
        api_version = session_info.get("api_version", "")
        
        status_msg = f"✅ Connected to {instance.replace('https://', '')}"
        if api_version:
            status_msg += f" (API v{api_version})"
        
        self._show_status(status_msg, "green")
        
        # Call the parent's success callback
        if self.on_login_success:
            self.on_login_success(session_info)
        
        # Close this window after 1 second
        self.after(1000, self.destroy)
    
    def _on_login_error_callback(self, error_msg: str):
        """Called when login fails"""
        self._show_status(f"❌ Login failed: {error_msg}", "red")
        self._set_ui_enabled(True)
    
    def _show_status(self, message: str, color: str = "gray"):
        """Update status label"""
        self.status_label.configure(text=message, text_color=color)
    
    def _set_ui_enabled(self, enabled: bool):
        """Enable/disable UI elements"""
        state = "normal" if enabled else "disabled"
        
        self.username_entry.configure(state=state)
        self.password_entry.configure(state=state)
        self.token_entry.configure(state=state)
        self.login_button.configure(state=state)
        
        if not self.custom_domain_var.get():
            self.env_dropdown.configure(state=state)
        
        if self.custom_domain_var.get():
            self.custom_domain_entry.configure(state=state)