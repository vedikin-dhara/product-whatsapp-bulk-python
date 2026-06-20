import mysql.connector
import os
import json
import uuid
import random
import string
from datetime import datetime

CONFIG_FILE = "license_config.json"
KEYS_FILE = "generated_keys.txt"

def generate_license_key():
    """
    Generates a unique, professional-looking license key: WAS-XXXX-XXXX-XXXX-XXXX
    """
    parts = []
    for _ in range(4):
        part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        parts.append(part)
    return "WAS-" + "-".join(parts)

class LicenseManager:
    def __init__(self):
        self.host = "localhost"
        self.user = "root"
        self.password = ""
        self.database = "wasender"
        self.connection = None
        self._init_db()

    def _get_raw_connection(self):
        """
        Attempts to connect to the MySQL server without selecting a database.
        """
        return mysql.connector.connect(
            host=self.host,
            user=self.user,
            password=self.password
        )

    def _init_db(self):
        """
        Connects to the MySQL database. Creates the database and table if they do not exist.
        If table is empty, seeds it with 3 automatically generated unique keys.
        """
        try:
            # 1. Connect to MySQL Server
            conn = self._get_raw_connection()
            cursor = conn.cursor()
            
            # 2. Create Database if not exists
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.database}")
            conn.commit()
            cursor.close()
            conn.close()

            # 3. Connect to the specific database
            self.connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database
            )
            
            # 4. Create table if not exists
            cursor = self.connection.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS licenses (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    license_key VARCHAR(255) UNIQUE NOT NULL,
                    is_activated TINYINT(1) DEFAULT 0,
                    activated_at DATETIME NULL,
                    username VARCHAR(255) NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)
            self.connection.commit()

            # 5. Check if we need to seed initial license keys
            cursor.execute("SELECT COUNT(*) FROM licenses")
            count = cursor.fetchone()[0]
            if count == 0:
                print("Licenses table is empty. Generating and seeding 3 unique license keys...")
                seeded_keys = []
                for i in range(1, 4):
                    key = generate_license_key()
                    username = f"SeedUser{i}"
                    cursor.execute(
                        "INSERT INTO licenses (license_key, is_activated, username) VALUES (%s, %s, %s)",
                        (key, 0, username)
                    )
                    seeded_keys.append((key, username))
                self.connection.commit()
                
                # Write keys to a file for the user to easily copy
                with open(KEYS_FILE, "w") as f:
                    f.write("=== AUTOMATICALLY GENERATED UNIQUE LICENSE KEYS ===\n")
                    f.write("Copy one of these keys to test the License Key popup activation:\n\n")
                    for key, username in seeded_keys:
                        f.write(f"Username: {username}\nLicense Key: {key}\nStatus: Not Activated\n\n")
                    f.write(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                print(f"Generated keys have been written to {KEYS_FILE}")
            
            cursor.close()

        except mysql.connector.Error as err:
            print(f"Database Initialization Error: {err}")
            self.connection = None

    def is_connected(self):
        """
        Checks if the manager is successfully connected to the database.
        """
        if self.connection is None:
            return False
        try:
            self.connection.ping(reconnect=True, attempts=3, delay=1)
            return True
        except mysql.connector.Error:
            return False

    def add_new_user(self, username):
        """
        Automatically generates a unique, immutable license key for a new user and adds it to the database.
        """
        if not self.is_connected():
            return None, "Database not connected."

        key = generate_license_key()
        try:
            cursor = self.connection.cursor()
            # Double check uniqueness in a loop just in case
            attempts = 0
            while attempts < 10:
                cursor.execute("SELECT id FROM licenses WHERE license_key = %s", (key,))
                if cursor.fetchone() is None:
                    break
                key = generate_license_key()
                attempts += 1

            cursor.execute(
                "INSERT INTO licenses (license_key, is_activated, username) VALUES (%s, %s, %s)",
                (key, 0, username)
            )
            self.connection.commit()
            cursor.close()
            return key, None
        except mysql.connector.Error as err:
            return None, f"Failed to add user: {err}"

    def check_license_in_db(self, license_key):
        """
        Queries the database to check if the license key exists and retrieves its details.
        Returns (exists, is_activated, username)
        """
        if not self.is_connected():
            raise ConnectionError("Database is not connected.")

        cursor = self.connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM licenses WHERE license_key = %s", (license_key,))
        result = cursor.fetchone()
        cursor.close()

        if result:
            return True, bool(result['is_activated']), result['username']
        return False, False, None

    def activate_license(self, license_key):
        """
        Activates the key in the database if not activated, saves locally, and returns status.
        """
        try:
            exists, is_activated, username = self.check_license_in_db(license_key)
            if not exists:
                return False, "The license key entered is incorrect or does not exist."

            if not is_activated:
                # Update status to activated in the database
                cursor = self.connection.cursor()
                cursor.execute(
                    "UPDATE licenses SET is_activated = 1, activated_at = %s WHERE license_key = %s",
                    (datetime.now(), license_key)
                )
                self.connection.commit()
                cursor.close()

            # Save the license key locally
            self._save_local_license(license_key)
            return True, "License activated successfully!"

        except Exception as e:
            return False, f"Activation error: {str(e)}"

    def verify_local_license(self):
        """
        Checks the local config file and verifies the license key against the database.
        Returns True if the local license is correct and active, False otherwise.
        """
        local_key = self._get_local_license()
        if not local_key:
            return False

        try:
            exists, is_activated, _ = self.check_license_in_db(local_key)
            # If license is correct (exists) and is activated, then it's valid
            if exists and is_activated:
                return True
            else:
                # Key is no longer valid in database, remove local configuration
                self.clear_local_license()
                return False
        except Exception:
            # If database is offline, but we have a local key, should we allow it?
            # The prompt says: check the license key is correct or not if license key is correct than open the WASender.
            # To be safe, if the local DB is down, we must show an error because it verifies against the database.
            return False

    def _get_local_license(self):
        """
        Reads local license key from JSON config.
        """
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    data = json.load(f)
                    return data.get("license_key")
            except Exception:
                return None
        return None

    def _save_local_license(self, license_key):
        """
        Saves the license key to local JSON config.
        """
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump({"license_key": license_key, "activated_at": str(datetime.now())}, f, indent=4)
        except Exception as e:
            print(f"Failed to save local license: {e}")

    def clear_local_license(self):
        """
        Clears local license key configuration.
        """
        if os.path.exists(CONFIG_FILE):
            try:
                os.remove(CONFIG_FILE)
            except Exception as e:
                print(f"Failed to remove config file: {e}")
