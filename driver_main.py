# driver_main.py
import mysql.connector
from tabulate import tabulate
from datetime import datetime

def get_validated_menu_choice(prompt, valid_options):
    """Enforces rigorous menu boundaries to block junk inputs or crashes."""
    while True:
        choice = input(prompt).strip()
        if choice in valid_options:
            return choice
        print(f" Validation Error: Selection unrecognized. Please choose from {valid_options}.")

def view_profile(license_number, conn):
    print("\n --- MY LTO DRIVER PROFILE ---")
    try:
        cur = conn.cursor(dictionary=True)
        # Compute real-time point ledger summaries directly via SQL math
        cur.execute("SELECT COALESCE(SUM(points_changed), 0) AS active_points FROM demerit_ledger WHERE license_number = %s", (license_number,))
        active_points = cur.fetchone()['active_points']

        query = "SELECT license_number, license_type, license_status, expiry_date, address, sex FROM driver WHERE license_number = %s"
        cur.execute(query, (license_number,))
        profile = cur.fetchone()
        cur.close()

        if profile:
            data = [[k.replace('_', ' ').title(), v] for k, v in profile.items()]
            data.append(["Active Demerit Points Balance", active_points])
            print(tabulate(data, headers=["Profile Parameter", "Registered Value"], tablefmt="grid"))
        else:
            print(" System Error: Profile not found in the central registry.")
    except mysql.connector.Error as err:
        print(f" Database Retrieval Failure: {err}")

def driver_main(driver_name, license_number, conn):
    while True:
        print("\n" + "═"*62)
        print(f"║   DRIVER PERSONAL RECOGNITION WORKSPACE                     ║")
        print(f"║    Welcome, {driver_name:<46} ║")
        print(f"║    License: {license_number:<46} ║")
        print("═"*62)
        print(" [1]  View My Profile Details")
        print(" [2]  View My Registered Vehicles")
        print(" [3]  View My Traffic Violations & Ticket History")
        print(" [4]  Settle Outstanding Citation Fines (Online Payment)")
        print(" [5]  Process Self-Service License Renewal")
        print(" [0]  Sign Out & Disconnect")
        print("─"*62)

        choice = get_validated_menu_choice("Select an option to view: ", ['1', '2', '3', '4', '5', '0'])

        if choice == '1':
            view_profile(license_number, conn)
        elif choice == '2':
            view_my_vehicles(license_number, conn)
        elif choice == '3':
            view_my_violations(license_number, conn)
        elif choice == '4':
            settle_fines_online(license_number, conn)
        elif choice == '5':
            driver_self_renewal(license_number, conn)
        elif choice == '0':
            print("\n Driver workspace closed safely. Disconnecting central registry lines.")
            break

def view_my_vehicles(license_number, conn):
    print("\n --- MY REGISTERED MOTOR VEHICLES ---")
    try:
        cur = conn.cursor(dictionary=True)
        query = """
            SELECT v.plate_number, v.make, v.model, v.year, v.color, r.registration_status, r.expiration_date, v.vehicle_classification
            FROM vehicle v
            LEFT JOIN registration r ON v.plate_number = r.plate_number
            WHERE v.license_number = %s
        """
        cur.execute(query, (license_number,))
        vehicles = cur.fetchall()
        cur.close()

        if vehicles:
            print(tabulate(vehicles, headers="keys", tablefmt="grid"))
        else:
            print(" You do not have any motor vehicles registered under this license number.")
    except mysql.connector.Error as err:
        print(f" Database Retrieval Failure: {err}")

def view_my_violations(license_number, conn):
    print("\n --- MY TRAFFIC CITATIONS & OUTSTANDING FINES ---")
    try:
        cur = conn.cursor(dictionary=True)
        query = """
            SELECT v.violation_id, vt.violation_name, v.violation_date, v.location, vt.fine_amount, v.violation_status
            FROM violation v
            JOIN violationType vt ON v.violation_code = vt.violation_code
            WHERE v.license_number = %s
            ORDER BY v.violation_date DESC
        """
        cur.execute(query, (license_number,))
        violations = cur.fetchall()
        cur.close()

        if violations:
            print(tabulate(violations, headers="keys", tablefmt="grid"))
        else:
            print(" Clean Record! No traffic violations are associated with this license number.")
    except mysql.connector.Error as err:
        print(f" Database Retrieval Failure: {err}")

