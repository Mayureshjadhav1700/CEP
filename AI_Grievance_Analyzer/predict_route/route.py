@app.route('/predict', methods=['POST'])
def predict():
    # Get user info
    name = request.form['name']
    village = request.form['village']
    pincode = request.form['pincode']
    aadhar_number = request.form['aadhar_number']

    complaint_text = ""
    extracted_text = ""
    department = ""

    # Text input
    if 'complaint' in request.form and request.form['complaint'].strip() != "":
        complaint_text = request.form['complaint']
        extracted_text = complaint_text

    # Image input
    elif 'image' in request.files:
        image_file = request.files['image']
        if image_file.filename != "":
            image_path = os.path.join("static/uploads", image_file.filename)
            image_file.save(image_path)
            result = reader.readtext(image_path, detail=0)
            extracted_text = " ".join(result)

    # Audio input
    elif 'audio' in request.files:
        audio_file = request.files['audio']
        if audio_file.filename != "":
            audio_path = os.path.join("static/recordings", audio_file.filename)
            audio_file.save(audio_path)
            result = whisper_model.transcribe(audio_path)
            extracted_text = result["text"]

    # Prediction
    if extracted_text.strip() != "":
        text_vec = vectorizer.transform([extracted_text])
        department = model.predict(text_vec)[0]

    # Save all info in SQLite
    conn = sqlite3.connect('grievance.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO complaints
        (name, village, pincode, aadhar_number, complaint_text, department, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (name, village, pincode, aadhar_number, extracted_text, department, datetime.now()))
    conn.commit()
    conn.close()

    return render_template('index.html',
                           complaint=extracted_text,
                           department=department)
