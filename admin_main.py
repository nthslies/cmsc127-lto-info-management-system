# admin_main.py
import mysql.connector
import re
from datetime import datetime
from tabulate import tabulate
from reports import (
    view_drivers_filtered, view_vehicles_by_owner, view_expired_registrations,
    view_invalid_licenses, view_driver_violations_by_date, 
    view_violation_distribution_by_year, view_violations_by_location
)

def admin_main(admin_name, conn):
    while True:
        print("\n" + "═"*62)
        print("║                 LTO ADMINISTRATIVE PANEL                     ║")
        print(f"║                     Welcome, {admin_name}!                   ║")
        print("═"*62)
        print("  [1] Register New Records (Driver / Vehicle / Violation)")
        print("  [2] Update Existing Records")
        print("  [3] Delete Records (With Cascade Restrictions)")
        print("  [4] Generate System Query Reports")
        print("  [0] Sign Out & Lock Lines")
        print("─"*62)

        choice = input("Enter option: ").strip()

        if choice == '1':
            add_menu(conn)
        elif choice == '2':
            update_menu(conn)
        elif choice == '3':
            delete_menu(conn)
        elif choice == '4':
            generate_reports_menu(conn)
        elif choice == '0':
            print("\n Admin session closed safely. Returning to main portal.\n")
            break
        else:
            print("\n Invalid input. Please choose a valid panel option.\n")

def generate_reports_menu(conn):
    cur = conn.cursor(dictionary=True)
    while True:
        print("\n%s [LTO Query Control] System Reports Dashboard" % " ")
        print("=" * 72)
        print("[1]  View registered drivers filtered by parameters")
        print("[2]  View all vehicles owned by a given driver")
        print("[3]  View all vehicles with expired registrations as of a date")
        print("[4]  View all drivers with expired or suspended licenses")
        print("[5]  View all traffic violations committed by a driver (Date Range)")
        print("[6]  View total number of violations per type for a given year")
        print("[7]  View all vehicles involved in violations within a city/region")
        print("[0]  Return to Admin Panel")
        print("=" * 72)
        
        report = input("Select the query report to generate: ").strip()

        try:
            if report == '1':
                view_drivers_filtered(cur)
            elif report == '2':
                last_name = input("Enter Driver's Registered Last Name: ").strip()
                view_vehicles_by_owner(cur, last_name)
            elif report == '3':
                target_date = input("Enter Cutoff Date (YYYY-MM-DD): ").strip()
                view_expired_registrations(cur, target_date)
            elif report == '4':
                view_invalid_licenses(cur)
            elif report == '5':
                lic_num = input("Enter Driver License Number: ").strip()
                start_d = input("Enter Start Date (YYYY-MM-DD): ").strip()
                end_d = input("Enter End Date (YYYY-MM-DD): ").strip()
                view_driver_violations_by_date(cur, lic_num, start_d, end_d)
            elif report == '6':
                target_year = input("Enter Assessment Year (YYYY): ").strip()
                view_violation_distribution_by_year(cur, target_year)
            elif report == '7':
                region = input("Enter City or Region keyword (e.g. Los Baños): ").strip()
                view_violations_by_location(cur, region)
            elif report == '0':
                break
            else:
                print("⚠️ Selection unrecognized.")
        except mysql.connector.Error as err:
            print(f"⚠️ Query Error: {err}")
            
    cur.close()

# ═════════════════════════════════════════════════════════════════════
#  RECORD MANAGEMENT INSERTION MENU & AUTO-ID GENERATION (CRUD Step 1)
# ═════════════════════════════════════════════════════════════════════
def add_menu(conn):
    while True:
        print("\n [Record Management] Insertion Panel")
        print("  [1] Register New Driver")
        print("  [2] Register New Vehicle")
        print("  [3] Record New Traffic Violation Apprehension")
        print("  [0] Back")
        choice = input("Select operation (0-3): ").strip()

        if choice == '1':
            register_driver(conn)
        elif choice == '2':
            register_vehicle(conn)
        elif choice == '3':
            record_real_world_apprehension(conn)
        elif choice == '0':
            break
        else:
            print(" Invalid choice. Select 0, 1, 2, or 3.")

