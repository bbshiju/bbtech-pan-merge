import os
import re
from flask import Flask, request, send_file, render_template_string, redirect, url_for, flash
from werkzeug.utils import secure_filename
import fitz  # PyMuPDF
from PyPDF2 import PdfReader, PdfWriter
from io import BytesIO

app = Flask(__name__)
app.secret_key = 'supersecretkey'
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2MB limit per file

HTML = """
<!doctype html>
<title>PDF Merge Tool</title>
<h2>Upload PDFs</h2>
<form method=post enctype=multipart/form-data>
  <label>PDF 1 (single page, both parts stacked):</label><br>
  <input type=file name=pdf1 required><br><br>
  <label>PDF 2 (any PDF):</label><br>
  <input type=file name=pdf2 required><br><br>
  <input type=submit value='Upload and Merge'>
</form>
{% with messages = get_flashed_messages() %}
  {% if messages %}
    <ul>
    {% for message in messages %}
      <li style="color:red;">{{ message }}</li>
    {% endfor %}
    </ul>
  {% endif %}
{% endwith %}
"""

def extract_ack_number(text):
    match = re.search(r'(\d{15})', text)
    return match.group(1) if match else None

@app.route('/', methods=['GET', 'POST'])
def upload_files():
    if request.method == 'POST':
        if 'pdf1' not in request.files or 'pdf2' not in request.files:
            flash('Both PDF files are required.')
            return redirect(request.url)
        pdf1 = request.files['pdf1']
        pdf2 = request.files['pdf2']
        if pdf1.filename == '' or pdf2.filename == '':
            flash('No selected file(s).')
            return redirect(request.url)
        if not pdf1.filename.lower().endswith('.pdf') or not pdf2.filename.lower().endswith('.pdf'):
            flash('Only PDF files are allowed.')
            return redirect(request.url)
        try:
            # Load PDF 1 with PyMuPDF
            pdf1_bytes = pdf1.read()
            doc = fitz.open(stream=pdf1_bytes, filetype="pdf")
            page = doc[0]
            rect = page.rect

            # Crop to just above the "Applicant's Copy" section (adjust 0.47 as needed)
            crop_percentage = 0.47  # Change this value to fine-tune the crop
            crop_rect = fitz.Rect(rect.x0, rect.y0, rect.x1, rect.y0 + rect.height * crop_percentage)
            page.set_cropbox(crop_rect)
            # Extract text for ack number
            text = page.get_text()
            ack_number = extract_ack_number(text or "")
            if not ack_number:
                flash('Could not find 15-digit Acknowledgement Number in PDF 1.')
                return redirect(request.url)
            # Save the cropped page directly from the original doc
            cropped_pdf_bytes = BytesIO()
            doc.save(cropped_pdf_bytes)
            cropped_pdf_bytes.seek(0)
            # Merge with PDF 2 using PyPDF2
            writer = PdfWriter()
            cropped_reader = PdfReader(cropped_pdf_bytes)
            writer.add_page(cropped_reader.pages[0])
            reader2 = PdfReader(pdf2)
            for page in reader2.pages:
                writer.add_page(page)
            output = BytesIO()
            writer.write(output)
            output.seek(0)
            filename = f"{ack_number}.pdf"
            return send_file(output, as_attachment=True, download_name=filename, mimetype='application/pdf')
        except Exception as e:
            flash(f'Error processing files: {e}')
            return redirect(request.url)
    return render_template_string(HTML)

if __name__ == '__main__':
    app.run(debug=True)
