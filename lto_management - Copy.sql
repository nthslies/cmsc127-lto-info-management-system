-- 1. Safely handle the database layout initialization
DROP DATABASE IF EXISTS lto_management;
CREATE DATABASE lto_management;
USE lto_management;

-- 2. Safely handle user management creation drops
DROP USER IF EXISTS 'admin'@'localhost';
DROP USER IF EXISTS 'admin'@'%';

CREATE USER 'admin'@'%' IDENTIFIED BY 'adminadmin';
GRANT ALL PRIVILEGES ON lto_management.* TO 'admin'@'%';
FLUSH PRIVILEGES;

-- =====================================================================
-- 🛡️ TABLE STRUCTURES
-- =====================================================================

-- For driver (Updated to include Accumulated Demerit Points tracking)
CREATE TABLE driver (
    license_number VARCHAR(13) UNIQUE,
    first_name VARCHAR(50) NOT NULL,
    middle_name VARCHAR(50),
    last_name VARCHAR(50) NOT NULL,
    date_of_birth DATE NOT NULL,
    sex CHAR(1) NOT NULL,
    address VARCHAR(250) NOT NULL,
    expiry_date DATE NOT NULL,
    license_type VARCHAR(20) NOT NULL,
    license_status VARCHAR(20) NOT NULL,
    accumulated_demerit_points INT NOT NULL DEFAULT 0, -- RA 10930 Point Tracker Registry
    CONSTRAINT driver_pk PRIMARY KEY (license_number)
);

-- For vehicle
CREATE TABLE vehicle (
    plate_number VARCHAR(7),
    engine_number VARCHAR(50) NOT NULL,
    chassis_number VARCHAR(50) NOT NULL,
    vehicle_type VARCHAR(30) NOT NULL,
    make VARCHAR(50) NOT NULL,
    model VARCHAR(50) NOT NULL,
    year INT NOT NULL,
    color VARCHAR(30) NOT NULL,
    license_number VARCHAR(13),
    CONSTRAINT vehicle_pk PRIMARY KEY (plate_number),
    CONSTRAINT vehicle_engine_uk UNIQUE (engine_number),
    CONSTRAINT vehicle_chassis_uk UNIQUE (chassis_number),
    CONSTRAINT vehicle_driver_fk FOREIGN KEY (license_number) REFERENCES driver(license_number)
);

-- For registration
CREATE TABLE registration (
    registration_number VARCHAR(20),
    registration_status VARCHAR(20) NOT NULL,
    registration_date DATE NOT NULL,
    expiration_date DATE NOT NULL,
    plate_number VARCHAR(7),
    CONSTRAINT registration_pk PRIMARY KEY (registration_number),
    CONSTRAINT registration_plate_fk FOREIGN KEY (plate_number) REFERENCES vehicle(plate_number)
);

-- For violation
CREATE TABLE violation (
    violation_id INT,
    violation_date DATE NOT NULL,
    location VARCHAR(250) NOT NULL,
    violation_status VARCHAR(20) NOT NULL,
    license_number VARCHAR(13),
    plate_number VARCHAR(7),
    CONSTRAINT violation_pk PRIMARY KEY (violation_id),
    CONSTRAINT violation_driver_fk FOREIGN KEY (license_number) REFERENCES driver(license_number),
    CONSTRAINT violation_vehicle_fk FOREIGN KEY (plate_number) REFERENCES vehicle(plate_number)
);

-- For violation type (Updated with Demerit Points and legal Severity Category Tiers)
CREATE TABLE violationType (
    violation_code VARCHAR(10),
    violation_name VARCHAR(100) NOT NULL,
    fine_amount DECIMAL(10,2) NOT NULL,
    demerit_points INT NOT NULL DEFAULT 1,            -- Scales: 5, 3, or 1 point/s
    severity_category VARCHAR(20) NOT NULL DEFAULT 'Light', -- 'Grave', 'Less Grave', 'Light'
    violation_id INT,
    CONSTRAINT violationtype_pk PRIMARY KEY (violation_code),
    CONSTRAINT violationtype_violation_fk FOREIGN KEY (violation_id) REFERENCES violation(violation_id)
);

-- =====================================================================
-- 📊 DATABASE VIEWS
-- =====================================================================

