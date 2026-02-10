import customtkinter as ctk
import sys
import os

# Ensure we can import from local packages
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ui.main_window import MainWindow

def main():
    ctk.set_appearance_mode("System")  # Modes: "System" (standard), "Dark", "Light"
    ctk.set_default_color_theme("green")  # Themes: "blue" (standard), "green", "dark-blue"

    app = MainWindow()
    app.mainloop()

if __name__ == "__main__":
    main()