def settle_fines_online(license_number, conn):
    print("\n --- ONLINE CITATION FARE SETTLEMENT PORTAL ---")
    try:
        cur = conn.cursor(dictionary=True)
        query = """
            SELECT v.violation_id, vt.violation_name, vt.fine_amount 
            FROM violation v 
            JOIN violationType vt ON v.violation_code = vt.violation_code 
            WHERE v.license_number = %s AND v.violation_status = 'Unpaid'
        """
        cur.execute(query, (license_number,))
        unpaid_tickets = cur.fetchall()
        
        if not unpaid_tickets:
            print(" Balance Clean! You have no outstanding unpaid citations.")
            cur.close()
            return

        print(tabulate(unpaid_tickets, headers="keys", tablefmt="grid"))
        total_fines = sum(float(ticket['fine_amount']) for ticket in unpaid_tickets)
        print(f" Total Amount Due for Online Payment: ₱{total_fines:,.2f}")
        
        confirm = get_validated_menu_choice("\nProceed to pay all outstanding fines via electronic channel? (YES/NO): ", ['YES', 'NO', 'yes', 'no']).upper()
        if confirm == 'YES':
            cur.close()
            cur = conn.cursor()
            # Clear outstanding financial blocks cleanly
            cur.execute("UPDATE violation SET violation_status = 'Paid' WHERE license_number = %s AND violation_status = 'Unpaid'", (license_number,))
            conn.commit()
            print("\n [PAYMENT SUCCESSFUL]: All fines settled. Your financial liabilities are cleared!")
        else:
            print(" Transaction cancelled by user.")
            cur.close()
    except mysql.connector.Error as err:
        print(f" Payment Transaction Processing Aborted: {err}")