CREATE VIEW view_all_drivers AS SELECT * FROM driver;

CREATE VIEW view_vehicle_driver AS SELECT v.plate_number, v.make, v.model, v.year, d.first_name, d.last_name FROM vehicle v JOIN driver d ON v.license_number = d.license_number;

CREATE VIEW view_registrations AS SELECT * FROM registration;

CREATE VIEW view_violations AS SELECT * FROM violation;

CREATE VIEW view_driver_vehicles AS SELECT d.license_number, d.first_name, d.last_name, v.plate_number, v.make, v.model FROM driver d LEFT JOIN vehicle v ON d.license_number = v.license_number;

CREATE VIEW view_vehicle_registration_status AS SELECT v.plate_number, v.make, v.model, r.registration_status, r.expiration_date FROM vehicle v LEFT JOIN registration r ON v.plate_number = r.plate_number;

CREATE VIEW view_violation_details AS SELECT v.violation_id, v.violation_date, v.location, d.first_name, d.last_name, vh.plate_number FROM violation v JOIN driver d ON v.license_number = d.license_number JOIN vehicle vh ON v.plate_number = vh.plate_number;

CREATE VIEW view_driver_violation_summary AS SELECT d.license_number, d.first_name, d.last_name, COUNT(v.violation_id) AS total_violations, SUM(vt.fine_amount) AS total_fines FROM driver d LEFT JOIN violation v ON d.license_number = v.license_number LEFT JOIN violationType vt ON v.violation_id = v.violation_id GROUP BY d.license_number, d.first_name, d.last_name;

CREATE VIEW view_expired_licenses AS SELECT * FROM driver WHERE expiry_date < CURRENT_DATE;

CREATE VIEW view_expired_registration AS SELECT v.plate_number, r.expiration_date FROM vehicle v JOIN registration r ON v.plate_number = r.plate_number WHERE r.expiration_date < CURRENT_DATE;

-- LTO System Point Registry View (Tracks compliance metrics per RA 10930 rules)
CREATE VIEW view_driver_points_registry AS 
SELECT license_number, first_name, last_name, license_type, license_status, accumulated_demerit_points 
FROM driver ORDER BY accumulated_demerit_points DESC, last_name ASC;


-- =====================================================================
-- 🇵🇭 POPULATING DATA RECORDS WITH DEMERIT VALUE ASSIGNMENTS
-- =====================================================================

