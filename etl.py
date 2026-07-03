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

if __name__ == "__main__":
    conn = get_connection()
    if conn:
        print("Connection successful")
        df = extract()
        df = transform(df)
        site_map = load_dim_site(df, conn)
        supplier_map = load_dim_supplier(df, conn)
        print(site_map)
        print(supplier_map)
        conn.close()