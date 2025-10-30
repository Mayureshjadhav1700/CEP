import sqlite3
import csv

# Connect to the database
conn = sqlite3.connect('grievance.db')
c = conn.cursor()

# Select all records from complaints table
c.execute("SELECT * FROM complaints")
rows = c.fetchall()

# Column headers
headers = [description[0] for description in c.description]

# Export to CSV
with open('complaints.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(headers)  # write header
    writer.writerows(rows)    # write data

print("Data exported to complaints.csv successfully!")

conn.close()