INSERT INTO driver (license_number, first_name, middle_name, last_name, date_of_birth, sex, address, expiry_date, license_type, license_status, accumulated_demerit_points)
VALUES 
('N01-23-000001', 'Ariana', 'Dizon', 'Gomez', '2004-04-15', 'M', 'Los Baños, Laguna', '2031-04-15', 'Non-Professional', 'Active', 2),
('N02-24-123456', 'Maria', 'Clara', 'De Los Santos', '1985-10-22', 'F', 'Calamba, Laguna', '2029-10-22', 'Professional', 'Active', 8),
('N03-22-987654', 'Juan', 'Perez', 'Dela Cruz', '1970-01-30', 'M', 'Santo Tomas, Batangas', '2024-01-30', 'Non-Professional', 'Expired', 7),
('N04-25-112233', 'Leonor', 'Rivera', 'Kipping', '1995-05-12', 'F', 'San Pablo, Laguna', '2030-05-12', 'Professional', 'Suspended', 3),
('N05-21-554433', 'Jose', 'Protacio', 'Rizal', '1992-06-19', 'M', 'Calamba, Laguna', '2026-06-19', 'Non-Professional', 'Active', 5),
('E01-22-000123', 'Johnathan', 'Mendoza', 'Alvarez', '1990-08-14', 'M', 'Brgy. Batong Malake, Los Baños, Laguna', '2032-08-14', 'Professional', 'Active', 5),
('E02-23-000456', 'Patricia', 'Luna', 'Santos', '1998-11-03', 'F', 'Calamba City, Laguna', '2033-11-03', 'Non-Professional', 'Active', 5),
('E03-21-000789', 'Ramon', 'Agoncillo', 'Bautista', '1975-05-25', 'M', 'San Pablo City, Laguna', '2025-05-25', 'Professional', 'Expired', 0),
('E01-24-001122', 'Camille', 'Recto', 'Clara', '2001-02-14', 'F', 'Bay, Laguna', '2029-02-14', 'Student Permit', 'Active', 5),
('E02-20-003344', 'Danilo', 'Panganiban', 'Dimaculangan', '1968-12-01', 'M', 'Lipa City, Batangas', '2025-12-01', 'Professional', 'Suspended', 0),
('N01-24-000888', 'Mark', 'Anthony', 'Piatos', '2000-01-15', 'M', 'Quezon City, NCR', '2034-01-15', 'Non-Professional', 'Active', 8),
('N02-23-011223', 'Sofia', 'Isabella', 'Aquino', '1996-07-22', 'F', 'Makati City, NCR', '2033-07-22', 'Non-Professional', 'Active', 0),
('N03-21-099887', 'Ferdinand', 'Marcos', 'Cruz', '1982-09-11', 'M', 'Manila, NCR', '2024-09-11', 'Professional', 'Expired', 5),
('N01-25-022334', 'Angelica', 'Pangan', 'Valdez', '1993-04-30', 'F', 'Pasig City, NCR', '2035-04-30', 'Professional', 'Active', 1),
('A01-22-100200', 'Efren', 'Singson', 'Villanueva', '1988-03-19', 'M', 'Vigan City, Ilocos Sur', '2032-03-19', 'Professional', 'Active', 1),
('A02-23-300400', 'Katarina', 'Valdez', 'Marcos', '1995-10-10', 'F', 'Laoag City, Ilocos Norte', '2033-10-10', 'Non-Professional', 'Active', 0),
('A01-21-500600', 'Mariano', 'Diaz', 'Que', '1960-06-15', 'M', 'San Fernando City, La Union', '2024-06-15', 'Non-Professional', 'Expired', 0),
('D01-23-445566', 'Rodolfo', 'Castro', 'Gonzales', '1984-01-20', 'M', 'Angeles City, Pampanga', '2033-01-20', 'Professional', 'Active', 1),
('D02-24-778899', 'Elena', 'Soriano', 'Santiago', '1991-12-25', 'F', 'Malolos, Bulacan', '2034-12-25', 'Non-Professional', 'Active', 3),
('D03-20-112244', 'Geronimo', 'Joson', 'Tinop', '1973-07-08', 'M', 'Cabanatuan City, Nueva Ecija', '2025-07-08', 'Professional', 'Revoked', 0),
('G01-22-998877', 'Manuel', 'Lopez', 'Roxas', '1987-11-30', 'M', 'Iloilo City, Iloilo', '2032-11-30', 'Professional', 'Active', 5),
('G02-24-554411', 'Grace', 'Hofilena', 'Perez', '1999-05-05', 'F', 'Bacolod City, Negros Occidental', '2029-05-05', 'Student Permit', 'Active', 2),
('H01-23-123123', 'Siegfried', 'Go', 'Osmena', '1992-04-04', 'M', 'Cebu City, Cebu', '2033-04-04', 'Professional', 'Active', 1),
('H02-21-456456', 'Michelle', 'Sy', 'Chiongbian', '1994-09-18', 'F', 'Mandaue City, Cebu', '2031-09-18', 'Non-Professional', 'Active', 1),
('H03-22-789789', 'Vicente', 'Rama', 'Cuenco', '1980-02-28', 'M', 'Dumaguete City, Negros Oriental', '2025-02-28', 'Non-Professional', 'Suspended', 5),
('H01-25-111222', 'Kristine', 'Hermosa', 'Sotto', '1997-03-26', 'F', 'Lapu-Lapu City, Cebu', '2035-03-26', 'Non-Professional', 'Active', 1);

