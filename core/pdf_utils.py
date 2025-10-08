import pdfplumber, re
from io import BytesIO

def read_pdf_text(file, max_pages=25, max_chars=20000):
    raw = file.read()
    file.seek(0)
    with pdfplumber.open(BytesIO(raw)) as pdf:
        pages = [p.extract_text() or "" for p in pdf.pages[:max_pages]]
    full = "\n".join(pages)[:max_chars]
    return full
