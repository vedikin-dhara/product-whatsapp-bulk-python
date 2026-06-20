import sys
from core.license_manager import LicenseManager

def main():
    # Instantiate LicenseManager
    manager = LicenseManager()
    
    if not manager.is_connected():
        print("\n❌ Error: Could not connect to local MySQL database server.")
        print("Please make sure WampServer / XAMPP MySQL is running with username 'root' and no password.\n")
        sys.exit(1)
        
    print("\n==================================================")
    print("        WASender - Generate New License Key       ")
    print("==================================================\n")
    
    if len(sys.argv) > 1:
        username = " ".join(sys.argv[1:])
    else:
        username = input("Enter username for the new license key: ").strip()
        
    if not username:
        print("❌ Error: Username cannot be empty.")
        sys.exit(1)
        
    key, error = manager.add_new_user(username)
    
    if error:
        print(f"❌ Error: {error}")
    else:
        print("==================================================")
        print(" SUCCESS! New user added successfully.")
        print(f" Username:    {username}")
        print(f" License Key: {key}")
        print("==================================================")
        print("\nNote: The license key is generated automatically, unique, and cannot be changed.")
        
        # Append to generated_keys.txt
        try:
            with open("generated_keys.txt", "a") as f:
                f.write(f"Username: {username}\nLicense Key: {key}\nStatus: Not Activated (Generated via Admin Tool)\n\n")
            print("The generated key has been appended to 'generated_keys.txt'.\n")
        except Exception as e:
            print(f"Could not append to generated_keys.txt: {e}\n")

if __name__ == "__main__":
    main()
