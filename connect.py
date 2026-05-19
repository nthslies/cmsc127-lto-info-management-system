# connect.py
import mysql.connector

def database():
    try:
        mydb = mysql.connector.connect(
            host="localhost",
            user="root",        # Replace with your MySQL username
            password="yourpassword",  # Replace with your MySQL root password
            buffered=True
        )
        mycursor = mydb.cursor()

        # 2. Recreate or establish the LTO database
        print("Creating database if it doesn't exist...")
        mycursor.execute("CREATE DATABASE IF NOT EXISTS lto_management")
        mycursor.execute("USE lto_management")

        # 3. Check if your tables are already built to avoid duplicate execution
        mycursor.execute("SHOW TABLES")
        existing_tables = mycursor.fetchall()

        if not existing_tables:
            print("Database is empty. Loading lto_management.sql...")
            
            # 4. Open and parse your LTO script file from the local folder
            with open("lto_management.sql", "r", encoding="utf-8") as file:
                # Read entire script and split by semicolon delimiter
                sql_commands = file.read().split(';')

                for command in sql_commands:
                    clean_command = command.strip()
                    if clean_command:  # Skip empty strings
                        try:
                            mycursor.execute(clean_command)
                        except mysql.connector.Error as err:
                            print(f"\n Error executing statement:\n{clean_command}\nError: {err}\n")

            mydb.commit()
            print(" lto_management.sql executed and database setup completed successfully!")
        else:
            print(" LTO tables already exist. Skipping script execution to preserve data.")
        
        return mydb, mycursor

    except mysql.connector.Error as err:
        print(f" Database connection error: {err}")
        return None, None
    except FileNotFoundError:
        print(" Configuration Error: 'lto_management.sql' was not found in this directory. Ensure it matches your folder layout.")
        return None, None
    except Exception as e:
        print(f" An unexpected error occurred: {e}")
        return None, None