import customtkinter as ctk
import sys
import os

# Ensure we can import from local packages
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ui.main_window import MainWindow
from core.license_manager import LicenseManager
from ui.license_window import LicenseWindow

def main():
    ctk.set_appearance_mode("System")  # Modes: "System" (standard), "Dark", "Light"
    ctk.set_default_color_theme("green")  # Themes: "blue" (standard), "green", "dark-blue"

    license_manager = LicenseManager()

    def launch_main():
        app = MainWindow()
        app.mainloop()

    # Check if a valid, active local license exists
    if license_manager.verify_local_license():
        launch_main()
    else:
        # Otherwise, open the license key popup
        activation_app = LicenseWindow(license_manager, launch_main)
        activation_app.mainloop()

if __name__ == "__main__":
    main()

