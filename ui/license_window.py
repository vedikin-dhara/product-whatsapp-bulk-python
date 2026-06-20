import customtkinter as ctk
import sys
import os
from core.license_manager import LicenseManager

class LicenseWindow(ctk.CTk):
    def __init__(self, license_manager: LicenseManager, on_success_callback):
        super().__init__()
        
        self.license_manager = license_manager
        self.on_success_callback = on_success_callback
        
        # Window Configuration
        self.title("WASender - Activation")
        self.geometry("480x340")
        self.resizable(False, False)
        
        # Center the window on screen
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
        
        # Appearance configuration
        ctk.set_appearance_mode("Light")
        ctk.set_default_color_theme("green")
        
        # Bind close event
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Build UI Elements
        self.create_widgets()
        
        # Check initial database connection
        self.check_database_connection()

    def create_widgets(self):
        # Background and layout
        self.configure(fg_color="white")
        
        # Main Frame with padding
        self.main_frame = ctk.CTkFrame(self, fg_color="white", corner_radius=0)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # 1. Header Emoji and Title
        self.header_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.header_frame.pack(fill="x", pady=(10, 15))
        
        self.icon_label = ctk.CTkLabel(
            self.header_frame, 
            text="🔑", 
            font=("Arial", 36)
        )
        self.icon_label.pack()
        
        self.title_label = ctk.CTkLabel(
            self.header_frame, 
            text="License Key", 
            font=("Arial", 22, "bold"), 
            text_color="#2E7D32" # Dark green
        )
        self.title_label.pack(pady=(5, 0))
        
        self.subtitle_label = ctk.CTkLabel(
            self.header_frame, 
            text="Please enter your unique license key to activate the software.", 
            font=("Arial", 12), 
            text_color="gray"
        )
        self.subtitle_label.pack(pady=(5, 0))

        # 2. Input Frame
        self.input_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.input_frame.pack(fill="x", pady=10)
        
        self.key_entry = ctk.CTkEntry(
            self.input_frame, 
            placeholder_text="WAS-XXXX-XXXX-XXXX-XXXX", 
            font=("Consolas", 14),
            height=40,
            justify="center",
            border_color="#4CAF50",
            fg_color="#F1F8E9",
            text_color="black"
        )
        self.key_entry.pack(fill="x", padx=20)
        self.key_entry.bind("<Return>", lambda event: self.handle_activation())

        # 3. Status Label
        self.status_label = ctk.CTkLabel(
            self.main_frame, 
            text="", 
            font=("Arial", 12, "bold"),
            text_color="red",
            wraplength=400
        )
        self.status_label.pack(pady=5)

        # 4. Buttons Frame
        self.button_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.button_frame.pack(fill="x", pady=(10, 0))
        
        self.activate_btn = ctk.CTkButton(
            self.button_frame, 
            text="Activate Software", 
            font=("Arial", 13, "bold"),
            height=40,
            fg_color="#4CAF50",
            hover_color="#388E3C",
            text_color="white",
            command=self.handle_activation
        )
        self.activate_btn.pack(side="left", fill="x", expand=True, padx=(20, 5))
        
        # Retry connection button (hidden by default)
        self.retry_btn = ctk.CTkButton(
            self.button_frame,
            text="🔄 Reconnect DB",
            font=("Arial", 13, "bold"),
            height=40,
            fg_color="#757575",
            hover_color="#616161",
            text_color="white",
            command=self.retry_db_connection
        )
        # We only pack this button when database connection is down

    def check_database_connection(self):
        """
        Verifies if local MySQL server is running and reachable.
        If offline, disables UI elements and prompts user to start MySQL.
        """
        if not self.license_manager.is_connected():
            # Try to initialize again in case it was off during startup
            self.license_manager._init_db()
            
        if not self.license_manager.is_connected():
            self.key_entry.configure(state="disabled")
            self.activate_btn.configure(state="disabled")
            self.status_label.configure(
                text="❌ Local MySQL server is offline.\nPlease make sure WampServer / XAMPP MySQL is running.",
                text_color="#D32F2F"
            )
            # Display retry button
            if not self.retry_btn.winfo_ismapped():
                self.retry_btn.pack(side="right", padx=(5, 20))
            return False
        else:
            self.key_entry.configure(state="normal")
            self.activate_btn.configure(state="normal")
            self.status_label.configure(text="")
            if self.retry_btn.winfo_ismapped():
                self.retry_btn.pack_forget()
            return True

    def retry_db_connection(self):
        """
        Clears status and recheck database connection.
        """
        self.status_label.configure(text="Connecting to database...", text_color="blue")
        self.update()
        if self.check_database_connection():
            self.status_label.configure(text="✅ Database connected successfully!", text_color="#388E3C")

    def handle_activation(self):
        # Avoid duplicate submission if DB is offline
        if not self.check_database_connection():
            return
            
        license_key = self.key_entry.get().strip()
        
        if not license_key:
            self.status_label.configure(text="Please enter a license key.", text_color="red")
            return
            
        self.status_label.configure(text="Validating license...", text_color="#1976D2")
        self.update()
        
        success, message = self.license_manager.activate_license(license_key)
        
        if success:
            self.status_label.configure(text=f"✅ {message}", text_color="#388E3C")
            self.update()
            # Wait 1.5 seconds so user can see success checkmark
            self.after(1500, self.complete_activation)
        else:
            self.status_label.configure(text=f"❌ {message}", text_color="#D32F2F")

    def complete_activation(self):
        # Open WASender (MainWindow) and close LicenseWindow
        self.destroy()
        self.on_success_callback()

    def on_close(self):
        # Force exit python application if user closes the license activation popup
        sys.exit(0)
