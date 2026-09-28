import os
import logging
from pypdf import PdfReader

# Silence third-party PDF font and syntax warnings
logging.getLogger("pypdf").setLevel(logging.ERROR)

def parse_pdf(file_path: str, max_pages: int = 50) -> str:
    """
    Parse a PDF file into readable Markdown text.
    Extracts text page by page, formatting page breaks cleanly.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    reader = PdfReader(file_path)
    total_pages = len(reader.pages)
    pages_to_read = min(total_pages, max_pages)

    output = []
    output.append(f"# Document: {os.path.basename(file_path)}\n")
    if total_pages > max_pages:
        output.append(f"> Note: Document has {total_pages} pages. Showing first {max_pages} pages.\n")

    for idx in range(pages_to_read):
        page = reader.pages[idx]
        text = page.extract_text()
        if text and text.strip():
            output.append(f"## Page {idx + 1}\n")
            output.append(text.strip())
            output.append("\n---\n")

    return "\n".join(output)