INSERT INTO vehicle (plate_number, engine_number, chassis_number, vehicle_type, make, model, year, color, license_number)
VALUES 
('ABC1234', 'ENG-101', 'CHS-101', 'Sedan', 'Toyota', 'Vios', 2022, 'White', 'N01-23-000001'),
('XYZ9876', 'ENG-202', 'CHS-202', 'SUV', 'Mitsubishi', 'Montero', 2023, 'Black', 'N02-24-123456'),
('OWN2024', 'ENG-203', 'CHS-203', 'Hatchback', 'Toyota', 'Wigo', 2021, 'Red', 'N02-24-123456'),
('LTO2024', 'ENG-303', 'CHS-303', 'Sedan', 'Honda', 'Brio', 2021, 'Red', 'N03-22-987654'),
('GHI5566', 'ENG-404', 'CHS-404', 'Pickup', 'Ford', 'Ranger', 2024, 'White', 'N04-25-112233'),
('JKL1122', 'ENG-505', 'CHS-505', 'Sedan', 'Mazda', 'Mazda3', 2020, 'Red', 'N05-21-554433'),
('EAR1122', 'ENG-E101', 'CHS-E101', 'Private Car', 'Honda', 'Civic', 2021, 'Blue', 'E01-22-000123'),
('WXY4567', 'ENG-E202', 'CHS-E202', 'Private Car', 'Toyota', 'Fortuner', 2023, 'Gray', 'E02-23-000456'),
('ZJQ8899', 'ENG-E303', 'CHS-E303', 'Public Utility Vehicle', 'Isuzu', 'Elf Jeepney', 2018, 'Green', 'E03-21-000789'),
('NXP9090', 'ENG-N404', 'CHS-N404', 'Motorcycle', 'Yamaha', 'Mio Aerox', 2024, 'Matte Black', 'N01-24-000888'),
('PIATOS1', 'ENG-N505', 'CHS-N505', 'Private Car', 'Mazda', 'CX-5', 2022, 'Soul Red', 'N01-24-000888'),
('NDZ4455', 'ENG-N606', 'CHS-N606', 'Private Car', 'Hyundai', 'Tucson', 2021, 'White', 'N02-23-011223'),
('NRE8811', 'ENG-N707', 'CHS-N707', 'Public Utility Vehicle', 'Toyota', 'Hiace Commuter', 2019, 'White', 'N03-21-099887'),
('AAZ1111', 'ENG-A101', 'CHS-A101', 'Private Car', 'Mitsubishi', 'Xpander', 2022, 'Silver', 'A01-22-100200'),
('ABB2222', 'ENG-A202', 'CHS-A202', 'Motorcycle', 'Honda', 'Click 125i', 2023, 'Red', 'A02-23-300400'),
('DFF3333', 'ENG-D101', 'CHS-D101', 'Private Car', 'Nissan', 'Navara', 2020, 'Orange', 'D01-23-445566'),
('DGG4444', 'ENG-D202', 'CHS-D202', 'Private Car', 'Toyota', 'Innova', 2019, 'Black', 'D02-24-778899'),
('DHH5555', 'ENG-D303', 'CHS-D303', 'Public Utility Vehicle', 'Mitsubishi', 'L300', 2017, 'White', 'D03-20-112244'),
('GAA1234', 'ENG-G101', 'CHS-G101', 'Private Car', 'Ford', 'Everest', 2023, 'White', 'G01-22-998877'),
('GBB5678', 'ENG-G202', 'CHS-G202', 'Motorcycle', 'Suzuki', 'Raider R150', 2022, 'Blue', 'G02-24-554411'),
('HAA9999', 'ENG-H101', 'CHS-H101', 'Private Car', 'Toyota', 'Avanza', 2021, 'Silver', 'H01-23-123123'),
('HBB8888', 'ENG-H202', 'CHS-H202', 'Private Car', 'Honda', 'City', 2020, 'Modern Steel', 'H02-21-456456'),
('HCC7777', 'ENG-H303', 'CHS-H303', 'Private Car', 'Subaru', 'Forester', 2019, 'Bronze', 'H03-22-789789'),
('HDD6666', 'ENG-H404', 'CHS-H404', 'Motorcycle', 'Kawasaki', 'Ninja 400', 2023, 'Green', 'H01-25-111222'),
('EAA2233', 'ENG-E404', 'CHS-E404', 'Private Car', 'Kia', 'Seltos', 2022, 'Yellow', 'E01-22-000123'),
('NAA5566', 'ENG-N808', 'CHS-N808', 'Private Car', 'BMW', '3 Series', 2021, 'Black', 'N01-25-022334'),
('GXX3344', 'ENG-G303', 'CHS-G303', 'Private Car', 'Geely', 'Coolray', 2022, 'Red', 'G01-22-998877'),
('HZZ1122', 'ENG-H505', 'CHS-H505', 'Private Car', 'MG', 'ZS', 2021, 'White', 'H01-25-111222');

