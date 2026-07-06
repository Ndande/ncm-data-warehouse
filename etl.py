import os
import psycopg2
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD")
        )
        return conn
    except psycopg2.OperationalError as e:
        print(f"Connection failed: {e}")
        return None


def extract():
    df = pd.read_excel(r"C:\Users\ndand\data_pipeline\SPARE PARTS WEEKLY FOLLOW UP.xlsx", sheet_name="WEEKLY REPORT SPARES",skiprows=3)
    return df

def transform(df):
    df['DATE'] = pd.to_datetime(df['DATE'], errors='coerce')
    df['SITE'] = df['SITE'].str.strip().str.title()  # Remove leading/trailing whitespace and capitalize
    df['SUPPLIER'] = df['SUPPLIER'].str.strip().str.title()  # Remove leading/trailing whitespace and capitalize
    df['VEHICLE NUMBER'] = df['VEHICLE NUMBER'].str.strip()  # Remove leading/trailing whitespace 
    df['T PRICE'] = pd.to_numeric(df['T PRICE'], errors='coerce')  # Convert to numeric, set errors to NaN
    df['U PRICE'] = pd.to_numeric(df['U PRICE'], errors='coerce')  # Convert to numeric, set errors to NaN
    df_clean = df.dropna(subset=['SITE', 'SUPPLIER', 'T PRICE'])  # Drop rows with NaN in critical columns
    return df_clean

def load_dim_site(df, conn):
    cursor = conn.cursor()
    #Get unique sites from the dataframe
    sites = df['SITE'].dropna().unique()
    #Insert each site if it does not exisit
    for site in sites:
        cursor.execute("""
            INSERT INTO dim_site (name)
            VALUES (%s)
            ON CONFLICT (name) DO NOTHING
        """, (site,))
    conn.commit()
    #Build a mapping of site names to their IDs
    cursor.execute("SELECT name, id FROM dim_site")
    site_map = {row[0]: row[1] for row in cursor.fetchall()}
    cursor.close()
    return site_map
    
def load_dim_supplier(df, conn):
    cursor = conn.cursor()
    #Get unique suppliers from the dataframe
    suppliers = df['SUPPLIER'].dropna().unique()
    #Insert each supplier if it does not exist
    for supplier in suppliers:
        cursor.execute("""
            INSERT INTO dim_supplier (name)
            VALUES (%s)
            ON CONFLICT (name) DO NOTHING
        """, (supplier,))
    conn.commit()
    #Build a mapping of supplier names to their IDs
    cursor.execute("SELECT name, id FROM dim_supplier")
    supplier_map = {row[0]: row[1] for row in cursor.fetchall()}
    cursor.close()
    return supplier_map

def load_dim_vehicle(df, conn):
    cursor = conn.cursor()
    # Insert UNASSIGNED row first as a guaranteed fallback
    cursor.execute("""
        INSERT INTO dim_vehicle (code_parc, designation)
        VALUES (%s, %s)
        ON CONFLICT (code_parc) DO NOTHING
    """, ('UNASSIGNED', 'Stock / bulk / unidentified purchase'))
    #Get unique vehicles from the dataframe
    vehicles = df['VEHICLE NUMBER'].dropna().unique()
    #Insert each vehicle if it does not exist
    for vehicle in vehicles:
        cursor.execute("""
            INSERT INTO dim_vehicle (code_parc)
            VALUES (%s)
            ON CONFLICT (code_parc) DO NOTHING
        """, (vehicle,))
    conn.commit()
    #Build a mapping of vehicle names to their IDs
    cursor.execute("SELECT code_parc, id FROM dim_vehicle")
    vehicle_map = {row[0]: row[1] for row in cursor.fetchall()}
    cursor.close()
    return vehicle_map

def load_dim_date(df, conn):
    cursor = conn.cursor()
    #Get unique dates from the dataframe
    dates = df['DATE'].dropna().unique()
    #Insert each date if it does not exist
    for date in dates:
        cursor.execute("""
            INSERT INTO dim_date (full_date, day, month, month_name, quarter, year, day_of_week)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (full_date) DO NOTHING
        """, (date, date.day, date.month, date.strftime("%B"), (date.month - 1) // 3 + 1, date.year, date.strftime("%A")))
    conn.commit()
    #Build a mapping of dates to their IDs
    cursor.execute("SELECT full_date, id FROM dim_date")
    date_map = {row[0]: row[1] for row in cursor.fetchall()}
    cursor.close()
    return date_map

def load_fact_spare_parts(df, conn, site_map, supplier_map, vehicle_map, date_map):
    cursor = conn.cursor()
    for index, row in df.iterrows():
        site_id = site_map.get(row['SITE'])
        supplier_id = supplier_map.get(row['SUPPLIER'])
        vehicle_id = vehicle_map.get(row['VEHICLE NUMBER'], vehicle_map.get('UNASSIGNED'))  # Default to UNASSIGNED if not found
        date_id = date_map.get(row['DATE'].date() if pd.notna(row['DATE']) else None)
        
        cursor.execute("""
            INSERT INTO fact_spare_parts (date_id, vehicle_id, site_id, supplier_id, items, payment_method, u_price, qte, t_price)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (date_id, vehicle_id, site_id, supplier_id, row['ITEMS'], row['REMARK'], row['U PRICE'], row['QTE'], row['T PRICE']))
    conn.commit()
    cursor.close()

if __name__ == "__main__":
    conn = get_connection()
    if conn:
        print("Connection successful")
        df = extract()
        df = transform(df)
        site_map = load_dim_site(df, conn)
        supplier_map = load_dim_supplier(df, conn)
        vehicle_map = load_dim_vehicle(df, conn)
        date_map = load_dim_date(df, conn)
        load_fact_spare_parts(df, conn, site_map, supplier_map, vehicle_map, date_map)
        print(f"Vehicles loaded: {len(vehicle_map)}")
        print(f"Dates loaded: {len(date_map)}")
        print(site_map)
        print(supplier_map)
        print(vehicle_map)
        print(date_map)
        print("Facts loaded successfully")
        conn.close()