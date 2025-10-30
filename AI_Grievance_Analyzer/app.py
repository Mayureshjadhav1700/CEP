from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import os
import joblib
import sqlite3
from datetime import datetime
import easyocr
import whisper
import csv
from dotenv import load_dotenv

# -----------------------------
# Load environment variables
# -----------------------------
load_dotenv()  # reads .env file

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET", "super_secret_key")  # default secret

# Fixed admin credentials
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

# Ensure folders exist
os.makedirs("static/uploads", exist_ok=True)
os.makedirs("static/recordings", exist_ok=True)

# Absolute paths for DB & CSV
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "grievance.db")
CSV_PATH = os.path.join(BASE_DIR, "complaints.csv")

print("📂 Database path:", DB_PATH)
print("📄 CSV path:", CSV_PATH)

# -----------------------------
# Database Setup
# -----------------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Users table with optional role
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            mobile TEXT,
            role TEXT DEFAULT 'user'
        )
    ''')
    # Complaints table
    c.execute('''
        CREATE TABLE IF NOT EXISTS complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            full_name TEXT,
            village TEXT,
            pincode TEXT,
            aadhar TEXT,
            complaint_text TEXT,
            department TEXT,
            timestamp TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# -----------------------------
# Load AI Model + Vectorizer
# -----------------------------
model_path = os.path.join(BASE_DIR, "model/grievance_model.pkl")
vectorizer_path = os.path.join(BASE_DIR, "model/vectorizer.pkl")
model = joblib.load(model_path)
vectorizer = joblib.load(vectorizer_path)

# -----------------------------
# OCR + Whisper
# -----------------------------
reader = easyocr.Reader(['en'])
whisper_model = whisper.load_model("tiny")

# -----------------------------
# Helper: Save to CSV
# -----------------------------
def save_to_csv(full_name, mobile, village, pincode, aadhar, complaint, department, timestamp):
    file_exists = os.path.isfile(CSV_PATH)
    with open(CSV_PATH, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Full Name", "Mobile", "Village", "Pincode", "Aadhar", "Complaint", "Department", "Timestamp"])
        writer.writerow([full_name, mobile, village, pincode, aadhar, complaint, department, timestamp])
    print(f"📝 Complaint saved in CSV: {full_name} → {department}")

# -----------------------------
# Routes
# -----------------------------
@app.route('/')
def login():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def do_login():
    name = request.form.get('name', '').strip()
    mobile = request.form.get('mobile', '').strip()
    password = request.form.get('password', '').strip()  # used only for admin

    # --- Admin login ---
    if name == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        session['user_id'] = 0
        session['username'] = "Admin"
        session['role'] = "admin"
        return redirect(url_for('admin_dashboard'))

    # --- User login ---
    if not name or not mobile:
        return "Name and Mobile are required!"

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE name=? AND mobile=?", (name, mobile))
    user = c.fetchone()

    if user:
        user_id = user[0]
    else:
        c.execute("INSERT INTO users (name, mobile, role) VALUES (?, ?, 'user')", (name, mobile))
        conn.commit()
        user_id = c.lastrowid

    conn.close()

    session['user_id'] = user_id
    session['username'] = name
    session['role'] = 'user'
    session['mobile'] = mobile
    return redirect(url_for('index'))

@app.route('/index')
def index():
    if 'user_id' not in session or session.get('role') != 'user':
        return redirect(url_for('login'))
    return render_template('index.html', username=session['username'])

@app.route('/predict', methods=['POST'])
def predict():
    if 'user_id' not in session or session.get('role') != 'user':
        return redirect(url_for('login'))

    # --- Form fields ---
    full_name = request.form.get("full_name", "")
    village = request.form.get("village", "")
    pincode = request.form.get("pincode", "")
    aadhar = request.form.get("aadhar", "")

    extracted_text = ""
    department = ""

    # --- Text input ---
    if 'complaint' in request.form and request.form['complaint'].strip():
        extracted_text = request.form['complaint'].strip()

    # --- Image input ---
    elif 'image' in request.files:
        image_file = request.files['image']
        if image_file and image_file.filename:
            image_path = os.path.join("static/uploads", image_file.filename)
            image_file.save(image_path)
            result = reader.readtext(image_path, detail=0)
            extracted_text = " ".join(result)

    # --- Audio input ---
    elif 'audio' in request.files:
        audio_file = request.files['audio']
        if audio_file and audio_file.filename:
            audio_path = os.path.join("static/recordings", audio_file.filename)
            audio_file.save(audio_path)
            result = whisper_model.transcribe(audio_path)
            extracted_text = result["text"]

    if extracted_text.strip():
        text_vec = vectorizer.transform([extracted_text])
        department = model.predict(text_vec)[0]
    else:
        extracted_text = "No complaint text provided."
        department = "Unknown"

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # --- Save to DB ---
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO complaints (user_id, full_name, village, pincode, aadhar, complaint_text, department, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (session['user_id'], full_name, village, pincode, aadhar, extracted_text, department, timestamp))
    conn.commit()
    conn.close()
    print(f"✅ Complaint saved to DB: {extracted_text[:60]} → {department}")

    # --- Save to CSV ---
    save_to_csv(full_name, session['mobile'], village, pincode, aadhar, extracted_text, department, timestamp)

    return render_template('index.html',
                           username=session['username'],
                           complaint=extracted_text,
                           department=department)

# -----------------------------
# Admin Dashboard
# -----------------------------
@app.route('/admin')
def admin_dashboard():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT u.name, u.mobile, c.full_name, c.village, c.pincode, c.aadhar, 
               c.complaint_text, c.department, c.timestamp
        FROM complaints c
        JOIN users u ON c.user_id = u.id
        ORDER BY c.timestamp DESC
    """)
    complaints = c.fetchall()
    conn.close()

    return render_template('admin_dashboard.html', complaints=complaints)

# -----------------------------
# Logout
# -----------------------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# -----------------------------
# View complaints API (optional)
# -----------------------------
@app.route('/view_complaints')
def view_complaints():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT u.name, u.mobile, c.full_name, c.village, c.pincode, c.aadhar, 
               c.complaint_text, c.department, c.timestamp
        FROM complaints c
        JOIN users u ON c.user_id = u.id
        ORDER BY c.timestamp DESC
    """)
    data = c.fetchall()
    conn.close()
    return jsonify(data)

# -----------------------------
# Run App
# -----------------------------
if __name__ == '__main__':
    app.run(debug=True)

