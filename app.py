from flask import Flask, request, render_template, send_from_directory
import os
import cv2
import pytesseract
from fpdf import FPDF
from difflib import ndiff

# Set the path to Tesseract executable
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Initialize Flask app
app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'static/uploads'
RESULT_FOLDER = 'static/results'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['RESULT_FOLDER'] = RESULT_FOLDER

@app.route('/')
def index():
    """Render the upload page."""
    return render_template('index.html')

@app.route('/compare', methods=['POST'])
def compare_images():
    """Handle image text extraction and comparison."""
    if 'file1' not in request.files or 'file2' not in request.files:
        return "Please upload both images.", 400

    # Retrieve uploaded files
    file1 = request.files['file1']
    file2 = request.files['file2']

    # Ensure files are valid
    if not file1.filename or not file2.filename:
        return "Both files must have valid filenames.", 400

    # Save uploaded files
    path1 = os.path.join(app.config['UPLOAD_FOLDER'], file1.filename)
    path2 = os.path.join(app.config['UPLOAD_FOLDER'], file2.filename)
    file1.save(path1)
    file2.save(path2)

    # Load images using OpenCV
    img1 = cv2.imread(path1)
    img2 = cv2.imread(path2)

    # Validate image loading
    if img1 is None:
        return "Image 1 is invalid or corrupted.", 400
    if img2 is None:
        return "Image 2 is invalid or corrupted.", 400

    # Convert images to grayscale for better OCR accuracy
    gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

    # Extract text using Tesseract OCR
    text1 = pytesseract.image_to_string(gray1)
    text2 = pytesseract.image_to_string(gray2)

    # Process extracted text (remove extra spaces, convert to lowercase)
    text1_cleaned = " ".join(text1.split()).lower()
    text2_cleaned = " ".join(text2.split()).lower()

    # Compare text and identify differences
    missing_words = []
    additional_words = []

    diff = list(ndiff(text1_cleaned.split(), text2_cleaned.split()))
    for word in diff:
        if word.startswith('- '):  # Word missing in Image 2
            missing_words.append(word[2:])
        elif word.startswith('+ '):  # Word added in Image 2
            additional_words.append(word[2:])

    missing_text = ", ".join(missing_words) if missing_words else "None"
    additional_text = ", ".join(additional_words) if additional_words else "None"

    # Generate PDF
    pdf_filename = f"result_{file1.filename}_{file2.filename}.pdf"
    pdf_filepath = os.path.join(app.config['RESULT_FOLDER'], pdf_filename)
    create_pdf(pdf_filepath, file1.filename, file2.filename, text1_cleaned, text2_cleaned, missing_text, additional_text)

    # Render result template with extracted data and download link
    return render_template(
        'result.html',
        original1=file1.filename,
        original2=file2.filename,
        extracted_text1=text1_cleaned,
        extracted_text2=text2_cleaned,
        missing_text=missing_text,
        additional_text=additional_text,
        pdf_filename=pdf_filename
    )

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Serve uploaded images."""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/download/<filename>')
def download_file(filename):
    """Download the generated PDF."""
    return send_from_directory(app.config['RESULT_FOLDER'], filename)

def create_pdf(pdf_filepath, original1, original2, text1, text2, missing_text, additional_text):
    """Generate PDF with comparison result in proper order."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    # Title
    pdf.cell(200, 10, txt="Comparison Result", ln=True, align='C')

    # Image 1
    pdf.ln(10)
    pdf.cell(200, 10, txt=f"Original Image 1: {original1}", ln=True)
    pdf.image(os.path.join(app.config['UPLOAD_FOLDER'], original1), x=10, y=30, w=80)

    # Image 2
    pdf.ln(50)  # Adding space for the second image
    pdf.cell(200, 10, txt=f"Original Image 2: {original2}", ln=True)
    pdf.image(os.path.join(app.config['UPLOAD_FOLDER'], original2), x=10, y=70, w=80)

    # Extracted Text Section
    pdf.ln(100)  # Adding space before extracted texts
    pdf.multi_cell(0, 10, f"Extracted Text from Image 1:\n{text1}")
    pdf.ln(5)
    pdf.multi_cell(0, 10, f"Extracted Text from Image 2:\n{text2}")

    # Text Differences Section
    pdf.ln(10)  # Adding space before differences
    pdf.cell(200, 10, txt=f"Missing Text (in Image 1 but not in Image 2):", ln=True)
    pdf.multi_cell(0, 10, missing_text)
    pdf.cell(200, 10, txt=f"Additional Text (in Image 2 but not in Image 1):", ln=True)
    pdf.multi_cell(0, 10, additional_text)

    # Save PDF
    pdf.output(pdf_filepath)

if __name__ == '__main__':
    app.run(debug=True)
