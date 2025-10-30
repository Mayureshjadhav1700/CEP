import csv
import re
from datetime import datetime

# Step 1: Read the CSV file
def read_csv_file(filename):
    data = []
    with open(filename, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            data.append(row)
    return data, reader.fieldnames

# Step 2: Process the data
def process_complaints_data(data, original_headers):
    print(f"Original dataset rows: {len(data)}")
    
    # Bilingual standardization mapping
    complaint_standardization = {
        # Water complaints
        'no water supply': ['no water supply', 'पाणी पुरवठा बंद'],
        'water tanker not arrived': ['water tanker not arrived', 'पाण्याचा टँकर आला नाही'],
        'water tank empty': ['drinking water tank is empty', 'पाण्याचा टँक रिकामा'],
        'handpump broken': ['handpump is broken', 'हँडपंप बंद'],
        'drinking water problem': ['drinking water problem', 'पिण्याच्या पाण्याची समस्या'],
        
        # Electricity complaints
        'electricity supply disrupted': ['electricity supply disrupted', 'वीज पुरवठा खंडित झाला'],
        'frequent power cuts': ['frequent power cuts', 'वीज खूप वेळा जाते'],
        'transformer not working': ['electric transformer is not working', 'ट्रान्सफॉर्मर बंद'],
        'prolonged power cut': ['no electricity for.*hours', 'वीज गेली'],
        
        # Health complaints
        'doctor not available': ['no doctor available', 'डॉक्टर उपलब्ध नाही'],
        'medicines not available': ['medicines are not available', 'औषधे उपलब्ध नाहीत'],
        'health worker absent': ['village health worker is absent', 'आरोग्य कर्मचारी गैरहजर'],
        'ambulance not arrived': ['emergency ambulance did not arrive', 'अॅम्ब्युलन्स आली नाही'],
        'health camp needed': ['health camp needed', 'आरोग्य शिबीराची गरज'],
        
        # Road complaints
        'road potholes': ['road is damaged', 'रस्त्यावर खड्डे', 'potholes'],
        'new road required': ['new road required', 'नवीन रस्ता बनवणे आवश्यक'],
        'road work pending': ['road construction is pending', 'रस्ता बांधकाम प्रलंबित'],
        
        # Sanitation complaints
        'garbage not collected': ['garbage is not collected', 'कचरा उचलला जात नाही', 'dustbins are overflowing'],
        'drainage problem': ['drainage water is overflowing', 'नाल्यांची स्वच्छता होत नाही'],
        
        # Education complaints
        'teachers not available': ['no teachers', 'शिक्षक नाहीत'],
        
        # Infrastructure complaints
        'streetlights not working': ['streetlights are not working', 'स्ट्रीटलाइट बंद'],
        'playground not maintained': ['playground is not maintained', 'प्लेग्राउंडची देखभाल नाही'],
        'library closed': ['library remains closed', '图书馆关闭'],
        
        # Administrative complaints
        'panchayat office empty': ['no one available at panchayat office', 'पंचायत कार्यालयात कोणी नाही']
    }
    
    def standardize_complaint(row):
        complaint_text = row.get('Complaint_Text', '')
        lang = row.get('lang', 'en')
        
        if not complaint_text:
            return 'unknown_issue'
        
        complaint_lower = complaint_text.lower()
        
        # Check each standardized category
        for standardized_name, patterns in complaint_standardization.items():
            for pattern in patterns:
                if re.search(pattern, complaint_lower, re.IGNORECASE):
                    return standardized_name
        
        return 'other_issue'
    
    def correct_category(row):
        standardized = row.get('Standardized_Complaint', '')
        current_category = row.get('Category', '')
        
        # Health camp requests should be "Others" (not Health)
        if 'health_camp_needed' in standardized:
            return 'Others'
        
        # Teacher availability should be "Education" (not Others)
        if 'teachers_not_available' in standardized and current_category == 'Others':
            return 'Education'
        
        # Panchayat office issues should be "Administrative" (not Others)
        if 'panchayat_office_empty' in standardized and current_category == 'Others':
            return 'Administrative'
        
        return current_category
    
    def refine_sentiment(row):
        complaint_text = str(row.get('Complaint_Text', '')).lower()
        standardized = row.get('Standardized_Complaint', '')
        current_sentiment = row.get('Sentiment', 'Negative')
        
        # Requests and suggestions should be Neutral
        if any(phrase in standardized for phrase in ['health_camp_needed', 'new_road_required']):
            return 'Neutral'
        
        # Check for request language in both English and Marathi
        request_keywords = ['need', 'required', 'necessary', 'should be', 'गरज', 'आवश्यक', 'बनवणे']
        if any(keyword in complaint_text for keyword in request_keywords):
            return 'Neutral'
        
        return current_sentiment
    
    def reassess_priority(row):
        category = row.get('Category', '')
        standardized = row.get('Standardized_Complaint', '')
        current_priority = row.get('Priority', 'Medium')
        
        # HIGH PRIORITY: Critical infrastructure and emergencies
        if (category in ['Water', 'Electricity'] or 
            (category == 'Health' and standardized in ['doctor_not_available', 'ambulance_not_arrived']) or
            (category == 'Sanitation' and 'drainage_problem' in standardized)):
            return 'High'
        
        # MEDIUM PRIORITY: Daily inconveniences
        elif (category == 'Health' and standardized in ['medicines_not_available', 'health_worker_absent']) or \
             (category == 'Sanitation' and 'garbage_not_collected' in standardized) or \
             (category == 'Road' and 'road_potholes' in standardized):
            return 'Medium'
        
        # LOW PRIORITY: Amenities, requests, and administrative issues
        elif (category in ['Others', 'Education', 'Administrative']) or \
             ('health_camp_needed' in standardized) or \
             ('new_road_required' in standardized):
            return 'Low'
        
        return current_priority
    
    def clean_complaint_text(text):
        if not text:
            return text
        
        # Standardize terms while preserving original language
        text = re.sub(r'primary health center', 'PHC', text, flags=re.IGNORECASE)
        text = re.sub(r'phc', 'PHC', text, flags=re.IGNORECASE)
        
        return text.strip()
    
    # Process each row
    processed_data = []
    for row in data:
        # Create a new row with all original data
        new_row = row.copy()
        
        # Clean complaint text (without changing language)
        new_row['Complaint_Text'] = clean_complaint_text(row.get('Complaint_Text', ''))
        
        # Standardize complaint (bilingual approach)
        new_row['Standardized_Complaint'] = standardize_complaint(new_row)
        
        # Correct category
        new_row['Category'] = correct_category(new_row)
        
        # Refine sentiment
        new_row['Sentiment'] = refine_sentiment(new_row)
        
        # Reassess priority
        new_row['Priority'] = reassess_priority(new_row)
        
        # KEEP ORIGINAL LANGUAGE - no changes to 'lang' column
        
        processed_data.append(new_row)
    
    # Remove duplicates (based on content, not language)
    unique_data = []
    seen = set()
    for row in processed_data:
        # Use standardized complaint + village + date to identify duplicates
        key = (row['Standardized_Complaint'], row['Village'], row['Date'])
        if key not in seen:
            seen.add(key)
            unique_data.append(row)
    
    print(f"Processed dataset rows: {len(unique_data)}")
    return unique_data

# Step 3: Write processed data to new CSV
def write_csv_file(filename, data, headers):
    with open(filename, 'w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=headers)
        writer.writeheader()
        writer.writerows(data)

# Step 4: Generate analysis report
def generate_report(processed_data):
    print("\n" + "="*60)
    print("PROCESSING COMPLETE - SUMMARY REPORT")
    print("="*60)
    
    # Initialize counters
    categories = {}
    sentiments = {}
    priorities = {}
    languages = {}
    standardized_counts = {}
    
    for row in processed_data:
        # Count categories
        cat = row['Category']
        categories[cat] = categories.get(cat, 0) + 1
        
        # Count sentiments
        sent = row['Sentiment']
        sentiments[sent] = sentiments.get(sent, 0) + 1
        
        # Count priorities
        prio = row['Priority']
        priorities[prio] = priorities.get(prio, 0) + 1
        
        # Count languages
        lang = row['lang']
        languages[lang] = languages.get(lang, 0) + 1
        
        # Count standardized complaints
        std = row['Standardized_Complaint']
        standardized_counts[std] = standardized_counts.get(std, 0) + 1
    
    print(f"\n📊 TOTAL COMPLAINTS: {len(processed_data)}")
    
    print(f"\n🌐 LANGUAGE DISTRIBUTION:")
    for lang, count in sorted(languages.items()):
        percentage = (count / len(processed_data)) * 100
        print(f"   {lang.upper()}: {count} ({percentage:.1f}%)")
    
    print(f"\n📋 CATEGORY DISTRIBUTION:")
    for cat, count in sorted(categories.items()):
        percentage = (count / len(processed_data)) * 100
        print(f"   {cat}: {count} ({percentage:.1f}%)")
    
    print(f"\n😊 SENTIMENT DISTRIBUTION:")
    for sent, count in sorted(sentiments.items()):
        percentage = (count / len(processed_data)) * 100
        print(f"   {sent}: {count} ({percentage:.1f}%)")
    
    print(f"\n🚨 PRIORITY DISTRIBUTION:")
    for prio, count in sorted(priorities.items()):
        percentage = (count / len(processed_data)) * 100
        print(f"   {prio}: {count} ({percentage:.1f}%)")
    
    print(f"\n🔧 TOP 10 STANDARDIZED COMPLAINT TYPES:")
    sorted_std = sorted(standardized_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    for std, count in sorted_std:
        print(f"   {std}: {count}")
    
    # Show sample of each language
    print(f"\n👀 SAMPLE COMPLAINTS BY LANGUAGE:")
    en_samples = [r for r in processed_data if r['lang'] == 'en'][:2]
    mr_samples = [r for r in processed_data if r['lang'] == 'mr'][:2]
    
    print(f"\n   English samples:")
    for i, sample in enumerate(en_samples, 1):
        print(f"     {i}. {sample['Complaint_Text'][:60]}...")
        print(f"        → Standardized: {sample['Standardized_Complaint']}")
        print(f"        → Category: {sample['Category']}, Sentiment: {sample['Sentiment']}, Priority: {sample['Priority']}")
    
    print(f"\n   Marathi samples:")
    for i, sample in enumerate(mr_samples, 1):
        print(f"     {i}. {sample['Complaint_Text'][:60]}...")
        print(f"        → Standardized: {sample['Standardized_Complaint']}")
        print(f"        → Category: {sample['Category']}, Sentiment: {sample['Sentiment']}, Priority: {sample['Priority']}")

# Main execution
def main():
    try:
        # Read original data
        print("📖 Reading dataset...")
        original_data, original_headers = read_csv_file('dataset_eng_marathi.csv')
        
        # Add new column to headers
        new_headers = original_headers + ['Standardized_Complaint']
        
        # Process data
        print("🔄 Processing complaints...")
        processed_data = process_complaints_data(original_data, original_headers)
        
        # Write processed data
        print("💾 Saving processed dataset...")
        write_csv_file('processed_complaints_bilingual.csv', processed_data, new_headers)
        
        # Generate detailed report
        generate_report(processed_data)
        
        print(f"\n✅ SUCCESS: Processed dataset saved as 'processed_complaints_bilingual.csv'")
        print(f"   Original: {len(original_data)} rows")
        print(f"   Processed: {len(processed_data)} rows (duplicates removed)")
        print(f"   New column added: 'Standardized_Complaint'")
        
    except FileNotFoundError:
        print("❌ Error: File 'dataset_eng_marathi.csv' not found. Please make sure it's in the same directory.")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    main()