# admin_main.py
import mysql.connector
import re
import time
from datetime import datetime, date
from tabulate import tabulate

from reports import (
    view_drivers_filtered, view_vehicles_by_owner, view_expired_registrations,
    view_invalid_licenses, view_driver_violations_by_date, 
    view_violation_distribution_by_year, view_violations_by_location,
    is_invalid_license_format, is_invalid_date_format, is_invalid_year_format
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
                license_number = input("Enter Driver's License Number: ").strip()
                view_vehicles_by_owner(cur, license_number)
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
                print(" Selection unrecognized.")
        except mysql.connector.Error as err:
            print(f" Query Error: {err}")
            
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
    try:
        query = """
            SELECT COALESCE(MAX(CAST(SUBSTRING_INDEX(registration_number, '-', -1) AS UNSIGNED)), 0) AS max_num 
            FROM registration;
        """
        cur.execute(query)
        result = cur.fetchone()
        
        if result and result[0] is not None:
            next_num = int(result[0]) + 1
        else:
            next_num = 1
        
        return f"REG-{str(next_num).zfill(3)}"
        
    except Exception as e:
        print(f" System Warning: Registry auto-sequence anomaly detected ({e}). Utilizing emergency fallback timestamp.")
        emergency_stamp = int(time.time())
        return f"REG-{emergency_stamp}"
    finally:
        cur.close()

def register_driver(conn):
    print("\n --- Register New Driver Profile ---")
    lic_num = input("License Number (e.g., N01-24-000099): ").strip()
    if not lic_num:
        print(" Input Error: License Number cannot be empty.")
        return
    if is_invalid_license_format(lic_num):
        return

    # FORMAT GATE: Validates calendar format layout immediately
    dob_input = input("Date of Birth (YYYY-MM-DD): ").strip()
    if is_invalid_date_format(dob_input): 
        return

    dob_date = datetime.strptime(dob_input, "%Y-%m-%d").date()

    # age limit for student's driver license (must be 16 at least for a license)
    current_date = date.today()
    calculated_age = current_date.year - dob_date.year - ((current_date.month, current_date.day) < (dob_date.month, dob_date.day))
    if calculated_age < 16:
        print(f" Registration Blocked: Applicant is only {calculated_age} years old. Minimum LTO age requirement is 16.")
        return    

    sex = input("Sex (M/F): ").strip().upper()
    if sex not in ['M', 'F']:
        print(" Input Error: Sex parameter choice option must be exactly M or F.")
        return

    # ═════════════════════════════════════════════════════════════════
    # 🖩 AUTOMATED LICENSE EXPRATION CALCULATOR GATE
    # ═════════════════════════════════════════════════════════════════
    print("\nSelect License Classification:")
    print(" [1] Student Permit\n [2] Non-Professional\n [3] Professional")
    type_choice = input("Choice (1-3): ").strip()

    if type_choice not in ['1', '2', '3']:
        print(" Input Error: Selection unrecognized. Operation aborted.")
        return

    if type_choice == '1':
        l_type = "Student Permit"
        # student permits expire exactly 1 year from today's registration processing date
        exp_date = date(current_date.year + 1, current_date.month, current_date.day)
    else:
        l_type = "Professional" if type_choice == '3' else "Non-Professional"
        # pro/non-Pro cards expire exactly 5 years from the next birth anniversary cycle
        # target the birth month/day 5 years into the future
        target_year = current_date.year + 5
        try:
            exp_date = date(target_year, dob_date.month, dob_date.day)
        except ValueError:
            # handle the rare leap year edge case (Feb 29 birthday) safely shifting to Feb 28
            exp_date = date(target_year, 2, 28)

    # transform calculated date objects back into SQL-ready strings
    exp_input = exp_date.strftime("%Y-%m-%d")

    # pre-flight database check: prevents primary key duplicates
    cur = conn.cursor()
    cur.execute("SELECT license_number FROM driver WHERE license_number = %s", (lic_num,))
    if cur.fetchone():
        print("Pre-flight Gate: Driver record already exists inside registry!")
        cur.close()
        return
    cur.close()

    # Collect remaining details safely
    f_name = input("First Name: ").strip()
    if not f_name or f_name.isdigit():
        print(" Input Error: First name cannot be empty or strictly numeric.")
        return

    m_name = input("Middle Name (Optional): ").strip() or None

    l_name = input("Last Name: ").strip()
    if not l_name or l_name.isdigit():
        print(" Input Error: Last name cannot be empty.")
        return

    addr = input("Complete Home Address: ").strip()
    if not addr:
        print(" Input Error: Operational address field is required.")
        return
    
    l_stat = input("Status (Active/Expired/Suspended): ").strip() or "Active"

    try:
        cur = conn.cursor()
        query = """INSERT INTO driver (license_number, first_name, middle_name, last_name, date_of_birth, sex, address, expiry_date, license_type, license_status) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
        cur.execute(query, (lic_num, f_name, m_name, l_name, dob_input, sex, addr, exp_input, l_type, l_stat))
        conn.commit()
        
        print(f"\n Driver profile saved successfully!")
        print(f" System Generated Expiration Stamp: {exp_date.strftime('%A, %B %d, %Y')}")
        cur.close()
    except mysql.connector.Error as err:
        print(f" DB Transaction Error: {err}")

def register_vehicle(conn):
    print("\n --- Register New Motor Vehicle ---")
    lic_num = input("Owner's License Number: ").strip()

    if is_invalid_license_format(lic_num):
        return

    cur = conn.cursor()
    cur.execute("SELECT first_name, last_name FROM driver WHERE license_number = %s", (lic_num,))
    driver = cur.fetchone()
    cur.close()

    if not driver:
        print(f" Pre-flight Error: Driver license '{lic_num}' is not registered!")
        return

    plate = input("Plate Number: ").strip().upper()
    if not (3 <= len(plate) <= 7 and plate.isalnum()):
        print(" Input Error: Plate number must be between 3 to 7 alphanumeric characters (e.g., OWN2024).")
        return

    engine = input("Engine Number (e.g. ENG-E101): ").strip().upper()
    if not (6 <= len(engine) <= 15):
        print(" Input Error: Engine number must be between 6 to 15 characters.")
        return

    chassis = input("Chassis Number (e.g. CHS-E101): ").strip().upper()
    if not (6 <= len(chassis) <= 17):
        print(" Input Error: Chassis number/VIN must be between 6 to 17 characters.")
        return

    v_type = input("Vehicle Type (e.g., Sedan, SUV, Motorcycle): ").strip()
    if not v_type or v_type.isdigit():
        print(" Input Error: Vehicle type cannot be left blank and must be a descriptive textual string.")
        return

    make = input("Manufacturer/Make (e.g., Toyota, Honda, Mitsubishi): ").strip()
    if not make or make.isdigit():
        print(" Input Error: Manufacturer brand name cannot be left blank.")
        return

    model = input("Model (e.g., Vios, Montero, Civic): ").strip()
    if not model:
        print(" Input Error: Vehicle model designation line cannot be left blank.")
        return

    year_input = input("Year of Manufacture (YYYY): ").strip()
    if is_invalid_year_format(year_input):
        return
    year = int(year_input)

    color = input("Color: ").strip()
    if not color or color.isdigit():
        print(" Input Error: Vehicle color details must be explicitly specified.")
        return
    
    print("\nSelect Vehicle Classification:")
    print(" [1] Private Car\n [2] For-Hire / PUV (Commercial)")
    class_choice = input("Choice (1-2): ").strip()
    v_class = "For-Hire/PUV" if class_choice == '2' else "Private"

    franchise = None
    if class_choice == '2':
        franchise = input("Enter LTFRB Franchise Number [e.g.LTFRB-NCR-2018-1122]: ").strip()
        if not franchise:
            print(" Validation Error: For-Hire commercial units require an active franchise.")
            return

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
    
    if is_invalid_license_format(lic_num):
        return

    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM driver WHERE license_number = %s", (lic_num,))
        driver = cur.fetchone()
        cur.close()
        
        if not driver:
            print(f" Search Error: No registered driver found matching license '{lic_num}'.")
            return

        f_name = input(f"New First Name [{driver['first_name']}]: ").strip() or driver['first_name']
        if f_name.isdigit():
            print(" Input Error: First name cannot be strictly numeric. Modification aborted.")
            return

        m_name = input(f"New Middle Name [{driver['middle_name']}]: ").strip() or driver['middle_name']

        l_name = input(f"New Last Name [{driver['last_name']}]: ").strip() or driver['last_name']
        if l_name.isdigit():
            print(" Input Error: Last name cannot be strictly numeric. Modification aborted.")
            return  
                  
        addr = input(f"New Address [{driver['address']}]: ").strip() or driver['address']

        print(f"\nModify Sex Configuration [Current: {driver['sex']}]:")
        print("  [1] Male\n  [2] Female\n  [Press Enter to Skip]")
        sex_choice = input("Select choice (1-2): ").strip()
        if sex_choice == '1':
            sex = 'M'
        elif sex_choice == '2':
            sex = 'F'
        elif sex_choice == '':
            sex = driver['sex']
        else:
            print(" Validation Error: Selection unrecognized. Modification aborted.")
            return

        print(f"\nModify License Classification [Current: {driver['license_type']}]:")
        print("  [1] Student Permit\n  [2] Non-Professional\n  [3] Professional\n  [Press Enter to Skip]")
        type_choice = input("Select choice (1-3): ").strip()
        if type_choice == '1':
            l_type = "Student Permit"
        elif type_choice == '2':
            l_type = "Non-Professional"
        elif type_choice == '3':
            l_type = "Professional"
        elif type_choice == '':
            l_type = driver['license_type']
        else:
            print(" Validation Error: Selection unrecognized. Modification aborted.")
            return

        exp_input = input(f"\nNew Expiration Date (YYYY-MM-DD) [{driver['expiry_date']}]: ").strip()
        if exp_input == '':
            # if skipped, preserve the original date entry safely
            exp_final_date = driver['expiry_date']
            # if the database returns the date as a string format, it will parse cleanly
            if isinstance(exp_final_date, str):
                exp_final_date = datetime.strptime(exp_final_date, "%Y-%m-%d").date()
        else:
            # if typed, execute strict alphanumeric calendar formatting gates instantly
            if is_invalid_date_format(exp_input):
                return
            exp_final_date = datetime.strptime(exp_input, "%Y-%m-%d").date()

        # sync the license status
        current_date = date.today()
        if exp_final_date < current_date:
            l_stat = "Expired"
        else:
            # preserve existing glags (Suspended) unless explicitly updated by an overriding date change
            if driver['license_status'] in ['Suspended'] and exp_input == '':
                l_stat = driver['license_status']
            else:
                l_stat = "Active"

        # convert date object back into a database-ready string sequence
        exp_final_str = exp_final_date.strftime("%Y-%m-%d")


        cur = conn.cursor()
        update_query = """
            UPDATE driver 
            SET first_name = %s, middle_name = %s, last_name = %s, sex = %s,
                address = %s, license_type = %s, expiry_date = %s, license_status = %s 
            WHERE license_number = %s
        """
        cur.execute(update_query, (f_name, m_name, l_name, sex, addr, l_type, exp_final_str, l_stat, lic_num))
        conn.commit()

        print(" Updated successfully.")
        cur.close()
    
    except mysql.connector.Error as err:
        print(f" Database Modification Refused: {err}")
    except Exception as e:
        print(f" Unexpected Runtime Error: {e}")

def update_vehicle_registration(conn):
    print("\n --- Update Vehicle Details & Registration (Press Enter to Skip Field) ---")
    plate = input("Enter Target Vehicle Plate Number: ").strip().upper()
    if not plate:
        print(" Input Error: Plate number cannot be blank.")
        return

    try:
        cur = conn.cursor(dictionary=True)

        # get current vehicle data
        cur.execute("SELECT * FROM vehicle WHERE plate_number = %s", (plate,))
        v_data = cur.fetchone()

        # get current registration data
        cur.execute("SELECT * FROM registration WHERE plate_number = %s ORDER BY expiration_date DESC LIMIT 1", (plate,))
        r_data = cur.fetchone()

        if not v_data or not r_data:
            print(f" Search Error: Vehicle profile or active registration history not found for plate '{plate}'.")
            cur.close()
            return

        cur.close()

        # ═════════════════════════════════════════════════════════════════
        # MODULE A: VEHICLE ASSET STRUCTURAL UPDATES
        # ═════════════════════════════════════════════════════════════════

        make = input(f"New Manufacturer/Make [{v_data['make']}]: ").strip() or v_data['make']
        if make.isdigit():
            print(" Input Error: Manufacturer name cannot be strictly numeric. Operation aborted.")
            return

        model = input(f"New Model Designation [{v_data['model']}]: ").strip() or v_data['model']

        year_input = input(f"New Year of Manufacture [{v_data['year']}]: ").strip()
        if year_input == '':
            year = v_data['year']
        else:
            if is_invalid_year_format(year_input):
                return
            year = int(year_input)

        color = input(f"New Body Color Description [{v_data['color']}]: ").strip() or v_data['color']
        if color.isdigit():
            print(" Input Error: Color description cannot be strictly numeric. Operation aborted.")
            return

        print(f"\nUpdate Vehicle Classification [Current: {v_data['vehicle_classification']}]:")
        print("  [1] Private Car\n  [2] For-Hire / PUV (Commercial)\n  [Press Enter to Skip]")
        class_choice = input("Select choice (1-2): ").strip()

        if class_choice == '1':
            v_class = "Private"
            franchise = None
        elif class_choice == '2':
            v_class = "For-Hire/PUV"
            # require active LTFRB credentials if transitioning to commercial status
            current_franchise = v_data['ltfrb_franchise_number'] or "None Registered"
            franchise = input(f"Enter LTFRB Franchise Token Number [{current_franchise}]: ").strip() or v_data['ltfrb_franchise_number']
            if not franchise:
                print(" Validation Error: For-Hire commercial units require a valid franchise token.")
                return
        elif class_choice == '':
            v_class = v_data['vehicle_classification']
            franchise = v_data['ltfrb_franchise_number']
        else:
            print(" Validation Error: Option choice unrecognized. Operation aborted.")
            return

        # ═════════════════════════════════════════════════════════════════
        # MODULE B: LIFECYCLE REGISTRATION CALENDAR UPDATES
        # ═════════════════════════════════════════════════════════════════
        exp_input = input(f"\nNew Registration Expiration Date (YYYY-MM-DD) [{r_data['expiration_date']}]: ").strip()
        if exp_input == '':
            exp_final_date = r_data['expiration_date']
            if isinstance(exp_final_date, str):
                exp_final_date = datetime.strptime(exp_final_date, "%Y-%m-%d").date()
        else:
            if is_invalid_date_format(exp_input):
                return
            exp_final_date = datetime.strptime(exp_input, "%Y-%m-%d").date()

        current_date = date.today()
        r_status = "Expired" if exp_final_date < current_date else "Active"
        exp_final_str = exp_final_date.strftime("%Y-%m-%d")

        # ═════════════════════════════════════════════════════════════════
        # MODULE C: COMMIT TRANSACTIONS TO DATABASE PLATES
        # ═════════════════════════════════════════════════════════════════
        cur = conn.cursor()

        # update structural fields in vehicle table
        v_query = """
            UPDATE vehicle 
            SET make = %s, model = %s, year = %s, color = %s, 
                vehicle_classification = %s, ltfrb_franchise_number = %s 
            WHERE plate_number = %s
        """
        cur.execute(v_query, (make, model, year, color, v_class, franchise, plate))
        
        # update lifecycle fields in registration table
        r_query = """
            UPDATE registration 
            SET expiration_date = %s, registration_status = %s 
            WHERE registration_number = %s
        """
        cur.execute(r_query, (exp_final_str, r_status, r_data['registration_number']))

        conn.commit()

        print(f"\n SUCCESS: Vehicle asset attributes and operational logs modified cleanly!")
        print(f" Automated Registration Status: Adjusted to '{r_status}' based on calendar timelines.")
        cur.close()

    except mysql.connector.Error as err:
        print(f" Database Modification Refused: {err}")
    except Exception as e:
        print(f" Unexpected Runtime Error: {e}")

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
    print("\n --- Remove Driver Record Framework ---")
    lic_num = input("Enter Driver License Number to DELETE: ").strip()
    
    if is_invalid_license_format(lic_num):
        return

    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT first_name, last_name FROM driver WHERE license_number = %s", (lic_num,))
        driver = cur.fetchone()
        
        if not driver:
            print(f" Search Error: Driver license '{lic_num}' does not exist in registry database.")
            cur.close()
            return

        # Scan for active relational records connected to this driver
        cur.execute("SELECT COUNT(*) AS c FROM vehicle WHERE license_number = %s", (lic_num,))
        v_count = cur.fetchone()['c']
        cur.execute("SELECT COUNT(*) AS c FROM violation WHERE license_number = %s", (lic_num,))
        viol_count = cur.fetchone()['c']
        cur.close()

        # Dynamic warning notice if active relational paths are discovered
        if v_count > 0 or viol_count > 0:
            print(f"\n CRITICAL LINKAGE ALERT: {driver['first_name']} {driver['last_name']} has active assets:")
            print(f"   - Linked Registered Motor Vehicles: {v_count} unit(s)")
            print(f"   - Linked Traffic Citation Violations: {viol_count} record(s)")
            print("\n REAL-WORLD COMPLIANCE CASCADING POLICY:")
            print("   Executing this action will permanently PURGE all their registered vehicle profiles,")
            print("   registration lifecycles, and traffic demerit ledger histories completely.")
            
            confirm_cascade = input("\nProceed with total system cascade purge? (Type CASCADE-DELETE): ").strip()
            if confirm_cascade != "CASCADE-DELETE":
                print(" Operation aborted safely to preserve database table infrastructure.")
                return
        else:
            confirm = input(f"\nAre you sure you want to permanently delete driver {lic_num}? (YES/NO): ").strip().upper()
            if confirm != 'YES':
                print(" Transaction cancelled by user.")
                return

        cur = conn.cursor()
        
        cur.execute("DELETE FROM demerit_ledger WHERE license_number = %s", (lic_num,))        
        cur.execute("DELETE FROM violation WHERE license_number = %s", (lic_num,))        
        cur.execute("DELETE FROM registration WHERE plate_number IN (SELECT plate_number FROM vehicle WHERE license_number = %s)", (lic_num,))        
        cur.execute("DELETE FROM vehicle WHERE license_number = %s", (lic_num,))        
        cur.execute("DELETE FROM driver WHERE license_number = %s", (lic_num,))
        
        conn.commit()
        print(f"\n  CRITICAL PURGE COMPLETE: Driver '{lic_num}' and all connected records removed from the network.")
        cur.close()

    except mysql.connector.Error as err:
        conn.rollback() # Rolls back transaction modifications if an execution error occurs
        print(f"  Database Cascading Purge Failure: {err}")


def delete_vehicle(conn):
    print("\n --- Remove Registered Vehicle Asset ---")
    plate = input("Enter Vehicle Plate Number to DELETE: ").strip().upper()
    
    if not plate:
        print("  Input Error: Plate number cannot be empty.")
        return

    try:
        cur = conn.cursor(dictionary=True)
        # Pre-flight check: Verify asset existence
        cur.execute("SELECT make, model FROM vehicle WHERE plate_number = %s", (plate,))
        vehicle = cur.fetchone()
        
        if not vehicle:
            print(f"  Search Error: Vehicle asset plate '{plate}' not found in registry database.")
            cur.close()
            return

        # Count dependent citation entries
        cur.execute("SELECT COUNT(*) AS c FROM violation WHERE plate_number = %s", (plate,))
        v_count = cur.fetchone()['c']
        cur.close()

        if v_count > 0:
            print(f"\n  RELATIONAL IMPACT NOTICE: Vehicle asset {plate} is linked to {v_count} citation record(s).")
            print("   Wiping this car will cascade-delete its tracking logs from the violation ledger.")

        confirm = input(f"\nConfirm permanent structural removal of asset {plate}? (YES/NO): ").strip().upper()
        if confirm != 'YES':
            print("  Transaction cancelled by user.")
            return

        cur = conn.cursor()
        
        cur.execute("DELETE FROM demerit_ledger WHERE violation_id IN (SELECT violation_id FROM violation WHERE plate_number = %s)", (plate,))        
        cur.execute("DELETE FROM violation WHERE plate_number = %s", (plate,))        
        cur.execute("DELETE FROM registration WHERE plate_number = %s", (plate,))        
        cur.execute("DELETE FROM vehicle WHERE plate_number = %s", (plate,))
        
        conn.commit()
        print(f"\n  SUCCESS: Vehicle profile asset '{plate}' and its lifecycle registries cleared.")
        cur.close()

    except mysql.connector.Error as err:
        conn.rollback()
        print(f"  Database Modification Refused: {err}")