INSERT INTO registration (registration_number, registration_status, registration_date, expiration_date, plate_number)
VALUES 
('REG-001', 'Current', '2025-01-01', '2026-01-01', 'ABC1234'),
('REG-002', 'Current', '2025-05-01', '2026-05-01', 'XYZ9876'),
('REG-003', 'Expired', '2023-01-01', '2024-01-01', 'LTO2024'), 
('REG-004', 'Current', '2025-02-01', '2026-02-01', 'GHI5566'),
('REG-005', 'Current', '2025-03-01', '2026-03-01', 'OWN2024'),
('REG-006', 'Active', '2025-05-10', '2026-05-10', 'EAR1122'),
('REG-007', 'Active', '2025-08-20', '2026-08-20', 'WXY4567'),
('REG-008', 'Expired', '2023-03-15', '2024-03-15', 'ZJQ8899'),
('REG-009', 'Active', '2025-11-12', '2026-11-12', 'NXP9090'),
('REG-010', 'Active', '2025-04-05', '2026-04-05', 'PIATOS1'),
('REG-011', 'Active', '2025-07-19', '2026-07-19', 'NDZ4455'),
('REG-012', 'Expired', '2024-01-10', '2025-01-10', 'NRE8811'),
('REG-013', 'Active', '2025-09-02', '2026-09-02', 'AAZ1111'),
('REG-014', 'Active', '2025-10-14', '2026-10-14', 'ABB2222'),
('REG-015', 'Active', '2025-02-28', '2026-02-28', 'DFF3333'),
('REG-016', 'Active', '2025-06-12', '2026-06-12', 'DGG4444'),
('REG-017', 'Expired', '2023-08-05', '2024-08-05', 'DHH5555'),
('REG-018', 'Active', '2025-12-01', '2026-12-01', 'GAA1234'),
('REG-019', 'Active', '2025-03-22', '2026-03-22', 'GBB5678'),
('REG-020', 'Active', '2025-01-15', '2026-01-15', 'HAA9999'),
('REG-021', 'Active', '2025-05-20', '2026-05-20', 'HBB8888'),
('REG-022', 'Expired', '2024-04-11', '2025-04-11', 'HCC7777'),
('REG-023', 'Active', '2025-07-07', '2026-07-07', 'HDD6666'),
('REG-024', 'Active', '2025-02-18', '2026-02-18', 'EAA2233'),
('REG-025', 'Active', '2025-10-30', '2026-10-30', 'NAA5566');

INSERT INTO violation (violation_id, violation_date, location, violation_status, license_number, plate_number)
VALUES 
(1, '2025-08-15', 'Los Baños, Laguna', 'Unpaid', 'N01-23-000001', 'ABC1234'),
(2, '2025-09-20', 'Calamba, Laguna', 'Paid', 'N01-23-000001', 'ABC1234'),
(3, '2026-01-10', 'Los Baños, Laguna', 'Settled', 'N02-24-123456', 'XYZ9876'),
(4, '2026-02-15', 'Makati City, NCR', 'Unpaid', 'N04-25-112233', 'GHI5566'),
(5, '2026-03-01', 'Los Baños, Laguna', 'Unpaid', 'N05-21-554433', 'JKL1122'),
(6, '2025-12-25', 'Los Baños, Laguna', 'Unpaid', 'N02-24-123456', 'XYZ9876'),
(7, '2025-06-15', 'Calamba, Laguna', 'Unpaid', 'E01-22-000123', 'EAR1122'),
(8, '2025-07-20', 'Los Baños, Laguna', 'Paid', 'E02-23-000456', 'WXY4567'),
(9, '2025-08-11', 'Quezon City, NCR', 'Settled', 'N01-24-000888', 'NXP9090'),
(10, '2025-09-05', 'Makati City, NCR', 'Unpaid', 'N01-24-000888', 'PIATOS1'),
(11, '2025-10-22', 'Vigan City, Ilocos Sur', 'Paid', 'A01-22-100200', 'AAZ1111'),
(12, '2025-11-03', 'Angeles City, Pampanga', 'Unpaid', 'D01-23-445566', 'DFF3333'),
(13, '2025-12-25', 'Iloilo City, Iloilo', 'Settled', 'G01-22-998877', 'GAA1234'),
(14, '2026-01-05', 'Cebu City, Cebu', 'Unpaid', 'H01-23-123123', 'HAA9999'),
(15, '2026-01-20', 'Mandaue City, Cebu', 'Paid', 'H02-21-456456', 'HBB8888'),
(16, '2026-02-14', 'Los Baños, Laguna', 'Unpaid', 'E01-24-001122', 'ABC1234'),
(17, '2026-02-28', 'Pasig City, NCR', 'Paid', 'N01-25-022334', 'NAA5566'),
(18, '2026-03-01', 'Malolos, Bulacan', 'Unpaid', 'D02-24-778899', 'DGG4444'),
(19, '2026-03-10', 'Bacolod City, Negros Occidental', 'Settled', 'G02-24-554411', 'GBB5678'),
(20, '2026-03-15', 'Dumaguete City, Negros Oriental', 'Unpaid', 'H03-22-789789', 'HCC7777'),
(21, '2026-04-02', 'Lapu-Lapu City, Cebu', 'Paid', 'H01-25-111222', 'HDD6666');

