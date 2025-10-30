import easyocr

# Initialize reader
reader = easyocr.Reader(['en'])  # 'en' = English

# Read text from image
results = reader.readtext('sample.png')

# Print extracted text
for (bbox, text, prob) in results:
    print(f"Text: {text} | Confidence: {prob:.2f}")