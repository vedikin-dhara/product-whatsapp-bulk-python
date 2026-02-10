from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import os
import pyperclip

class WhatsAppDriver:
    def __init__(self, user_data_dir=None):
        self.driver = None
        if user_data_dir is None:
            self.user_data_dir = os.path.join(os.getcwd(), "whatsapp_profile")
        else:
            self.user_data_dir = user_data_dir
        
        if not os.path.exists(self.user_data_dir):
            os.makedirs(self.user_data_dir)

    def load_browser(self):
        options = Options()
        options.add_argument(f"user-data-dir={self.user_data_dir}")
        options.add_argument("--start-maximized")
        # options.add_argument("--headless") # DO NOT USE HEADLESS FOR WHATSAPP 
        
        # Anti-detection
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.get("https://web.whatsapp.com")

    def is_logged_in(self):
        try:
            # Check for element that appears only when logged in (e.g., chat list pane)
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[aria-label='Chat list']"))
            )
            return True
        except:
            return False

    def send_campaign_batch(self, number, message, attachments=None):
        try:
            # 1. Navigate to chat
            link = f"https://web.whatsapp.com/send?phone={number}"
            self.driver.get(link)
            
            # 2. Wait for chat input to verify load
            try:
                WebDriverWait(self.driver, 25).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div[contenteditable='true'][data-tab='10']"))
                )
            except:
                print(f"Chat failed to load for {number}")
                return False

            # 3. Handle Media + Caption Logic (STRICT SINGLE MESSAGE)
            first_media = None
            if attachments:
                for item in attachments:
                    path = item.get('path', '')
                    if not path: continue
                    
                    ext = os.path.splitext(path)[1].lower()
                    if ext in ['.png', '.jpg', '.jpeg', '.mp4', '.3gp', '.mov']:
                        first_media = path
                        break # Found the first image/video
            
            if first_media:
                # MANDATORY: Send media WITH caption as ONE message
                # Bypasses all separate text logic
                print(f"Strict Mode: Sending first media found with caption to {number}")
                success = self._upload_and_send(first_media, message)
                return success
            else:
                # No media found, send text-only if message exists
                if message and message.strip():
                    self._send_text_only(message)
                    return True
                else:
                    print("No message or media to send.")
                    return False

        except Exception as e:
            print(f"Error handling batch for {number}: {e}")
            return False

    def send_message(self, number, message, media_path=None):
        # Legacy support wrapper
        attachments = [{'path': media_path}] if media_path else []
        return self.send_campaign_batch(number, message, attachments)

    def _send_text_only(self, message):
        try:
            msg_box = self.driver.find_element(By.CSS_SELECTOR, "div[contenteditable='true'][data-tab='10']")
            pyperclip.copy(message)
            msg_box.send_keys(Keys.CONTROL, 'v')
            time.sleep(1)
            msg_box.send_keys(Keys.ENTER)
        except Exception as e:
             print(f"Error sending text: {e}")

    def _upload_and_send(self, media_path, caption):
        """
        Forcefully sends media + caption in ONE single bubble.
        Strictly follows the 'Photos & Videos' workflow to avoid stickers.
        """
        try:
            # 1. Click the Attach button
            try:
                attach_btn = WebDriverWait(self.driver, 15).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "div[title='Attach'], span[data-icon='plus'], span[data-icon='clip'], div[aria-label='Attach']"))
                )
                self.driver.execute_script("arguments[0].click();", attach_btn)
                time.sleep(1.5)
            except Exception as e:
                print(f"Failed to click Attach button: {e}")
                # Fallback: maybe it's already open or we can try to find input directly later
            
            # 2. Click strictly on the "Photos & Videos" menu item
            # This ensures WhatsApp triggers the correct internal state for media (NOT stickers)
            try:
                # We search for the button that has the 'image' or 'photo' related icon/text
                photo_video_btn = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//li//span[contains(text(), 'Photos & Videos')]/parent::div/parent::button | //button[descendant::span[@data-icon='attach-image']]"))
                )
                self.driver.execute_script("arguments[0].click();", photo_video_btn)
                time.sleep(1.5)
            except Exception as e:
                print(f"Could not click 'Photos & Videos' icon, attempting direct input: {e}")

            # 3. Handle the File Input
            # Once 'Photos & Videos' is clicked (or even if clickable fails), the hidden input is usually primed
            file_input = None
            try:
                inputs = self.driver.find_elements(By.XPATH, "//input[@type='file']")
                for inp in inputs:
                    accept = (inp.get_attribute("accept") or "").lower()
                    # Proper media input MUST accept both images and videos
                    if "image" in accept and "video" in accept:
                        file_input = inp
                        break
                
                if not file_input and inputs:
                    for inp in inputs:
                        if "webp" not in (inp.get_attribute("accept") or "").lower():
                            file_input = inp
                            break
            except Exception as e:
                print(f"Error finding file input: {e}")

            if not file_input:
                print("CRITICAL: Suitable media input not found.")
                return False

            # Upload the file
            self.driver.execute_script("arguments[0].style.display = 'block'; arguments[0].style.visibility = 'visible';", file_input)
            file_input.send_keys(os.path.abspath(media_path))
            
            # 4. Handle the Preview Screen & Caption
            # This is where the single bubble is consolidated
            try:
                # Wait for the preview dialog to appear (the caption box is a good signal)
                print("Waiting for media preview/caption screen...")
                caption_xpath = "//div[@contenteditable='true' and (contains(@aria-label, 'caption') or contains(@aria-placeholder, 'caption') or @data-tab='10')]"
                caption_box = WebDriverWait(self.driver, 25).until(
                    EC.presence_of_element_located((By.XPATH, caption_xpath))
                )
                
                if caption:
                    print(f"Injecting caption: {caption[:20]}...")
                    # Force focus
                    self.driver.execute_script("arguments[0].focus(); arguments[0].click();", caption_box)
                    time.sleep(0.8)
                    
                    # Clear completely
                    caption_box.send_keys(Keys.CONTROL, 'a')
                    caption_box.send_keys(Keys.BACKSPACE)
                    time.sleep(0.3)
                    
                    # Paste correctly
                    pyperclip.copy(caption)
                    caption_box.send_keys(Keys.CONTROL, 'v')
                    
                    # CRITICAL: Wait for Lexical editor to register the change
                    # If we send too fast, the caption might be lost or sent separately
                    time.sleep(2.0) 
                
                # 5. Final Send from Preview
                send_btn_xpath = "//div[@aria-label='Send'] | //span[@data-icon='send'] | //button[descendant::span[@data-icon='send']]"
                send_btn = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, send_btn_xpath))
                )
                
                # Double check the caption box still has focus/content if possible (UX delay)
                self.driver.execute_script("arguments[0].click();", send_btn)
                print("Media + Caption sent as consolidated bubble.")
                
                # Wait for the preview screen to close
                WebDriverWait(self.driver, 15).until_not(
                    EC.presence_of_element_located((By.XPATH, "//div[@aria-label='Preview']"))
                )
                return True

            except Exception as e:
                print(f"Error during preview/caption phase: {e}")
                # Fallback to Enter if button click fails
                try:
                    caption_box.send_keys(Keys.ENTER)
                    time.sleep(2)
                    return True
                except:
                    return False

        except Exception as e:
            print(f"General error in _upload_and_send: {e}")
            return False

    def quit(self):
        if self.driver:
            self.driver.quit()
