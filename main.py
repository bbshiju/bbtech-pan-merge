import os
import re
from flask import Flask, request, send_file, render_template_string, redirect, flash
from werkzeug.utils import secure_filename
import fitz  # PyMuPDF
from PyPDF2 import PdfReader, PdfWriter
from io import BytesIO

app = Flask(__name__)
app.secret_key = 'supersecretkey'
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2MB limit per file

HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>BBTECH PAN Merge Tool</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    body { background-color: #f8f9fa; padding-top: 40px; }
    .container { max-width: 600px; background: white; padding: 30px; border-radius: 15px; box-shadow: 0 0 20px rgba(0,0,0,0.1); }
    h2 { color: #0d6efd; font-weight: 600; }
    .logo { width: 150px; margin-bottom: 15px; }
    .note { font-size: 0.95rem; color: #555; margin-bottom: 20px; }
    .footer { font-size: 0.85rem; color: #666; margin-top: 20px; line-height: 1.4; }
  </style>
</head>
<body>
  <div class="container text-center">
    <img src="https://bbsewa.com/wp-content/uploads/2025/05/bbtechlogo.jpeg" class="logo" alt="BBTECH Logo">
    <h2>BBTECH PAN Merge Tool</h2>
    <p class="text-muted">Upload Acknowledgement + PAN Form PDFs below</p>
    <div class="note">⚠️ <strong>Note:</strong> The final merged PDF will be automatically named using the 15-digit Acknowledgement Number.</div>
    <form method="post" enctype="multipart/form-data">
      <div class="mb-3 text-start">
        <label class="form-label">PDF 1 (Acknowledgement Slip)</label>
        <input class="form-control" type="file" name="pdf1" required>
      </div>
      <div class="mb-3 text-start">
        <label class="form-label">PDF 2 (PAN Application Form)</label>
        <input class="form-control" type="file" name="pdf2" required>
      </div>
      <button type="submit" class="btn btn-primary w-100">Upload and Merge</button>
    </form>
    {% with messages = get_flashed_messages() %}
      {% if messages %}
        <div class="alert alert-danger mt-3">
          {% for message in messages %}
            <div>{{ message }}</div>
          {% endfor %}
        </div>
      {% endif %}
    {% endwith %}
    <div class="footer mt-4">
      👨‍💼 <strong>Developed by BB TECHNOLOGIES AND SERVICES</strong><br>
      PAN card agency provider<br>
      📞 Contact us: 63827 78910
    </div>
  </div>
</body>
</html>
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
            pdf1_bytes = pdf1.read()
            doc = fitz.open(stream=pdf1_bytes, filetype="pdf")
            page = doc[0]
            rect = page.rect

            crop_percentage = 0.47
            crop_rect = fitz.Rect(rect.x0, rect.y0, rect.x1, rect.y0 + rect.height * crop_percentage)
            page.set_cropbox(crop_rect)

            text = page.get_text()
            ack_number = extract_ack_number(text or "")
            if not ack_number:
                flash('Could not find 15-digit Acknowledgement Number in PDF 1.')
                return redirect(request.url)

            cropped_pdf_bytes = BytesIO()
            doc.save(cropped_pdf_bytes)
            cropped_pdf_bytes.seek(0)

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