-- Re-mapped to support exact legal demerit scales from RA 10930 schedule documents
INSERT INTO violationType (violation_code, violation_name, fine_amount, demerit_points, severity_category, violation_id)
VALUES 
('V_SPEED', 'Overspeeding Infraction', 2500.00, 1, 'Light', 1),
('V_HELM',  'Not Wearing Protective Helmet', 1500.00, 1, 'Light', 2),
('V_PARK',  'Illegal Parking / Obstruction', 1000.00, 3, 'Less Grave', 4),
('V_RECK',  'Reckless Driving Infraction', 2000.00, 1, 'Light', 5),
('V_BELT',  'Failure to Wear Seatbelt Device', 1000.00, 1, 'Light', 7),
('V_DIST',  'Distracted Driving (Phone Use)', 5000.00, 1, 'Light', 8),
('V_DUI',   'Driving Under the Influence (DUI)', 20000.00, 5, 'Grave', 9),
('V_SIGN',  'Disregarding Traffic Signs/Signals', 3000.00, 5, 'Grave', 10),
('V_LIC',   'Driving Without a Valid License', 3000.00, 5, 'Grave', 13),
('V_REG',   'Driving an Unregistered Motor Vehicle', 10000.00, 5, 'Grave', 14),
('V_SMOKE', 'Smoke Belching (Air Pollution)', 5000.00, 1, 'Light', 17),
('V_LOAD',  'Axle Overloading Infraction', 3000.00, 3, 'Less Grave', 18);


-- =====================================================================
-- BASELINE PROJECT SPECIFICATIONS QUERIES
-- =====================================================================
-- 1 View all registered drivers (Filtered)
SELECT * FROM driver WHERE license_type = 'Non-Professional' AND license_status = 'Active' AND sex = 'F' AND date_of_birth BETWEEN '1990-01-01' AND '2005-01-01';

-- 2 View all vehicles owned by a given driver
SELECT d.first_name, d.last_name, v.plate_number, v.make, v.model FROM vehicle v JOIN driver d ON v.license_number = d.license_number WHERE d.last_name = 'De Los Santos';

-- 3 View all vehicles with expired registrations as of a given date
SELECT plate_number, registration_status, expiration_date FROM registration WHERE expiration_date < '2026-04-12';

-- 4 View all drivers with expired or suspended licenses
SELECT first_name, last_name, license_number, license_status FROM driver WHERE license_status = 'Expired' OR license_status = 'Suspended';

-- 5 Traffic violations by a driver within a date range
SELECT violation_date, location, violation_status FROM violation WHERE license_number = 'N01-23-000001' AND violation_date >= '2025-01-01' AND violation_date <= '2025-12-31';

-- 6 Total number of violations per type for a given year
SELECT vt.violation_name, COUNT(*) AS total_violations FROM violationType vt JOIN violation v ON vt.violation_id = v.violation_id WHERE YEAR(v.violation_date) = 2025 GROUP BY vt.violation_name;

-- 7 Vehicles involved in violations within a given city/region
SELECT DISTINCT vh.plate_number, vh.make, vh.model, v.location FROM vehicle vh JOIN violation v ON vh.plate_number = v.plate_number WHERE v.location LIKE '%Calamba%';