def driver_self_renewal(license_number, conn):
    print(f"\n --- SELF-SERVICE LICENSE RENEWAL VERIFICATION GATE ---")
    
    if not conn:
        print(" System Error: Central database lines are unstable.")
        return False

    cur = conn.cursor(dictionary=True)

    try:
        # GATE 1: Unpaid Citations Financial Block Check
        cur.execute("SELECT COUNT(*) AS unpaid_count FROM violation WHERE license_number = %s AND violation_status = 'Unpaid'", (license_number,))
        unpaid_tickets = cur.fetchone()['unpaid_count']

        if unpaid_tickets > 0:
            print(f" RENEWAL DENIED: You have {unpaid_tickets} unsettled traffic citations.")
            print("   [CRITICAL SYSTEM BLOCK]: Navigate to option [4] to settle outstanding fines first.")
            cur.close()
            return False

        # GATE 2: Demerit Point Accumulation Scale Ledger Check
        cur.execute("SELECT COALESCE(SUM(points_changed), 0) AS active_points FROM demerit_ledger WHERE license_number = %s", (license_number,))
        active_points = cur.fetchone()['active_points']
        print(f" System Audit: Your current active demerit balance is {active_points} point(s).")

        if active_points >= 10:
            print("  RENEWAL LOCKOUT: You have accumulated 10 or more demerit points.")
            print("   [RA 10930 Section 14]: You must visit an LTO branch to complete mandatory examinations.")
            cur.close()
            return False

        #  SCAN HISTORIC OFFENSES FOR PROHIBITION (Loophole Protection)
        # We find the highest point category accumulated from actual tickets within the last 12 months,
        # completely ignoring whether a renewal reset row has occurred.
        cur.execute("""
            SELECT MAX(transaction_date) AS last_settlement_date, 
                   COALESCE(SUM(points_changed), 0) AS total_historic_points
            FROM demerit_ledger 
            WHERE license_number = %s AND reason = 'Traffic Citation Apprehension'
              AND transaction_date >= DATE_SUB(CURRENT_DATE, INTERVAL 12 MONTH)
        """, (license_number,))
        history = cur.fetchone()

        last_settlement = history['last_settlement_date']
        historic_points = history['total_historic_points']

        print("\nSelect Desired Transaction Type:")
        print(" [1] Standard Validity Renewal")
        print(" [2] Upgrade Classification / Add restriction codes")
        tx_type = get_validated_menu_choice("Select choice (1-2): ", ['1', '2'])

        if tx_type == '2':
            # Map prohibition duration criteria against their true historical infraction footprint
            month_interval = 0
            if 1 <= historic_points <= 2: month_interval = 3
            elif 3 <= historic_points <= 4: month_interval = 6
            elif historic_points >= 5: month_interval = 12

            if month_interval > 0 and last_settlement:
                # Standardize last_settlement variable type instantly to completely fix the formatting crash
                if isinstance(last_settlement, str):
                    last_settlement = datetime.strptime(last_settlement, "%Y-%m-%d").date()

                # Dynamic SQL Date engine calculation tracking wait-time matrices on the fly
                prohibition_query = """
                    SELECT 
                        DATEDIFF(DATE_ADD(%s, INTERVAL %s MONTH), CURRENT_DATE) AS days_remaining,
                        DATE_ADD(%s, INTERVAL %s MONTH) AS raw_lift_date
                    FROM DUAL;
                """
                cur.execute(prohibition_query, (last_settlement, month_interval, last_settlement, month_interval))
                date_math = cur.fetchone()

                # If days remaining is positive, block the path regardless of active_points being 0!
                if date_math and date_math['days_remaining'] > 0:
                    raw_lift = date_math['raw_lift_date']
                    # Standardize lift date string variable conversion type securely
                    if isinstance(raw_lift, str):
                        raw_lift = datetime.strptime(raw_lift, "%Y-%m-%d").date()

                    clean_settlement = last_settlement.strftime("%A, %B %d, %Y")
                    clean_lift = raw_lift.strftime("%A, %B %d, %Y")

                    print(f"\n TRANSACTION DENIED: Upgrade blocked due to Section 17 Period of Prohibition.")
                    print(f"    --- LTO ENFORCEMENT TEMPORAL AUDIT ---")
                    print(f"   - Historical Points Logged   : {historic_points} demerit point(s)")
                    print(f"   - Prescribed Penalty Scale   : {month_interval} Months Absolute Wait-Time")
                    print(f"   - Last Citation Settlement   : {clean_settlement}")
                    print(f"   - Processing Lift Date       : {clean_lift}")
                    print(f"   - Waiting Time Remaining     : {date_math['days_remaining']} day(s) left")
                    print(f"   ----------------------------------------")
                    print("    System Action: Upgrade choices are locked until the lift date passes.")
                    cur.close()
                    return False

        # CLEARANCE PHASE: Execute points reset offset to zero out values safely
        cur.close()
        cur = conn.cursor()
        if tx_type == '1' and active_points > 0:
            cur.execute("INSERT INTO demerit_ledger (license_number, violation_id, points_changed, transaction_date, reason) VALUES (%s, NULL, %s, CURRENT_DATE, 'License Renewal Reset')", (license_number, -active_points))

        # Re-verify and clear out the points metrics attributes values securely
        cur.execute("""
            UPDATE driver 
            SET expiry_date = DATE_ADD(CURRENT_DATE, INTERVAL 5 YEAR), 
                license_status = 'Active', 
                accumulated_demerit_points = 0 
            WHERE license_number = %s
        """, (license_number,))
        conn.commit()
        print("\n SUCCESS: Transaction processed via online channel! Registry updated successfully.")
        cur.close()
        return True

    except mysql.connector.Error as err:
        if conn: conn.rollback()
        print(f" Database Transaction Error: {err}")
        return False
    except Exception as e:
        print(f" An unexpected validation error occurred: {e}")
        return False