# signin.py
import mysql.connector
from admin_main import admin_main
from driver_main import driver_main

def welcome_banner():
    print("\n" + "═"*62)
    print("║                                                              ║")
    print("║       🇵🇭  LAND TRANSPORTATION OFFICE MANAGEMENT SYSTEM       ║")
    print("║                    - Central Portal -                        ║")
    print("║                                                              ║")
    print("" + "═"*62)
    print(" Please select your gateway:")
    print("    [1] LTO Personnel Portal (Administrative Access)")
    print("    [2] Driver Portal        (View Personal Records)")
    print("    [0] Exit Application")
    print("" + "─"*62)

def sign_in_admin(conn):
    print("\n --- LTO PERSONNEL AUTHENTICATION ---")
    admin_id = input("Enter Personnel ID: ").strip().upper()
    password = input("Enter Password: ").strip()

    # For a simple backbone, we use a quick hardcoded credential check.
    # You can later scale this to query a dedicated system_users table.
    if admin_id == "ADMIN" and password == "adminadmin":
        print("\n Access Granted. Welcome to the LTO Control Dashboard!")
        admin_main("LTO Admin Officer", conn)
    else:
        print("\n Invalid Personnel ID or Password. Access Denied.")

def sign_in_driver(conn):
    print("\n --- DRIVER ACCESS PORTAL ---")
    license_num = input("Enter License Number (e.g., N01-23-000001): ").strip()
    last_name_input = input("Enter Registered Last Name: ").strip().lower()

    try:
        cur = conn.cursor(dictionary=True)
        
        # Verify if the driver exists using a parameterized query
        query = """
            SELECT first_name, last_name, license_number 
            FROM driver 
            WHERE LOWER(license_number) = LOWER(%s) AND LOWER(last_name) = %s
        """
        cur.execute(query, (license_num, last_name_input))
        driver_record = cur.fetchone()
        cur.close()

        if driver_record:
            full_name = f"{driver_record['first_name']} {driver_record['last_name']}"
            verified_license = driver_record['license_number']
            
            print(f"\n Authentication Successful! Welcome back, {full_name}.")
            # Pass the name, unique license key, and connection instance down the wire
            driver_main(full_name, verified_license, conn)
        else:
            print("\n No match found for that License Number and Last Name combination.")
            print("   Please check your details or visit an LTO branch to register.")

    except mysql.connector.Error as err:
        print(f" Database error during authentication: {err}")

def signin_main(conn):
    while True:
        welcome_banner()
        choice = input("Enter your choice: ").strip()

        if choice == '1':
            sign_in_admin(conn)
        elif choice == '2':
            sign_in_driver(conn)
        elif choice == '0':
            print("\n Exiting system. Securing LTO Management database lines. Goodbye!\n")
            break
        else:
            print("\n Invalid option. Please select 1, 2, or 0.\n")