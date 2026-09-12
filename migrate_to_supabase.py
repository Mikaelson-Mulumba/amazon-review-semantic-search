import psycopg2
import os
from psycopg2.extras import execute_values

# Connect to your LOCAL Docker Postgres (source)
local_conn = psycopg2.connect(
    host="localhost", port=5433, dbname="amazon_search",
    user="mikaelson", password="devpassword"
)
local_cur = local_conn.cursor()

# Connect to SUPABASE (destination) — replace YOUR_PASSWORD below
supabase_conn = psycopg2.connect(
    host="aws-0-eu-west-2.pooler.supabase.com",
    port=5432,
    dbname="postgres",
    user="postgres.kogrntulmflvtfgbbiqz",
    password=os.environ.get("DB_PASSWORD")
)
supabase_cur = supabase_conn.cursor()

# Fetch everything from local database
local_cur.execute("SELECT asin, title, review_text, rating, embedding FROM reviews;")
rows = local_cur.fetchall()
print(f"Fetched {len(rows)} rows from local database")

# Insert into Supabase in batches
insert_query = """
    INSERT INTO reviews (asin, title, review_text, rating, embedding)
    VALUES %s
"""
execute_values(supabase_cur, insert_query, rows, page_size=1000)
supabase_conn.commit()

print(f"Migrated {len(rows)} rows to Supabase")

# Verify
supabase_cur.execute("SELECT COUNT(*) FROM reviews;")
print("Rows in Supabase:", supabase_cur.fetchone()[0])

# Clean up connections
local_cur.close()
local_conn.close()
supabase_cur.close()
supabase_conn.close()
