import customtkinter as ctk
from tkinter import filedialog, messagebox, Scrollbar
import tkinter
import threading
import pandas as pd
import os
import sys

# Add parent directory to path to allow importing core modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.campaign_manager import CampaignManager
from core.validator import validate_number

class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window Configuration
        self.title("WASender")
        self.geometry("1200x800")
        
        # Determine theme - trying to match green/white aesthetic
        ctk.set_appearance_mode("Light") 
        ctk.set_default_color_theme("green")

        # Core Components
        self.campaign_manager = CampaignManager(self.update_status_callback)
        self.loaded_numbers = [] # List of dicts {Number, Name}
        self.attachments = [] # List of dicts: {'path': str, 'type': 'auto'|'custom'|'none', 'text': str}

        # Layout Grid Configuration
        self.grid_columnconfigure(1, weight=1) # Main content expands
        self.grid_rowconfigure(1, weight=1)    # Main content vertically expands

        # 1. Top Bar
        self.create_top_bar()

        # 2. Sidebar (Icons)
        self.create_sidebar()

        # 3. Main Content Area (Split into Left Target Panel and Right Message Panel)
        self.create_main_content()

        # 4. Bottom Footer (Delay Settings & Start)
        self.create_footer()

    def create_top_bar(self):
        self.top_bar = ctk.CTkFrame(self, height=50, corner_radius=0, fg_color="#4CAF50") # Material Green
        self.top_bar.grid(row=0, column=0, columnspan=2, sticky="ew")
        
        # Hamburger Menu & Title
        self.menu_btn = ctk.CTkButton(self.top_bar, text="☰", width=40, fg_color="transparent", font=("Arial", 20))
        self.menu_btn.pack(side="left", padx=10)
        
        self.logo_label = ctk.CTkLabel(self.top_bar, text="WASender", font=("Arial", 20, "bold"), text_color="white")
        self.logo_label.pack(side="left", padx=10)

        # Right side icons placeholders
        self.version_label = ctk.CTkLabel(self.top_bar, text="3.5.0", text_color="white", fg_color="#388E3C", corner_radius=5)
        self.version_label.pack(side="right", padx=10)
        
        self.lang_option = ctk.CTkOptionMenu(self.top_bar, values=["English"], width=100)
        self.lang_option.pack(side="right", padx=10)

        self.tools_icon = ctk.CTkButton(self.top_bar, text="🛠", width=30, fg_color="transparent", text_color="white")
        self.tools_icon.pack(side="right", padx=5)
        
        self.acct_btn = ctk.CTkButton(self.top_bar, text="💬 ACCOUNTS", fg_color="transparent", text_color="white", command=self.load_browser_event)
        self.acct_btn.pack(side="right", padx=5)

    def create_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=60, corner_radius=0, fg_color="white")
        self.sidebar.grid(row=1, column=0, sticky="ns")
        
        # Sidebar Icons (User, Group, Tools)
        # Using simple emoji/text as placeholders for icons
        self.sb_btn1 = ctk.CTkButton(self.sidebar, text="👤", width=40, fg_color="#E8F5E9", text_color="green", font=("Arial", 20))
        self.sb_btn1.pack(pady=10, padx=5)
        
        self.sb_btn2 = ctk.CTkButton(self.sidebar, text="👥", width=40, fg_color="transparent", text_color="gray", font=("Arial", 20))
        self.sb_btn2.pack(pady=10, padx=5)
        
        self.sb_btn3 = ctk.CTkButton(self.sidebar, text="🛠", width=40, fg_color="transparent", text_color="gray", font=("Arial", 20))
        self.sb_btn3.pack(pady=10, padx=5)

    def create_main_content(self):
        self.main_content = ctk.CTkFrame(self, fg_color="#F5F5F5", corner_radius=0)
        self.main_content.grid(row=1, column=1, sticky="nsew")
        self.main_content.grid_columnconfigure(0, weight=1) # Target panel
        self.main_content.grid_columnconfigure(1, weight=2) # Message panel
        self.main_content.grid_rowconfigure(0, weight=1)

        # --- Left Panel: Target ---
        self.create_target_panel()

        # --- Right Panel: Message ---
        self.create_message_panel()

    def create_target_panel(self):
        self.target_frame = ctk.CTkFrame(self.main_content, fg_color="white")
        self.target_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.target_frame.grid_rowconfigure(3, weight=1) # Table expands
        self.target_frame.grid_columnconfigure(0, weight=1)

        # Header
        header_frame = ctk.CTkFrame(self.target_frame, fg_color="white")
        header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        
        ctk.CTkLabel(header_frame, text="Target", font=("Arial", 14, "bold")).pack(side="left")
        
        self.upload_btn = ctk.CTkButton(header_frame, text="❎ UPLOAD EXCEL", fg_color="#4CAF50", hover_color="#388E3C", width=120, command=self.import_numbers)
        self.upload_btn.pack(side="right")

        # Manual Entry Row
        entry_frame = ctk.CTkFrame(self.target_frame, fg_color="white")
        entry_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        
        self.entry_number = ctk.CTkEntry(entry_frame, placeholder_text="Number (with code)", width=140)
        self.entry_number.pack(side="left", padx=(0, 5), expand=True, fill="x")
        self.entry_number.bind("<Return>", lambda event: self.add_manual_number())
        
        self.entry_name = ctk.CTkEntry(entry_frame, placeholder_text="Name (Optional)", width=140)
        self.entry_name.pack(side="left", padx=5, expand=True, fill="x")
        self.entry_name.bind("<Return>", lambda event: self.add_manual_number())
        
        self.add_btn = ctk.CTkButton(entry_frame, text="+", width=30, fg_color="#4CAF50", command=self.add_manual_number)
        self.add_btn.pack(side="left", padx=5)

        # Table Header
        table_header = ctk.CTkFrame(self.target_frame, fg_color="#EEEEEE", height=30)
        table_header.grid(row=2, column=0, sticky="ew", padx=1, pady=1)
        ctk.CTkLabel(table_header, text="Number", width=120, anchor="w").pack(side="left", padx=10)
        ctk.CTkLabel(table_header, text="Name", width=120, anchor="w").pack(side="left", padx=10)

        # Table List (Scrollable Frame)
        self.numbers_scroll_frame = ctk.CTkScrollableFrame(self.target_frame, fg_color="white", label_text="")
        self.numbers_scroll_frame.grid(row=3, column=0, sticky="nsew", padx=1, pady=1)
        self.numbers_scroll_frame.grid_columnconfigure(0, weight=1)
        
        # Bottom Actions
        bottom_actions = ctk.CTkFrame(self.target_frame, fg_color="white")
        bottom_actions.grid(row=4, column=0, sticky="ew", padx=10, pady=10)
        
        self.download_sample_btn = ctk.CTkButton(bottom_actions, text="❎ DOWNLOAD SAMPLE EXCEL", fg_color="#4CAF50", hover_color="#388E3C", command=self.download_sample)
        self.download_sample_btn.pack(side="left")

    def create_message_panel(self):
        self.msg_frame = ctk.CTkFrame(self.main_content, fg_color="white")
        self.msg_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.msg_frame.grid_rowconfigure(1, weight=1) # Message area expands
        self.msg_frame.grid_columnconfigure(0, weight=3) # Message input
        self.msg_frame.grid_columnconfigure(1, weight=1) # Attachments

        # Tabs Header
        ctk.CTkLabel(self.msg_frame, text="Message", font=("Arial", 14, "bold")).grid(row=0, column=0, padx=10, pady=10, sticky="w")
        
        # Message Area
        self.msg_tabview = ctk.CTkTabview(self.msg_frame, fg_color="#4CAF50", segmented_button_fg_color="#4CAF50", segmented_button_selected_color="#388E3C", segmented_button_selected_hover_color="#2E7D32", segmented_button_unselected_color="#4CAF50", segmented_button_unselected_hover_color="#66BB6A", text_color="white")
        self.msg_tabview.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        
        self.msg_boxes = []
        for i in range(1, 6):
            t_name = f"Message {i}"
            self.msg_tabview.add(t_name)
            # Textbox inside tab
            tb = ctk.CTkTextbox(self.msg_tabview.tab(t_name), fg_color="#E0E0E0", text_color="black")
            tb.pack(expand=True, fill="both")
            self.msg_boxes.append(tb)

        # Attachments Sidebar (Inside Message Panel)
        att_frame = ctk.CTkFrame(self.msg_frame, fg_color="white")
        att_frame.grid(row=1, column=1, sticky="nsew", padx=5, pady=35) # Align with tabview content
        att_frame.grid_rowconfigure(2, weight=1)
        att_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(att_frame, text="Attachments", font=("Arial", 12, "bold")).grid(row=0, column=0, sticky="w", pady=5)
        self.add_file_btn = ctk.CTkButton(att_frame, text="📝 ADD FILE", fg_color="#4CAF50", hover_color="#388E3C", command=self.attach_media)
        self.add_file_btn.grid(row=1, column=0, sticky="ew", pady=5)
        
        # Attachments List Header
        att_header = ctk.CTkFrame(att_frame, fg_color="#EEEEEE", height=25)
        att_header.grid(row=2, column=0, sticky="ew")
        ctk.CTkLabel(att_header, text="File", width=100, anchor="w").pack(side="left", padx=5)
        ctk.CTkLabel(att_header, text="Caption", width=60, anchor="w").pack(side="left", padx=5)

        # Attachments List (Scrollable)
        self.att_scroll_frame = ctk.CTkScrollableFrame(att_frame, fg_color="#F5F5F5", label_text="")
        self.att_scroll_frame.grid(row=3, column=0, sticky="nsew", pady=5)
        self.att_scroll_frame.grid_columnconfigure(0, weight=1)

        # Polls & Buttons Placeholders
        extra_frame = ctk.CTkFrame(self.msg_frame, fg_color="transparent")
        extra_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=10)
        
        poll_frame = ctk.CTkFrame(extra_frame, fg_color="#F5F5F5")
        poll_frame.pack(side="left", fill="both", expand=True, padx=5)
        ctk.CTkLabel(poll_frame, text="Polls").pack(anchor="w", padx=5)
        ctk.CTkButton(poll_frame, text="+ ADD POLL", fg_color="#4CAF50", width=100).pack(pady=5)
        
        btn_frame = ctk.CTkFrame(extra_frame, fg_color="#F5F5F5")
        btn_frame.pack(side="left", fill="both", expand=True, padx=5)
        ctk.CTkLabel(btn_frame, text="Buttons").pack(anchor="w", padx=5)
        ctk.CTkButton(btn_frame, text="+ ADD BUTTON", fg_color="#4CAF50", width=120).pack(pady=5)

    def create_footer(self):
        self.footer = ctk.CTkFrame(self, height=60, fg_color="white")
        self.footer.grid(row=2, column=1, sticky="ew")
        
        # Delay Settings
        delay_Frame = ctk.CTkFrame(self.footer, fg_color="white")
        delay_Frame.pack(side="left", padx=20, pady=10)
        
        ctk.CTkLabel(delay_Frame, text="Delay Settings").grid(row=0, column=0, sticky="w")
        
        # Row 1: Wait X to Y seconds after every Z messages
        r1 = ctk.CTkFrame(delay_Frame, fg_color="white")
        r1.grid(row=1, column=0, sticky="w")
        self.chk_delay1 = ctk.CTkCheckBox(r1, text="Wait", checkbox_height=18, checkbox_width=18, border_width=1, fg_color="#4CAF50")
        self.chk_delay1.pack(side="left")
        self.chk_delay1.select()
        
        self.delay_wait_min = ctk.CTkEntry(r1, width=35); self.delay_wait_min.insert(0, "5"); self.delay_wait_min.pack(side="left", padx=2)
        ctk.CTkLabel(r1, text="to").pack(side="left")
        self.delay_wait_max = ctk.CTkEntry(r1, width=35); self.delay_wait_max.insert(0, "20"); self.delay_wait_max.pack(side="left", padx=2)
        ctk.CTkLabel(r1, text="seconds after every").pack(side="left")
        self.delay_msg_count = ctk.CTkEntry(r1, width=35); self.delay_msg_count.insert(0, "10"); self.delay_msg_count.pack(side="left", padx=2)
        ctk.CTkLabel(r1, text="Messages").pack(side="left")

        # Row 2: Wait X to Y seconds before every message
        r2 = ctk.CTkFrame(delay_Frame, fg_color="white")
        r2.grid(row=2, column=0, sticky="w")
        self.chk_delay2 = ctk.CTkCheckBox(r2, text="Wait", checkbox_height=18, checkbox_width=18, border_width=1, fg_color="#4CAF50")
        self.chk_delay2.pack(side="left")
        self.chk_delay2.select()
        
        self.delay_each_min = ctk.CTkEntry(r2, width=35); self.delay_each_min.insert(0, "4"); self.delay_each_min.pack(side="left", padx=2)
        ctk.CTkLabel(r2, text="to").pack(side="left")
        self.delay_each_max = ctk.CTkEntry(r2, width=35); self.delay_each_max.insert(0, "8"); self.delay_each_max.pack(side="left", padx=2)
        ctk.CTkLabel(r2, text="seconds before every message").pack(side="left")

        # Action Buttons (Clear, Start)
        action_frame = ctk.CTkFrame(self.footer, fg_color="white")
        action_frame.pack(side="right", padx=20, pady=10)
        
        self.clear_bt = ctk.CTkButton(action_frame, text="🧹 CLEAR", fg_color="#4CAF50", hover_color="#388E3C", width=100, command=self.clear_all_fields)
        self.clear_bt.pack(pady=2)
        
        self.start_bt = ctk.CTkButton(action_frame, text="➤ START CAMPAIGN", fg_color="#4CAF50", hover_color="#388E3C", width=150, command=self.start_campaign_event)
        self.start_bt.pack(pady=2)

    # --- Logic Methods ---

    def load_browser_event(self):
        messagebox.showinfo("Status", "Loading Browser...")
        threading.Thread(target=self._load_browser_thread).start()

    def _load_browser_thread(self):
        try:
            self.campaign_manager.driver.load_browser()
            messagebox.showinfo("Status", "Browser Loaded.")
        except Exception as e:
            messagebox.showerror("Error", f"Error loading browser: {e}")

    def import_numbers(self):
        file_path = filedialog.askopenfilename(filetypes=[("Excel/CSV", "*.xlsx;*.csv")])
        if not file_path:
            return

        try:
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path)
            
            if 'Number' not in df.columns:
                messagebox.showerror("Error", "File must have a 'Number' column.")
                return
            
            valid_count = 0
            for index, row in df.iterrows():
                raw_num = row['Number']
                name = row.get('Name', '')
                valid_num = validate_number(raw_num)
                if valid_num:
                    self.loaded_numbers.append({'Number': valid_num, 'Name': name})
                    valid_count += 1
            
            self._refresh_numbers_display()
            messagebox.showinfo("Import", f"Imported {valid_count} numbers.")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to import: {e}")

    def download_sample(self):
         # Create a sample dataframe and save it
         df = pd.DataFrame({'Number': ['919999999999', '15551234567'], 'Name': ['Test User 1', 'Test User 2']})
         file_path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel file", "*.xlsx")])
         if file_path:
             df.to_excel(file_path, index=False)
             messagebox.showinfo("Success", "Sample file saved.")

    def add_manual_number(self):
        raw_num = self.entry_number.get().strip()
        name = self.entry_name.get().strip()
        
        if not raw_num:
             return 
             
        valid_num = validate_number(raw_num)
        if valid_num:
            if any(d['Number'] == valid_num for d in self.loaded_numbers):
                 messagebox.showwarning("Duplicate", "Number already in list.")
                 return

            self.loaded_numbers.append({'Number': valid_num, 'Name': name})
            self._refresh_numbers_display()
            
            self.entry_number.delete(0, "end")
            self.entry_name.delete(0, "end")
            self.entry_number.focus()
        else:
            messagebox.showerror("Invalid", "Invalid Phone Number. Use country code (e.g. 91...)")

    def delete_number(self, number):
        self.loaded_numbers = [d for d in self.loaded_numbers if d['Number'] != number]
        self._refresh_numbers_display()

    def clear_all_fields(self):
        # 1. Clear Numbers
        self.loaded_numbers = []
        self._refresh_numbers_display()
        
        # 2. Clear Message Boxes
        for box in self.msg_boxes:
            box.delete("1.0", "end")
            
        # 3. Clear Attachments
        self.attachments = []
        self._refresh_attachments_display()

    def _refresh_numbers_display(self):
        # Clear existing
        for widget in self.numbers_scroll_frame.winfo_children():
            widget.destroy()
            
        for i, item in enumerate(self.loaded_numbers):
            self._create_row_widget(item)

    def _create_row_widget(self, item):
        row_frame = ctk.CTkFrame(self.numbers_scroll_frame, fg_color="transparent")
        row_frame.pack(fill="x", pady=2)
        
        ctk.CTkLabel(row_frame, text=item['Number'], width=120, anchor="w").pack(side="left", padx=10)
        ctk.CTkLabel(row_frame, text=item['Name'], width=120, anchor="w").pack(side="left", padx=10)
        
        del_btn = ctk.CTkButton(row_frame, text="🗑", width=30, fg_color="#F44336", hover_color="#D32F2F",
                                command=lambda n=item['Number']: self.delete_number(n))
        del_btn.pack(side="right", padx=5)

    def attach_media(self):
        file_path = filedialog.askopenfilename(filetypes=[("Media", "*.png;*.jpg;*.jpeg;*.mp4;*.3gp")])
        if file_path:
            # Default logic: If first media, set to auto (Main Msg). Else None.
            ext = os.path.splitext(file_path)[1].lower()
            is_media = ext in ['.png', '.jpg', '.jpeg', '.mp4', '.3gp', '.mov']
            
            # Check if we already have an 'auto' caption
            has_auto = any(a['type'] == 'auto' for a in self.attachments)
            
            att_type = 'auto' if is_media and not has_auto else 'none'
            
            self.attachments.append({
                'path': file_path,
                'type': att_type,
                'text': ''
            })
            self._refresh_attachments_display()

    def _refresh_attachments_display(self):
        # Clear existing
        for widget in self.att_scroll_frame.winfo_children():
            widget.destroy()

        for i, item in enumerate(self.attachments):
            self._create_attachment_row(i, item)

    def _create_attachment_row(self, index, item):
        path = item['path']
        filename = os.path.basename(path)
        
        row = ctk.CTkFrame(self.att_scroll_frame, fg_color="transparent")
        row.pack(fill="x", pady=2)
        
        # Shorten filename
        disp_name = (filename[:15] + '..') if len(filename) > 15 else filename
        ctk.CTkLabel(row, text=disp_name, width=100, anchor="w", font=("Arial", 11)).pack(side="left", padx=2)
        
        # Caption Status Label
        caption_text = "-"
        text_color = "gray"
        
        if item['type'] == 'auto':
            caption_text = "Main Msg"
            text_color = "#4CAF50" # Green
        elif item['type'] == 'custom':
            caption_text = "Custom"
            text_color = "#2196F3" # Blue
        elif item['type'] == 'static':
            caption_text = f"Msg {item['msg_index'] + 1}"
            text_color = "#9C27B0" # Purple
        
        lbl = ctk.CTkLabel(row, text=caption_text, width=60, anchor="w", text_color=text_color, font=("Arial", 10, "bold" if item['type'] != 'none' else "normal"))
        lbl.pack(side="left", padx=2)
        
        # Bind Right Click to Label
        lbl.bind("<Button-3>", lambda event, i=index: self._show_caption_menu(event, i))
        
        # Delete Button
        del_btn = ctk.CTkButton(row, text="x", width=20, height=20, fg_color="#E57373", hover_color="#D32F2F",
                                command=lambda i=index: self.remove_attachment(i))
        del_btn.pack(side="right", padx=2)

    def _show_caption_menu(self, event, index):
        # Create Context Menu
        menu =  tkinter.Menu(self, tearoff=0)
        menu.add_command(label="Use Main Message", command=lambda: self._set_caption_type(index, 'auto'))
        menu.add_command(label="Select Message...", command=lambda: self._open_message_selection_dialog(index))
        menu.add_command(label="Custom Caption...", command=lambda: self._set_custom_caption(index))
        menu.add_command(label="No Caption", command=lambda: self._set_caption_type(index, 'none'))
        menu.tk_popup(event.x_root, event.y_root)

    def _open_message_selection_dialog(self, index):
        # Create a Toplevel window for selection
        dialog = ctk.CTkToplevel(self)
        dialog.title("Select Message")
        dialog.geometry("300x250")
        dialog.grab_set() # Modal
        
        ctk.CTkLabel(dialog, text="Select a specific message to apply as caption:", wraplength=280).pack(pady=10)
        
        for i in range(5):
            btn_text = f"Message {i+1}"
            ctk.CTkButton(dialog, text=btn_text, command=lambda idx=i: [self._set_static_message(index, idx), dialog.destroy()]).pack(pady=5, padx=20, fill="x")

    def _set_static_message(self, index, msg_index):
         if 0 <= index < len(self.attachments):
             self.attachments[index]['type'] = 'static'
             self.attachments[index]['msg_index'] = msg_index
             self._refresh_attachments_display()

    def _set_caption_type(self, index, new_type):
        if 0 <= index < len(self.attachments):
            # If setting to auto, ensure no other attachment is auto (optional logic, but good for UX)
            if new_type == 'auto':
                 for item in self.attachments:
                     if item['type'] == 'auto':
                         item['type'] = 'none'
            
            self.attachments[index]['type'] = new_type
            self._refresh_attachments_display()

    def _set_custom_caption(self, index):
        dialog = ctk.CTkInputDialog(text="Enter Custom Caption:", title="Custom Caption")
        text = dialog.get_input()
        if text is not None: # None means cancel
             self.attachments[index]['type'] = 'custom'
             self.attachments[index]['text'] = text
             self._refresh_attachments_display()

    def remove_attachment(self, index):
        if 0 <= index < len(self.attachments):
            self.attachments.pop(index)
            self._refresh_attachments_display()

    def start_campaign_event(self):
        if not self.loaded_numbers:
            messagebox.showerror("Error", "No numbers loaded!")
            return
        
        messages = [box.get("1.0", "end-1c") for box in self.msg_boxes]
        
        # Validation: allow if message exists, OR if attachments exist (even without text, though usually text is desired)
        # But if user wants just image, that's fine.
        has_msg = any(msg.strip() for msg in messages)
        has_att = len(self.attachments) > 0
        
        if not has_msg and not has_att:
            messagebox.showerror("Error", "Message or Attachment required.")
            return

        try:
             # Logic to read from the two delay rows
             # Row 2 (Before every message) is akin to our per-message delay
             d_min = int(self.delay_each_min.get())
             d_max = int(self.delay_each_max.get())
             
             # Ignoring Row 1 (Block delay) for now to keep logic simple, or we can add it to CampaignManager later.
             
             known_interval = 20 # Hardcoded for now per UI simplicity, or add back to settings if user asks
        except ValueError:
             messagebox.showerror("Error", "Invalid delay settings.")
             return
        
        # Convert numbers list of dicts to list of dicts (already is)
        
        self.campaign_manager.set_config(
            numbers=self.loaded_numbers,
            messages=messages,
            attachments=self.attachments,
            delay_range=(d_min, d_max),
            known_numbers=[],
            known_interval=known_interval
        )
        
        self.campaign_manager.start_campaign()

    def update_status_callback(self, text):
        print(text) 
        # Optionally update a status bar if I added one (The image has "Ready" status bottom right usually, I put it top bar or footer)

if __name__ == "__main__":
    app = MainWindow()
    app.mainloop()
