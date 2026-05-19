# main.py
from connect import database
from signin import signin_main

def start_program():
    # 1. Initialize DB connection and run schema script if empty
    conn, cursor = database()
    
    if conn and conn.is_connected():
        # 2. Hand over execution control to the sign-in hub
        signin_main(conn)
        
        # 3. Clean closure when exiting the sign-in loop
        cursor.close()
        conn.close()
    else:
        print(" Critical System Error: Unable to establish database backbone connection.")

if __name__ == "__main__":
    start_program()