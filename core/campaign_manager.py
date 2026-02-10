import time
import threading
from datetime import datetime
from .whatsapp_driver import WhatsAppDriver

class CampaignManager:
    def __init__(self, update_status_callback=None):
        self.driver = WhatsAppDriver()
        self.numbers = []
        self.messages = [] # List of non-empty messages
        self.attachments = []
        self.delay_range = (5, 10)
        self.known_numbers = [] # List of tuples/dicts
        self.known_interval = 20
        self.is_running = False
        self.lock = threading.Lock()
        self.update_status_callback = update_status_callback
        
        self.sent_count = 0
        self.results = []

    def set_config(self, numbers, messages, attachments, delay_range, known_numbers, known_interval):
        self.numbers = numbers
        self.raw_messages = messages # Store all messages (even empty ones, to preserve index)
        self.messages = [m for m in messages if m and m.strip()] # Filter empty for rotation
        self.attachments = attachments
        self.delay_range = delay_range
        self.known_numbers = known_numbers
        self.known_interval = known_interval

    def start_campaign(self):
        if not self.driver.driver:
            self.driver.load_browser()
            
        if self.is_running:
            self._update_status("Campaign already running.")
            return

        self.is_running = True
        self.thread = threading.Thread(target=self._run_loop)
        self.thread.start()

    def stop_campaign(self):
        self.is_running = False

    def _run_loop(self):
        if not self.lock.acquire(blocking=False):
            return
        
        try:
            self.sent_count = 0
            self.results = []
            
            if not self.messages and not self.attachments:
             # Check if we have static attachments that use valid messages
             # Optimization: just check valid message count.
             valid_static = any(a.get('type') == 'static' and self.raw_messages[a.get('msg_index')] for a in self.attachments)
             if not valid_static:
                 self._update_status("Error: No messages or media configured.")
                 return

            for i, number_data in enumerate(self.numbers):
                if not self.is_running:
                    break
                
                number = str(number_data.get('Number', ''))
                name = str(number_data.get('Name', ''))
                
                if not number:
                    continue

                # Check Known Number Interleaving
                if self.sent_count > 0 and self.sent_count % self.known_interval == 0 and self.known_numbers:
                     self._send_to_known()

                # Message Rotation Logic
                if self.messages:
                    msg_index = i % len(self.messages)
                    current_msg = self.messages[msg_index]
                else:
                    current_msg = "" # Media only case

                # Resolve Attachment Captions (Static vs Auto)
                # Create a copy to modify for this specific send
                resolved_attachments = []
                for att in self.attachments:
                    # att is a dict
                    new_att = att.copy()
                    if new_att.get('type') == 'static':
                        # Resolve static message reference
                        m_idx = new_att.get('msg_index', 0)
                        if 0 <= m_idx < len(self.raw_messages):
                            new_att['type'] = 'custom' # Driver understands custom
                            new_att['text'] = self.raw_messages[m_idx]
                        else:
                            new_att['type'] = 'none' # Fallback
                    
                    resolved_attachments.append(new_att)

                self._update_status(f"Sending to {number}...")
                # We use a new method name or update existing one. Let's start using 'send_campaign_batch' as planned
                # But since we update driver later, let's update call here now.
                
                success = self.driver.send_campaign_batch(number, current_msg, resolved_attachments)
                
                status = "Sent" if success else "Failed"
                self.results.append({
                    "Number": number,
                    "Name": name,
                    "Status": status,
                    "Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                
                if success:
                    self.sent_count += 1
                
                # Delay
                import random
                delay = random.randint(self.delay_range[0], self.delay_range[1])
                self._update_status(f"Waiting {delay}s...")
                time.sleep(delay)

        finally:
            self.is_running = False
            self.lock.release()
            self._update_status("Campaign Completed.")

    def _send_to_known(self):
        self._update_status("Sending to known numbers...")
        # Simple round robin or send to all known? Requirement says "a message should be sent to the known number"
        # Implies one known number per interval, or maybe rotating through known numbers.
        # Let's rotate through known numbers.
        known_idx = (self.sent_count // self.known_interval) % len(self.known_numbers)
        target = self.known_numbers[known_idx]
        
        # What message to send to known number? Usually a random generic one or one of the campaign messages?
        # Req doesn't specify. Let's send the "current" rotation message or a generic "Hi".
        # Let's use "Hi" for safety to ensure it looks like a normal ping.
        self.driver.send_message(target, "Hi") 
        time.sleep(5)

    def _update_status(self, text):
        print(text)
        if self.update_status_callback:
            self.update_status_callback(text)
