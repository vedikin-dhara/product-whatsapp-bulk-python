from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    StaleElementReferenceException,
    SessionNotCreatedException,
    WebDriverException,
)
import time
import os
import pyperclip
import socket

MEDIA_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.mp4', '.3gp', '.mov'}
PHOTO_VIDEO_ACCEPT = 'image/*,video/mp4,video/3gpp,video/quicktime'
DEBUG_PORT = 9222


class WhatsAppDriver:
    def __init__(self, user_data_dir=None, port=9222):
        self.driver = None
        self.port = port
        if user_data_dir is None:
            self.user_data_dir = os.path.abspath(os.path.join(os.getcwd(), "whatsapp_profile"))
        else:
            self.user_data_dir = os.path.abspath(user_data_dir)

        if not os.path.exists(self.user_data_dir):
            os.makedirs(self.user_data_dir)

    def _is_driver_alive(self):
        if not self.driver:
            return False
        try:
            _ = self.driver.current_url
            return True
        except WebDriverException:
            self.driver = None
            return False

    def load_browser(self):
        """Launch or re-attach to Chrome, then navigate to WhatsApp Web on the first tab."""
        if self._is_driver_alive():
            # Already connected - ensure we are on WhatsApp Web
            try:
                if "web.whatsapp.com" not in self.driver.current_url:
                    self.driver.get("https://web.whatsapp.com")
            except Exception:
                pass
            return

        if self._attach_to_existing_chrome():
            # Attached to running Chrome - navigate current tab to WhatsApp
            try:
                if "web.whatsapp.com" not in self.driver.current_url:
                    self.driver.get("https://web.whatsapp.com")
            except Exception:
                pass
            return

        options = Options()
        options.page_load_strategy = 'eager'
        options.add_argument(f"user-data-dir={self.user_data_dir}")
        options.add_argument("--profile-directory=Default")
        options.add_argument(f"--remote-debugging-port={self.port}")
        options.add_argument("--start-maximized")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-extensions")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)

        try:
            self.driver = webdriver.Chrome(options=options)
        except SessionNotCreatedException as exc:
            if self._attach_to_existing_chrome():
                return
            raise RuntimeError(
                "Chrome could not start. Close all Chrome windows opened by WASender, "
                "then click ACCOUNTS again before starting a campaign."
            ) from exc

        self.driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        self.driver.get("https://web.whatsapp.com")

    def open_whatsapp_tab(self):
        """Open WhatsApp Web in a new tab on the existing Chrome window.
        Returns the new tab's window handle, or None on failure."""
        if not self._is_driver_alive():
            return None
        try:
            current_handles = set(self.driver.window_handles)
            self.driver.execute_script("window.open('https://web.whatsapp.com', '_blank');")
            time.sleep(1.5)
            new_handles = set(self.driver.window_handles) - current_handles
            if new_handles:
                new_handle = new_handles.pop()
                self.driver.switch_to.window(new_handle)
                return new_handle
        except Exception as e:
            print(f"Error opening new WhatsApp tab: {e}")
        return None

    def switch_to_tab(self, handle):
        """Switch the driver focus to a given tab handle."""
        try:
            self.driver.switch_to.window(handle)
            return True
        except Exception as e:
            print(f"Could not switch to tab {handle}: {e}")
            return False

    def _attach_to_existing_chrome(self):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.2)
            result = sock.connect_ex(('127.0.0.1', self.port))
            sock.close()
            if result != 0:
                # Port is closed, Chrome is not running
                return False
        except Exception:
            pass

        options = Options()
        options.add_experimental_option("debuggerAddress", f"127.0.0.1:{self.port}")
        try:
            self.driver = webdriver.Chrome(options=options)
            _ = self.driver.current_url
            print("Reusing existing Chrome session.")
            return True
        except WebDriverException:
            self.driver = None
            return False

    def is_logged_in(self):
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[aria-label='Chat list']"))
            )
            return True
        except Exception:
            return False

    def send_campaign_batch(self, number, message, attachments=None):
        try:
            if not self._is_driver_alive():
                print("Browser session is not available.")
                return False

            link = f"https://web.whatsapp.com/send?phone={number}"
            self.driver.get(link)

            if not self._wait_for_chat_compose():
                print(f"Chat failed to load for {number}")
                return False

            first_media = self._find_first_media_path(attachments)
            if not first_media:
                if message and message.strip():
                    self._send_text_only(message)
                    return True
                print("No message or media to send.")
                return False

            caption = self._resolve_media_caption(message, attachments, first_media)
            print(f"Sending photo/video with caption to {number}")
            return self._upload_and_send(first_media, caption)

        except Exception as e:
            print(f"Error handling batch for {number}: {e}")
            return False

    def send_message(self, number, message, media_path=None):
        attachments = [{'path': media_path, 'type': 'auto'}] if media_path else []
        return self.send_campaign_batch(number, message, attachments)

    def _find_first_media_path(self, attachments):
        if not attachments:
            return None
        for item in attachments:
            path = item.get('path', '')
            if not path:
                continue
            ext = os.path.splitext(path)[1].lower()
            if ext in MEDIA_EXTENSIONS:
                return path
        return None

    def _resolve_media_caption(self, message, attachments, media_path):
        if not attachments:
            return message or ""

        for item in attachments:
            if item.get('path') != media_path:
                continue

            att_type = item.get('type', 'auto')
            if att_type == 'none':
                return ""
            if att_type in ('custom', 'static'):
                return item.get('text', '') or ""
            if att_type == 'auto':
                return message or ""

        return message or ""

    def _wait_for_chat_compose(self, timeout=30):
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "footer"))
            )
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR,
                    "footer span[data-icon='plus'], footer span[data-icon='clip'], footer [aria-label='Attach']"
                ))
            )
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR,
                    "footer div[contenteditable='true'][data-tab='10']"
                ))
            )
            time.sleep(1.5)
            return True
        except TimeoutException:
            return False

    def _send_text_only(self, message):
        try:
            msg_box = self.driver.find_element(
                By.CSS_SELECTOR,
                "footer div[contenteditable='true'][data-tab='10']"
            )
            msg_box.click()
            pyperclip.copy(message)
            msg_box.send_keys(Keys.CONTROL, 'v')
            time.sleep(0.8)
            msg_box.send_keys(Keys.ENTER)
        except Exception as e:
            print(f"Error sending text: {e}")

    def _click_attach_button(self):
        selectors = [
            "footer span[data-icon='plus']",
            "footer span[data-icon='clip']",
            "footer div[title='Attach']",
            "footer [aria-label='Attach']",
            "span[data-icon='plus']",
            "span[data-icon='clip']",
        ]
        for selector in selectors:
            try:
                btn = WebDriverWait(self.driver, 8).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                )
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                time.sleep(0.3)
                self.driver.execute_script("arguments[0].click();", btn)
                time.sleep(1.0)
                return True
            except (TimeoutException, StaleElementReferenceException):
                continue
        return False

    def _find_photo_video_input(self):
        xpath_selectors = [
            f'//input[@type="file" and @accept="{PHOTO_VIDEO_ACCEPT}"]',
            '//input[@type="file" and contains(@accept, "image") and contains(@accept, "video") and not(contains(@accept, "webp"))]',
        ]
        for xpath in xpath_selectors:
            inputs = self.driver.find_elements(By.XPATH, xpath)
            if inputs:
                return inputs[0]

        for inp in self.driver.find_elements(By.CSS_SELECTOR, "input[type='file']"):
            accept = (inp.get_attribute("accept") or "").lower()
            if "image" in accept and "video" in accept and "webp" not in accept:
                return inp

        return None

    def _open_photo_video_picker(self):
        """
        Open attach menu and target the hidden Photos & Videos input.
        Do NOT click the Photos menu item — that opens the native OS file dialog
        and breaks Selenium file upload on Windows.
        """
        if not self._click_attach_button():
            print("Could not open attach menu.")
            return None

        file_input = self._find_photo_video_input()
        if file_input:
            return file_input

        print("Photos & Videos file input not found.")
        return None

    def _wait_for_media_preview(self, timeout=35):
        deadline = time.time() + timeout
        preview_signals = [
            (By.CSS_SELECTOR, "div[data-animate-media-popup='true']"),
            (By.CSS_SELECTOR, "div[aria-label='Preview']"),
            (By.CSS_SELECTOR, "span[data-icon='media-preview']"),
            (By.CSS_SELECTOR, "span[data-icon='wds-ic-hd']"),
            (By.CSS_SELECTOR, "span[data-icon='crop']"),
            (By.CSS_SELECTOR, "span[data-icon='rotate']"),
            (By.CSS_SELECTOR, "div[contenteditable='true'][data-tab='11']"),
            (By.XPATH, "//div[@role='dialog']//span[@data-icon='send']"),
            (By.XPATH, "//div[contains(@aria-label, 'caption') or contains(@aria-label, 'Caption')]"),
        ]

        while time.time() < deadline:
            for by, selector in preview_signals:
                if self.driver.find_elements(by, selector):
                    time.sleep(1.2)
                    return True
            time.sleep(0.4)

        return False

    def _find_preview_caption_box(self):
        caption_selectors = [
            (By.CSS_SELECTOR, "div[data-animate-media-popup='true'] div[contenteditable='true'][data-lexical-editor='true']"),
            (By.CSS_SELECTOR, "div[aria-label='Preview'] div[contenteditable='true']"),
            (By.CSS_SELECTOR, "div[contenteditable='true'][data-tab='11']"),
            (By.XPATH, "//div[@contenteditable='true' and (contains(@aria-label, 'caption') or contains(@aria-label, 'Caption') or contains(@aria-placeholder, 'caption') or contains(@aria-placeholder, 'Caption'))]"),
            (By.XPATH, "//div[@role='dialog']//div[@contenteditable='true']"),
        ]
        for by, selector in caption_selectors:
            try:
                return WebDriverWait(self.driver, 8).until(
                    EC.presence_of_element_located((by, selector))
                )
            except TimeoutException:
                continue
        return None

    def _set_preview_caption(self, caption_box, caption):
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", caption_box)
        self.driver.execute_script("arguments[0].focus(); arguments[0].click();", caption_box)
        time.sleep(0.5)

        caption_box.send_keys(Keys.CONTROL, 'a')
        caption_box.send_keys(Keys.BACKSPACE)
        time.sleep(0.2)

        pyperclip.copy(caption)
        caption_box.send_keys(Keys.CONTROL, 'v')
        time.sleep(1.5)

        self.driver.execute_script(
            """
            const el = arguments[0];
            el.dispatchEvent(new InputEvent('input', { bubbles: true }));
            el.dispatchEvent(new Event('change', { bubbles: true }));
            """,
            caption_box,
        )
        time.sleep(0.5)

    def _click_preview_send(self):
        send_selectors = [
            (By.CSS_SELECTOR, "div[data-animate-media-popup='true'] span[data-icon='send']"),
            (By.CSS_SELECTOR, "div[data-animate-media-popup='true'] [aria-label='Send']"),
            (By.CSS_SELECTOR, "div[aria-label='Preview'] span[data-icon='send']"),
            (By.XPATH, "//div[@role='dialog']//span[@data-icon='send']"),
            (By.XPATH, "//div[@role='dialog']//*[@aria-label='Send']"),
            (By.CSS_SELECTOR, "span[data-icon='send-light']"),
        ]
        for by, selector in send_selectors:
            try:
                send_btn = WebDriverWait(self.driver, 8).until(
                    EC.element_to_be_clickable((by, selector))
                )
                self.driver.execute_script("arguments[0].click();", send_btn)
                return True
            except TimeoutException:
                continue
        return False

    def _upload_and_send(self, media_path, caption):
        """
        Upload via Photos & Videos hidden input only.
        Never paste into chat or use generic file inputs (causes sticker send).
        """
        try:
            abs_path = os.path.abspath(media_path)
            if not os.path.isfile(abs_path):
                print(f"Media file not found: {abs_path}")
                return False

            file_input = self._open_photo_video_picker()
            if not file_input:
                return False

            print(f"Uploading media file: {os.path.basename(abs_path)}")
            file_input.send_keys(abs_path)

            if not self._wait_for_media_preview():
                print("Media preview did not open after upload.")
                return False

            if caption and caption.strip():
                caption_box = self._find_preview_caption_box()
                if caption_box:
                    print(f"Adding caption: {caption[:40]}...")
                    self._set_preview_caption(caption_box, caption)
                else:
                    print("Caption box not found; sending media without caption.")

            if not self._click_preview_send():
                print("Preview send button not found.")
                return False

            try:
                WebDriverWait(self.driver, 20).until_not(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-animate-media-popup='true']"))
                )
            except TimeoutException:
                pass

            print("Photo/video sent with caption.")
            return True

        except Exception as e:
            print(f"General error in _upload_and_send: {e}")
            return False

    def quit(self):
        if self.driver:
            try:
                self.driver.quit()
            except WebDriverException:
                pass
            self.driver = None