def get_next_registration_number(conn):
    cur = conn.cursor()
    cur.execute("SELECT registration_number FROM registration ORDER BY registration_number DESC LIMIT 1;")
    result = cur.fetchone()
    cur.close()
    if result:
        try:
            last_num = int(result[0].split('-')[1])
            return f"REG-{last_num + 1:03d}"
        except:
            return "REG-026"
    return "REG-001"

def register_driver(conn):
    print("\n --- Register New Driver Profile ---")
    lic_num = input("License Number (e.g., N01-24-000099): ").strip()
    if not lic_num:
        print(" License Number cannot be empty.")
        return

    cur = conn.cursor()
    cur.execute("SELECT license_number FROM driver WHERE license_number = %s", (lic_num,))
    if cur.fetchone():
        print(" Pre-flight Gate: Driver record already exists!")
        cur.close()
        return
    cur.close()

    f_name = input("First Name: ").strip() or "Unknown"
    m_name = input("Middle Name (Optional): ").strip() or None
    l_name = input("Last Name: ").strip() or "Unknown"
    dob = input("Date of Birth (YYYY-MM-DD): ").strip() or "2000-01-01"
    sex = input("Sex (M/F): ").strip().upper() or "M"
    addr = input("Complete Home Address: ").strip() or "Not Specified"
    exp = input("License Expiry Date (YYYY-MM-DD): ").strip() or "2031-01-01"
    l_type = input("Type (Student Permit/Non-Professional/Professional): ").strip() or "Non-Professional"
    l_stat = input("Status (Active/Expired/Suspended/Revoked): ").strip() or "Active"

    try:
        cur = conn.cursor()
        query = """INSERT INTO driver (license_number, first_name, middle_name, last_name, date_of_birth, sex, address, expiry_date, license_type, license_status) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
        cur.execute(query, (lic_num, f_name, m_name, l_name, dob, sex, addr, exp, l_type, l_stat))
        conn.commit()
        print(" Driver profile saved successfully.")
        cur.close()
    except mysql.connector.Error as err:
        print(f" DB Error: {err}")

def register_vehicle(conn):
    print("\n --- Register New Motor Vehicle ---")
    lic_num = input("Owner's License Number Link: ").strip()

    cur = conn.cursor()
    cur.execute("SELECT first_name, last_name FROM driver WHERE license_number = %s", (lic_num,))
    driver = cur.fetchone()
    cur.close()

    if not driver:
        print(f" Pre-flight Error: Driver license '{lic_num}' is not registered!")
        return

    plate = input("Plate Number: ").strip()
    if not plate: return
    engine = input("Engine Number: ").strip() or "ENG-GENERIC"
    chassis = input("Chassis Number: ").strip() or "CHS-GENERIC"
    v_type = input("Vehicle Type: ").strip() or "Sedan"
    make = input("Manufacturer/Make: ").strip() or "Toyota"
    model = input("Model: ").strip() or "Vios"
    
    year_input = input("Year of Manufacture (YYYY): ").strip()
    year = int(year_input) if (year_input.isdigit() and len(year_input) == 4) else 2026

    color = input("Color: ").strip() or "Black"
    
    print("\nSelect Vehicle Classification:")
    print(" [1] Private Car\n [2] For-Hire / PUV (Commercial)")
    class_choice = input("Choice (1-2): ").strip()
    v_class = "For-Hire/PUV" if class_choice == '2' else "Private"
    franchise = input("Enter LTFRB Franchise Token Number (or press Enter if Private): ").strip() or None if class_choice == '2' else None

    try:
        cur = conn.cursor()
        v_query = "INSERT INTO vehicle (plate_number, engine_number, chassis_number, vehicle_type, make, model, year, color, license_number, vehicle_classification, ltfrb_franchise_number) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        cur.execute(v_query, (plate, engine, chassis, v_type, make, model, year, color, lic_num, v_class, franchise))
        
        auto_reg_id = get_next_registration_number(conn)
        r_query = "INSERT INTO registration (registration_number, registration_status, registration_date, expiration_date, plate_number) VALUES (%s, 'Active', CURRENT_DATE, DATE_ADD(CURRENT_DATE, INTERVAL 1 YEAR), %s)"
        cur.execute(r_query, (auto_reg_id, plate))
        
        conn.commit()
        print(f" Vehicle registry finalized. Auto-generated Registration ID: {auto_reg_id}")
        cur.close()
    except mysql.connector.Error as err:
        print(f" System rejected database transaction: {err}")

def record_new_apprehension(conn):
    print("\n --- LTO OFFICIAL APPREHENSION LOGGING GATE ---")
    lic_num = input("Enter Driver License Number: ").strip()

    # Pre-flight check: Verify driver exists and fetch current standing
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT first_name, last_name, accumulated_demerit_points, license_status FROM driver WHERE license_number = %s", (lic_num,))
    driver = cur.fetchone()
    
    if not driver:
        print(f" Entry Aborted: Driver License '{lic_num}' does not exist in registry database.")
        cur.close()
        return

    print(f" Driver Found: {driver['first_name']} {driver['last_name']} (Current Points: {driver['accumulated_demerit_points']})")

    # Display clean master codes so admin is never confused
    print("\nMaster Infraction Codes:")
    print("  [V_DOCS]  Documentation Omission    [V_CHILD] Child Motorcycle Hazard")
    print("  [V_DIST]  Distracted Driving         [V_SGEAR] Safety Gear Non-Compliance")
    print("  [V_ENVIR] Environmental Omission    [V_CARE]  Careless Driving / Lane Error")
    print("  [V_TURN]  Improper Turning / Sign    [V_CARGO] Insecure Cargo Securement")
    print("  [V_PUV]   PUV Franchise Abuse        [V_REGIS] Unregistered MV / Colorum")
    print("  [V_DUI]   Driving Under Influence    [V_FRAUD] Counterfeit Papers / Crime")
    
    v_code = input("\nEnter Infraction Code from ticket: ").strip().upper()
    cur.execute("SELECT * FROM violationType WHERE violation_code = %s", (v_code,))
    v_type = cur.fetchone()

    if not v_type:
        print(" Entry Aborted: Unrecognized Infraction Code.")
        cur.close()
        return

    # ═════════════════════════════════════════════════════════════════
    #  THE SYSTEMATIC OFFENSE COUNTING ALGORITHM
    # ═════════════════════════════════════════════════════════════════
    
    # Count how many times this specific driver has committed this specific infraction code via the new schema link
    count_query = """
        SELECT COUNT(*) AS historic_count FROM violation 
        WHERE license_number = %s AND violation_code = %s
    """
    cur.execute(count_query, (lic_num, v_code))
    past_offenses = cur.fetchone()['historic_count']
    current_offense_number = past_offenses + 1  # Automatic tracking pointer

    # Determine base values from the master lookup configuration
    base_points = int(v_type['demerit_points'])
    base_fine = float(v_type['fine_amount'])
    tier_label = v_type['severity_category']
    
    assigned_points = base_points
    assigned_fine = base_fine

    # Apply RA 10930 graduated scaling rule sets dynamically based on offense number history
    if v_code in ['V_DOCS', 'V_CHILD', 'V_DIST', 'V_SGEAR', 'V_ENVIR', 'V_CARE', 'V_TURN']:
        if current_offense_number == 1:
            assigned_points = 1
            tier_label = "Light"
        elif current_offense_number == 2:
            assigned_points = 3
            tier_label = "Less Grave"
        else:
            assigned_points = 5
            tier_label = "Grave (Habitual Repeat Violator)"
            
    elif v_code in ['V_CARGO', 'V_PUV']:
        if current_offense_number == 1:
            assigned_points = 3
            tier_label = "Less Grave"
        else:
            assigned_points = 5
            tier_label = "Grave (Habitual Repeat Violator)"

    print(f"\n⚡ Point Assessment Dashboard:")
    print(f"   Detected Tracking: {v_type['violation_name']} -> Offense #{current_offense_number}")
    print(f"   Assigned Tier    : {tier_label} | Demerit Points: +{assigned_points}")
    print(f"   Assessed Penalty : ₱{assigned_fine:,.2f}")

    location = input("Enter Apprehension Location (City/Municipality): ").strip() or "Not Specified"
    plate = input("Enter Apprehension Vehicle Plate Number: ").strip().upper()

    # Dynamic execution sequence to finalize the ticket entry
    cur.close()
    cur = conn.cursor()
    cur.execute("SELECT COALESCE(MAX(violation_id), 0) + 1 FROM violation;")
    next_id = cur.fetchone()[0]

    try:
        # 1. Write the new ticket log into the violation infrastructure table
        query = """
            INSERT INTO violation (violation_id, violation_date, location, violation_status, license_number, plate_number, violation_code) 
            VALUES (%s, CURRENT_DATE, %s, 'Unpaid', %s, %s, %s)
        """
        cur.execute(query, (next_id, location, lic_num, plate, v_code))
        
        # 2. Update point aggregates inside master driver registry row
        cur.execute(
            "UPDATE driver SET accumulated_demerit_points = accumulated_demerit_points + %s WHERE license_number = %s",
            (assigned_points, lic_num)
        )

        # 3. Enforce automated license suspension thresholds (10 Points)
        new_total = driver['accumulated_demerit_points'] + assigned_points
        if new_total >= 10:
            cur.execute("UPDATE driver SET license_status = 'Suspended' WHERE license_number = %s", (lic_num,))
            print(f"\n AUTOMATED SYSTEM ENFORCEMENT TRIGGERED:")
            print(f"   Driver hit {new_total} accumulated points. License status set to 'Suspended'.")

        conn.commit()
        print(f"\n Apprehension data successfully committed. Saved under Ticket ID: {next_id}")

    except mysql.connector.Error as err:
        conn.rollback()
        print(f" Entry Rejected: Database rollback executed due to error: {err}")
    finally:
        cur.close()

def record_real_world_apprehension(conn):
    print("\n --- ENTERING REAL-WORLD LTO ENFORCEMENT PORTAL ---")
    lic_num = input("Enter Driver License Number: ").strip()
    plate = input("Enter Apprehended Vehicle Plate Number: ").strip().upper()

    cur = conn.cursor(dictionary=True)
    
    # 1. Pre-flight verification check
    cur.execute("SELECT first_name, last_name, license_type, license_status FROM driver WHERE license_number = %s", (lic_num,))
    driver = cur.fetchone()
    cur.execute("SELECT license_number AS owner_license, vehicle_classification, make, model FROM vehicle WHERE plate_number = %s", (plate,))
    vehicle = cur.fetchone()

    if not driver or not vehicle:
        print(" Data Mismatch Error: Verified Driver or Vehicle asset registry link not found.")
        cur.close()
        return

    # Check the dynamic ledger table to compute historical active points
    cur.execute("SELECT COALESCE(SUM(points_changed), 0) AS active_points FROM demerit_ledger WHERE license_number = %s", (lic_num,))
    previous_points = cur.fetchone()['active_points']

    # 2. Collect violation code mapping data
    v_code = input("Enter Infraction Code (e.g., V_CARE, V_DUI): ").strip().upper()
    cur.execute("SELECT * FROM violationType WHERE violation_code = %s", (v_code,))
    v_type = cur.fetchone()

    if not v_type:
        print(" Entry Aborted: Unrecognized Infraction Code.")
        cur.close()
        return

    # Calculate dynamic offense counting history via clean logs
    cur.execute("SELECT COUNT(*) AS past_count FROM violation WHERE license_number = %s AND violation_code = %s", (lic_num, v_code))
    past_offenses = cur.fetchone()['past_count']
    current_offense_number = past_offenses + 1

    # Apply RA 10930 Core Demerit Point math rules
    assigned_points = int(v_type['demerit_points'])
    assigned_fine = float(v_type['fine_amount'])
    tier_label = v_type['severity_category']

    # Escalation Rules based on repeat offenses
    if v_code in ['V_DOCS', 'V_CHILD', 'V_DIST', 'V_SGEAR', 'V_ENVIR', 'V_CARE', 'V_TURN'] and current_offense_number == 2:
        assigned_points = 3
        tier_label = "Less Grave"
    elif current_offense_number >= 3:
        assigned_points = 5
        tier_label = "Grave"

    # Apply Section 12 double demerit escalator if vehicle is PUV/For-Hire
    double_escalator = 'N'
    if vehicle['vehicle_classification'] == 'For-Hire/PUV':
        assigned_points *= 2
        double_escalator = 'Y'

    location = input("Enter Apprehension Location: ").strip()
    print("Select Apprehending Authority Unit Agency:\n [1] LTO_MAIN  [2] MMDA_01  [3] LGU_LB")
    ag_choice = input("Choice: ").strip()
    agency_code = "LTO_MAIN" if ag_choice == '1' else ("MMDA_01" if ag_choice == '2' else "LGU_LB")

    # Get next sequential ID pointer
    cur.close()
    cur = conn.cursor()
    cur.execute("SELECT COALESCE(MAX(violation_id), 0) + 1 FROM violation;")
    next_id = cur.fetchone()[0]

    try:
        # Commit to the core database tables
        cur.execute(
            "INSERT INTO violation (violation_id, violation_date, location, violation_status, license_number, plate_number, violation_code, double_points_applied, agency_code) VALUES (%s, CURRENT_DATE, %s, 'Unpaid', %s, %s, %s, %s, %s)",
            (next_id, location, lic_num, plate, v_code, double_escalator, agency_code)
        )
        cur.execute(
            "INSERT INTO demerit_ledger (license_number, violation_id, points_changed, transaction_date, reason) VALUES (%s, %s, %s, CURRENT_DATE, 'Traffic Citation Apprehension')",
            (lic_num, next_id, assigned_points)
        )
        
        # Keep the quick driver aggregate summary counter column completely updated
        cur.execute("UPDATE driver SET accumulated_demerit_points = accumulated_demerit_points + %s WHERE license_number = %s", (assigned_points, lic_num))

        # Check for immediate threshold suspension requirements (10 points)
        new_total_points = previous_points + assigned_points
        updated_status = driver['license_status']
        if new_total_points >= 10:
            cur.execute("UPDATE driver SET license_status = 'Suspended' WHERE license_number = %s", (lic_num,))
            updated_status = "Suspended"

        conn.commit()
        print(f"\n Real-world log committed successfully. Ticket ID: {next_id}")

        # ═════════════════════════════════════════════════════════════════
        # GENERATING REAL-TIME TRANSACTION RECEIPT ROW DATA
        # ═════════════════════════════════════════════════════════════════
        cur.close()
        cur = conn.cursor(dictionary=True)
        
        receipt_query = """
            SELECT 
                d.license_number,
                CONCAT(d.first_name, ' ', d.last_name) AS driver_name,
                d.license_type,
                %s AS current_license_status,
                v.violation_id AS ticket_id,
                vt.violation_name,
                v.plate_number,
                v.location AS apprehension_location,
                v.double_points_applied AS puv_escalator,
                vt.fine_amount AS ticket_fine,
                %s AS ticket_demerit_points,
                %s AS total_accumulated_points
            FROM violation v
            JOIN driver d ON v.license_number = d.license_number
            JOIN violationType vt ON v.violation_code = vt.violation_code
            WHERE v.violation_id = %s
        """
        cur.execute(receipt_query, (updated_status, assigned_points, new_total_points, next_id))
        receipt_data = cur.fetchall()
        
        print("\n --- LTO TRANSACTION Apprehension Receipt Summary Row ---")
        print(tabulate(receipt_data, headers="keys", tablefmt="grid"))
        
        if new_total_points >= 10:
            print(f" AUTOMATED SYSTEM ACTION: License status escalated to 'Suspended' due to point overload.")

    except mysql.connector.Error as err:
        conn.rollback()
        print(f" Transaction Refused by Database: {err}")
    finally:
        cur.close()

# ═════════════════════════════════════════════════════════════════════
# RECORD MANAGEMENT DYNAMIC UPDATE MENU (CRUD Step 2)
# ═════════════════════════════════════════════════════════════════════
def update_menu(conn):
    while True:
        print("\n [Record Management] Modification Panel")
        print("  [1] Modify Driver Complete Profile")
        print("  [2] Update Vehicle Registration Info")
        print("  [0] Back")
        
        # Clarified prompt here to avoid confusing choices with target license IDs!
        choice = input("Select update operation choice (0-2): ").strip()

        if choice == '1':
            update_driver_profile(conn)
        elif choice == '2':
            update_vehicle_registration(conn)
        elif choice == '0':
            break
        else:
            print(" Invalid menu selection. Please select 1, 2, or 0.")

def update_driver_profile(conn):
    print("\n --- Modify Driver Profile (Press Enter to Skip) ---")
    lic_num = input("Enter Target Driver License Number: ").strip()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM driver WHERE license_number = %s", (lic_num,))
        driver = cur.fetchone()
        cur.close()
        if not driver: return

        f_name = input(f"New First Name [{driver['first_name']}]: ").strip() or driver['first_name']
        m_name = input(f"New Middle Name [{driver['middle_name']}]: ").strip() or driver['middle_name']
        l_name = input(f"New Last Name [{driver['last_name']}]: ").strip() or driver['last_name']
        addr = input(f"New Address [{driver['address']}]: ").strip() or driver['address']
        l_type = input(f"New License Type [{driver['license_type']}]: ").strip() or driver['license_type']
        l_stat = input(f"New License Status [{driver['license_status']}]: ").strip() or driver['license_status']

        cur = conn.cursor()
        cur.execute("UPDATE driver SET first_name=%s, middle_name=%s, last_name=%s, address=%s, license_type=%s, license_status=%s WHERE license_number=%s", (f_name, m_name, l_name, addr, l_type, l_stat, lic_num))
        conn.commit()
        print(" Updated successfully.")
        cur.close()
    except mysql.connector.Error as err: print(f" Error: {err}")

def update_vehicle_registration(conn):
    print("\n --- Update Vehicle Registration ---")
    plate = input("Enter Target Vehicle Plate Number: ").strip()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM registration WHERE plate_number = %s ORDER BY expiration_date DESC LIMIT 1", (plate,))
        reg = cur.fetchone()
        cur.close()
        if not reg: return

        new_date = input(f"New Expiration Date [{reg['expiration_date']}]: ").strip() or reg['expiration_date']
        new_status = input(f"New Status [{reg['registration_status']}]: ").strip() or reg['registration_status']

        cur = conn.cursor()
        cur.execute("UPDATE registration SET expiration_date = %s, registration_status = %s WHERE registration_number = %s", (new_date, new_status, reg['registration_number']))
        conn.commit()
        print(" Timeline refreshed successfully.")
        cur.close()
    except mysql.connector.Error as err: print(f" Error: {err}")

# ═════════════════════════════════════════════════════════════════════
# RECORD MANAGEMENT DELETION WORKFLOWS WITH CASCADE PROTECT (CRUD Step 3)
# ═════════════════════════════════════════════════════════════════════
def delete_menu(conn):
    while True:
        print("\n [Record Management] Removal Panel")
        print("  [1] Remove Driver Record")
        print("  [2] Remove Registered Vehicle")
        print("  [0] Back")
        choice = input("Select removal target choice (0-2): ").strip()
        if choice == '1': delete_driver(conn)
        elif choice == '2': delete_vehicle(conn)
        elif choice == '0': break

def delete_driver(conn):
    print("\n --- Remove Driver Record ---")
    lic_num = input("Enter Driver License Number to DELETE: ").strip()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM vehicle WHERE license_number = %s", (lic_num,))
        v_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM violation WHERE license_number = %s", (lic_num,))
        viol_count = cur.fetchone()[0]
        cur.close()

        if v_count > 0 or viol_count > 0:
            print("\n🚨 CRITICAL WARNING: Deleting this driver will break relational database links!")
            return

        confirm = input(f"\nAre you sure you want to permanently delete driver {lic_num}? (YES/NO): ").strip().upper()
        if confirm == 'YES':
            cur = conn.cursor()
            cur.execute("DELETE FROM driver WHERE license_number = %s", (lic_num,))
            conn.commit()
            print(" Driver record purged cleanly.")
            cur.close()
    except mysql.connector.Error as err: print(f"❌ Error: {err}")

def delete_vehicle(conn):
    print("\n --- Remove Registered Vehicle ---")
    plate = input("Enter Vehicle Plate Number to DELETE: ").strip()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM registration WHERE plate_number = %s", (plate,))
        r_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM violation WHERE plate_number = %s", (plate,))
        v_count = cur.fetchone()[0]
        cur.close()

        confirm = input(f"Confirm permanent removal of asset {plate}? (YES/NO): ").strip().upper()
        if confirm == 'YES':
            cur = conn.cursor()
            cur.execute("DELETE FROM registration WHERE plate_number = %s", (plate,))
            cur.execute("DELETE FROM vehicle WHERE plate_number = %s", (plate,))
            conn.commit()
            print(" Vehicle asset structural registration destroyed completely.")
            cur.close()
    except mysql.connector.Error as err: print(f" Error: {err}")