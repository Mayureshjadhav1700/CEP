import sqlite3

conn = sqlite3.connect('grievance.db')
c = conn.cursor()

# Check if table exists
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
print("Tables in database:", c.fetchall())

# Check data
try:
    c.execute("SELECT * FROM complaints")
    rows = c.fetchall()
    print("\nTotal complaints:", len(rows))
    for row in rows:
        print(row)
except Exception as e:
    print("Error reading complaints:", e)

conn.close()
