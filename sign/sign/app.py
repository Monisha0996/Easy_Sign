import os
import base64
import pdfplumber
from flask import Flask, render_template, request, send_file, url_for, send_from_directory
from werkzeug.utils import secure_filename
from PyPDF2 import PdfReader, PdfWriter
from PIL import Image, ImageOps
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from io import BytesIO

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'png', 'jpg', 'jpeg'}

# Ensure the uploads folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Function to check allowed file types
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Function to find "Sign here" text and its coordinates in the PDF
def find_sign_here_coordinates(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            words = page.extract_words()
            previous_word = None
            for word in words:
                if previous_word and previous_word['text'].lower() == "sign" and word['text'].lower() == "here":
                    if abs(previous_word['top'] - word['top']) < 5:
                        return previous_word['x0'], previous_word['top'], word['x1'], word['bottom'], page_num
                previous_word = word
    return None, None, None, None, None

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        pdf_file = request.files.get('pdf_file')
        signature = request.files.get('signature-file')  # Uploaded signature file
        signature_data = request.form.get('signatureData')  # Canvas-drawn signature (base64 image)
        password = request.form.get('password')

        signature_path = None

        # Process canvas-drawn signature
        if signature_data:
            signature_path = process_canvas_signature(signature_data)
            if signature_path:
                print(f"Canvas signature saved at {signature_path}")
            else:
                return "Error: Could not process canvas signature."

        # Process uploaded signature file
        elif signature and allowed_file(signature.filename):
            signature_path = process_uploaded_signature(signature)
            if signature_path:
                print(f"Uploaded signature saved at {signature_path}")
            else:
                return "Error: Could not process uploaded signature."

        if not signature_path:
            return "Please provide a valid signature."

        if pdf_file and allowed_file(pdf_file.filename):
            pdf_path = save_uploaded_file(pdf_file)
            x0, y0, x1, y1, page_num = find_sign_here_coordinates(pdf_path)

            if x0 is not None and y0 is not None:
                signed_pdf_path = sign_pdf(pdf_path, signature_path, password, x0, y0, x1, y1, page_num)
                preview_url = url_for('preview_file', filename=os.path.basename(signed_pdf_path))
                download_url = url_for('download_file', filename=os.path.basename(signed_pdf_path))
                return render_template('preview.html', preview_url=preview_url, download_url=download_url)
            else:
                return "Could not find 'Sign here' in the document."
        else:
            return "Please upload a valid PDF document."
    
    return render_template('upload.html')

# Helper function to save the uploaded PDF
def save_uploaded_file(pdf_file):
    pdf_filename = secure_filename(pdf_file.filename)
    pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], pdf_filename)
    pdf_file.save(pdf_path)
    return pdf_path

# Function to process canvas-drawn signature
def process_canvas_signature(signature_data):
    try:
        signature_data = signature_data.split(",")[1]  # Remove Base64 header
        signature_img_data = base64.b64decode(signature_data)
        signature_img = Image.open(BytesIO(signature_img_data)).convert("RGBA")
        signature_img = flatten_image(signature_img)
        signature_path = os.path.join(app.config['UPLOAD_FOLDER'], 'signature_canvas.png')
        signature_img.save(signature_path)
        return signature_path
    except Exception as e:
        print(f"Error processing canvas signature: {e}")
        return None

# Function to process uploaded signature file
def process_uploaded_signature(signature):
    try:
        signature_filename = secure_filename(signature.filename)
        signature_path = os.path.join(app.config['UPLOAD_FOLDER'], signature_filename)
        signature.save(signature_path)
        signature_img = Image.open(signature_path).convert("RGBA")
        signature_img = flatten_image(signature_img)
        signature_img.save(signature_path)
        return signature_path
    except Exception as e:
        print(f"Error processing uploaded signature: {e}")
        return None

# Helper function to flatten images with transparency onto a white background
def flatten_image(image):
    background = Image.new("RGB", image.size, (255, 255, 255))
    background.paste(image, mask=image.split()[3])
    return background

# Function to sign the PDF with the signature and apply encryption if necessary
def sign_pdf(pdf_path, signature_path, password, x0, y0, x1, y1, page_num):
    reader = PdfReader(pdf_path)
    writer = PdfWriter()
    packet = BytesIO()
    can = canvas.Canvas(packet, pagesize=letter)
    
    box_width = x1 - x0
    box_height = y1 - y0
    signature_width = box_width * 0.85
    signature_height = box_height * 0.85
    centered_x = x0 + (box_width - signature_width) / 2
    centered_y = y0 + (box_height - signature_height) / 2

    can.drawImage(signature_path, centered_x, centered_y, width=signature_width, height=signature_height)
    can.save()
    packet.seek(0)
    signature_pdf = PdfReader(packet)

    for i in range(len(reader.pages)):
        page = reader.pages[i]
        if i == page_num:
            page.merge_page(signature_pdf.pages[0])
        writer.add_page(page)

    if password:
        writer.encrypt(user_pwd=password, use_128bit=True)

    signed_pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], 'signed_' + os.path.basename(pdf_path))
    with open(signed_pdf_path, 'wb') as f_out:
        writer.write(f_out)

    return signed_pdf_path

# Route to serve the signed PDF for preview
@app.route('/preview/<filename>')
def preview_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Route to allow downloading the signed PDF
@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
