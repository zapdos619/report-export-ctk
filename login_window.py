# login_window.py - FIXED VERSION (Part 1)
# Login window that appears FIRST when app starts

import customtkinter as ctk
import threading
from typing import Optional, Callable
from salesforce_auth import SalesforceAuth, SalesforceAuthError


class LoginWindow(ctk.CTkToplevel):  # ← CHANGED: Was CTk, now CTkToplevel
    """
    Login window shown as Toplevel.
    
    KEY FIX: Now a Toplevel window instead of standalone root window.
    This allows it to exist within a parent event loop.
    """
    
    def __init__(
        self, 
        master,  # ← NEW: Required master parameter
        on_login_success: Callable,
        on_login_cancelled: Optional[Callable] = None,
        *args, 
        **kwargs
    ):
        # ← CHANGED: Pass master to Toplevel
        super().__init__(master, *args, **kwargs)
        
        self.on_login_success = on_login_success
        self.on_login_cancelled = on_login_cancelled
        self.session_info = None
        
        # Initial setup
        self.title("Salesforce Login")
        
        # ← NEW: Make this window modal-like (grab focus)
        self.grab_set()
        
        # Hide initially to calculate size
        self.withdraw()
        self.update_idletasks()
        
        # Calculate size for current monitor
        self._calculate_responsive_size()
        
        # Setup UI with calculated sizes
        self._setup_ui()
        
        # Show and center
        self.deiconify()
        self.after(50, self._center_on_current_monitor)
        
        # Handle window close event
        self.protocol("WM_DELETE_WINDOW", self._on_window_close)
    
    def _calculate_responsive_size(self):
        """Calculate responsive window and component sizes"""
        self.update_idletasks()
        
        # Get current monitor dimensions
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        
        # Determine window size based on screen height
        if screen_height <= 768:
            window_height = int(screen_height * 0.75)
            self.compact_mode = True
        elif screen_height <= 900:
            window_height = int(screen_height * 0.70)
            self.compact_mode = True
        elif screen_height <= 1080:
            window_height = int(screen_height * 0.62)
            self.compact_mode = False
        else:
            window_height = int(screen_height * 0.55)
            self.compact_mode = False
        
        window_width = int(window_height * 0.85)
        
        window_width = max(400, min(window_width, 550))
        window_height = max(500, min(window_height, 650))
        
        self.window_width = window_width
        self.window_height = window_height
        
        self._calculate_component_sizes()
        
        self.geometry(f"{window_width}x{window_height}")
        self.minsize(400, 500)
        self.maxsize(600, 700)
    
    def _calculate_component_sizes(self):
        """Calculate all component sizes based on window dimensions"""
        h = self.window_height
        
        self.header_font_size = max(18, int(h * 0.038))
        self.subtitle_font_size = max(10, int(h * 0.019))
        self.label_font_size = max(11, int(h * 0.021))
        self.input_height = max(30, int(h * 0.058))
        self.button_height = max(36, int(h * 0.065))
        self.padding_large = max(12, int(h * 0.025))
        self.padding_medium = max(8, int(h * 0.015))
        self.padding_small = max(5, int(h * 0.010))
    
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
    
    # Continue LoginWindow class...
    
    def _setup_ui(self):
        """Setup UI with proportional sizing"""
        
        # Main container
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.grid(row=0, column=0, sticky="nsew", 
                            padx=self.padding_large, 
                            pady=self.padding_large)
        self.main_frame.grid_columnconfigure(0, weight=1)
        
        # Configure rows with proportional weights
        self.main_frame.grid_rowconfigure(0, weight=8)
        self.main_frame.grid_rowconfigure(1, weight=5)
        self.main_frame.grid_rowconfigure(2, weight=35)
        self.main_frame.grid_rowconfigure(3, weight=35)
        self.main_frame.grid_rowconfigure(4, weight=10)
        self.main_frame.grid_rowconfigure(5, weight=7)
        
        row = 0
        
        # HEADER
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
        
        # ENVIRONMENT FRAME
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
        
        self.env_var = ctk.StringVar(value="Production")
        self.env_dropdown = ctk.CTkOptionMenu(
            self.env_frame,
            variable=self.env_var,
            values=["Production", "Sandbox"],
            height=self.input_height
        )
        self.env_dropdown.grid(row=1, column=0, sticky="ew", 
                              padx=self.padding_large, pady=self.padding_small)
        
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
        
        self.custom_domain_entry = ctk.CTkEntry(
            self.env_frame,
            placeholder_text="mycompany.my.salesforce.com",
            state="disabled",
            height=self.input_height
        )
        self.custom_domain_entry.grid(row=3, column=0, sticky="ew", 
                                     padx=self.padding_large, 
                                     pady=(self.padding_small, self.padding_medium))
        
        # CREDENTIALS FRAME
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
        
        self.username_entry = ctk.CTkEntry(
            self.cred_frame,
            placeholder_text="your.email@company.com",
            height=self.input_height
        )
        self.username_entry.grid(row=1, column=0, sticky="ew", 
                                padx=self.padding_large, pady=self.padding_small)
        
        self.password_entry = ctk.CTkEntry(
            self.cred_frame,
            placeholder_text="Password",
            show="●",
            height=self.input_height
        )
        self.password_entry.grid(row=2, column=0, sticky="ew", 
                                padx=self.padding_large, pady=self.padding_small)
        
        self.token_entry = ctk.CTkEntry(
            self.cred_frame,
            placeholder_text="Security Token (optional)",
            show="●",
            height=self.input_height
        )
        self.token_entry.grid(row=3, column=0, sticky="ew", 
                             padx=self.padding_large, pady=self.padding_small)
        
        ctk.CTkLabel(
            self.cred_frame,
            text="💡 Leave blank if IP whitelisted",
            font=ctk.CTkFont(size=max(9, self.subtitle_font_size - 1)),
            text_color="gray",
            anchor="w"
        ).grid(row=4, column=0, padx=self.padding_large, 
               pady=(self.padding_small, self.padding_medium), sticky="w")
        
        # LOGIN BUTTON
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
        
        # STATUS LABEL
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
    
    # Continue LoginWindow class...
    
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
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        token = self.token_entry.get()
        
        # Validation
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
        """
        Background worker for login.
        
        KEY FIX: Uses self.after() to safely update UI from thread.
        """
        try:
            auth = SalesforceAuth()
            result = auth.login(username, password, token, domain)
            
            # Schedule UI update on main thread
            self.after(0, lambda: self._on_login_success_callback(result))
            
        except SalesforceAuthError as e:
            # Schedule error UI update on main thread
            self.after(0, lambda: self._on_login_error_callback(str(e)))
            
        except Exception as e:
            # Schedule generic error UI update on main thread
            self.after(0, lambda: self._on_login_error_callback(f"Error: {str(e)}"))
    
    def _on_login_success_callback(self, session_info: dict):
        """
        Handle successful login.
        
        KEY FIX: No more race conditions or delays before callback.
        Immediately triggers parent callback which handles window destruction.
        """
        self.session_info = session_info
        
        # Show success message
        instance = session_info.get("instance_url", "").replace('https://', '')
        api_version = session_info.get("api_version", "")
        
        msg = f"✅ Connected to {instance}"
        if api_version:
            msg += f" (v{api_version})"
        
        self._show_status(msg, "green")
        
        # ← KEY FIX: Call parent callback immediately (no delay!)
        # The parent (AppLauncher) is responsible for destroying this window
        if self.on_login_success:
            # Small delay just for user to see success message
            self.after(500, lambda: self._trigger_success_callback())
    
    def _trigger_success_callback(self):
        """
        Trigger the success callback.
        
        KEY FIX: Separated into own method to ensure callback fires
        even if window is being destroyed.
        """
        if self.on_login_success and self.session_info:
            try:
                # Release grab before callback (allows parent to take control)
                self.grab_release()
                
                # Call parent callback
                self.on_login_success(self.session_info)
                
                # Note: Parent is responsible for destroying this window
                # Don't call self.destroy() here!
                
            except Exception as e:
                print(f"⚠️ Error in login success callback: {e}")
    
    def _on_login_error_callback(self, error_msg: str):
        """
        Handle login error.
        
        KEY FIX: Re-enables UI immediately without delays.
        """
        self._show_status(f"❌ {error_msg}", "red")
        self._set_ui_enabled(True)
    
    def _show_status(self, message: str, color: str = "gray"):
        """Update status label"""
        try:
            self.status_label.configure(text=message, text_color=color)
        except:
            pass  # Widget might be destroyed
    
    def _set_ui_enabled(self, enabled: bool):
        """Enable/disable UI elements"""
        state = "normal" if enabled else "disabled"
        
        try:
            self.username_entry.configure(state=state)
            self.password_entry.configure(state=state)
            self.token_entry.configure(state=state)
            self.login_button.configure(state=state)
            
            if not self.custom_domain_var.get():
                self.env_dropdown.configure(state=state)
            if self.custom_domain_var.get():
                self.custom_domain_entry.configure(state=state)
        except:
            pass  # Widgets might be destroyed
    
    def _on_window_close(self):
        """
        Handle window close button (X).
        
        KEY FIX: Properly releases grab and calls cancellation callback.
        """
        # Release grab
        try:
            self.grab_release()
        except:
            pass
        
        # Call cancellation callback if provided
        if self.on_login_cancelled:
            try:
                self.on_login_cancelled()
            except Exception as e:
                print(f"⚠️ Error in cancellation callback: {e}")
        else:
            # Default: just destroy this window
            try:
                self.destroy()
            except:
                pass
    