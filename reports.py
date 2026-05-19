# reports.py
import mysql.connector
from tabulate import tabulate

# reports.py

def display_results(cur):
    rows = cur.fetchall()
    if rows:
        print("\n" + tabulate(rows, headers="keys", tablefmt="grid"))
    else:
        print("\n No operational records found matching the specified parameters.")

# LTO REPORT 1: Dynamic Driver Profiling 
def view_drivers_filtered(cur):
    print("\nFilter registered drivers by: [1] License Type  [2] License Status  [3] Sex  [4] Age Range  [5] View All")
    choice = input("Select filter option: ").strip()
    
    # Base query calculates real-time demerit aggregates straight from the ledger
    query = """
        SELECT 
            d.license_number, d.first_name, d.last_name, d.sex, d.license_type, d.license_status, d.date_of_birth,
            COALESCE(SUM(l.points_changed), 0) AS live_ledger_points
        FROM driver d
        LEFT JOIN demerit_ledger l ON d.license_number = l.license_number
    """
    group_by_clause = " GROUP BY d.license_number"
    
    if choice == '1':
        value = input("Enter License Type: ").strip()
        cur.execute(query + " WHERE d.license_type = %s" + group_by_clause + " ORDER BY d.last_name;", (value,))
    elif choice == '2':
        value = input("Enter Status: ").strip()
        cur.execute(query + " WHERE d.license_status = %s" + group_by_clause + " ORDER BY d.last_name;", (value,))
    elif choice == '3':
        value = input("Enter Sex (M/F): ").strip().upper()
        cur.execute(query + " WHERE d.sex = %s" + group_by_clause + " ORDER BY d.last_name;", (value,))
    elif choice == '4':
        min_age = input("Enter Minimum Age: ").strip()
        max_age = input("Enter Maximum Age: ").strip()
        cur.execute(query + " WHERE YEAR(CURRENT_DATE) - YEAR(d.date_of_birth) BETWEEN %s AND %s" + group_by_clause + " ORDER BY d.date_of_birth DESC;", (min_age, max_age))
    else:
        cur.execute(query + group_by_clause + " ORDER BY d.last_name;")
        
    display_results(cur)

# LTO REPORT 2: Fleet Assets Lookup 
def view_vehicles_by_owner(cur, last_name):
    query = """
        SELECT 
            d.license_number, d.first_name, d.last_name, 
            v.plate_number, v.make, v.model, v.year, v.color,
            v.vehicle_classification, 
            COALESCE(v.ltfrb_franchise_number, 'N/A') AS franchise_token
        FROM vehicle v 
        JOIN driver d ON v.license_number = d.license_number 
        WHERE LOWER(d.last_name) = LOWER(%s);
    """
    cur.execute(query, (last_name,))
    display_results(cur)

# LTO REPORT 3: Registration Lifecycle Expiration 
def view_expired_registrations(cur, cutoff_date):
    query = """
        SELECT r.registration_number, v.plate_number, v.make, v.model, r.registration_status, r.expiration_date
        FROM registration r
        JOIN vehicle v ON r.plate_number = v.plate_number
        WHERE r.expiration_date < %s;
    """
    cur.execute(query, (cutoff_date,))
    display_results(cur)

# LTO REPORT 4: Non-Compliant Drivers Audit 
def view_invalid_licenses(cur):
    query = """
        SELECT license_number, first_name, last_name, license_type, license_status, expiry_date 
        FROM driver 
        WHERE license_status IN ('Expired', 'Suspended', 'Revoked')
        ORDER BY license_status, last_name;
    """
    cur.execute(query)
    display_results(cur)

# LTO REPORT 5: Citation Historical Tracking 
def view_driver_violations_by_date(cur, license_number, start_date, end_date):
    query = """
    SELECT v.violation_id, vt.violation_name, v.violation_date, v.location, vt.fine_amount, v.violation_status
    FROM violation v
    JOIN violationType vt ON v.violation_code = vt.violation_code 
    WHERE v.license_number = %s AND v.violation_date BETWEEN %s AND %s
    ORDER BY v.violation_date DESC;
    """
    cur.execute(query, (license_number, start_date, end_date))
    display_results(cur)

# LTO REPORT 6: Aggregated Infraction Distribution Metric 
def view_violation_distribution_by_year(cur, target_year):
    query = """
        SELECT 
            vt.violation_name, 
            COUNT(v.violation_id) AS total_volume_apprehended, 
            SUM(vt.fine_amount) AS total_fines_assessed,
            SUM(CASE WHEN v.violation_status IN ('Paid', 'Settled') THEN vt.fine_amount ELSE 0.00 END) AS total_revenue_collected,
            SUM(CASE WHEN v.violation_status = 'Unpaid' THEN vt.fine_amount ELSE 0.00 END) AS outstanding_receivables
        FROM violationType vt 
        JOIN violation v ON vt.violation_code = v.violation_code 
        WHERE YEAR(v.violation_date) = %s 
        GROUP BY vt.violation_name
        ORDER BY total_volume_apprehended DESC;
    """
    cur.execute(query, (target_year,))
    display_results(cur)

# LTO REPORT 7: Regional Violation Mapping 
def view_violations_by_location(cur, region_keyword):
    query = """
        SELECT DISTINCT vh.plate_number, vh.make, vh.model, vh.vehicle_type, v.violation_date, v.location
        FROM vehicle vh 
        JOIN violation v ON vh.plate_number = v.plate_number 
        WHERE v.location LIKE %s
        ORDER BY v.violation_date DESC;
    """
    cur.execute(query, (f"%{region_keyword}%",))
    display_results(cur)