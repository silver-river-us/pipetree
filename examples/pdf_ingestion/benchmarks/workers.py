"""Worker functions for parallel PDF text extraction.

These functions run in separate processes via ProcessPoolExecutor.
They must be at module level to be picklable.
"""


def extract_pypdf_chunk(pdf_path: str, start: int, end: int) -> list[tuple[int, str]]:
    """Extract text from a chunk of pages using pypdf."""
    from pypdf import PdfReader

    reader = PdfReader(pdf_path)
    return [(i, reader.pages[i].extract_text() or "") for i in range(start, end)]


def extract_pdfplumber_chunk(pdf_path: str, start: int, end: int) -> list[tuple[int, str]]:
    """Extract text from a chunk of pages using pdfplumber."""
    import pdfplumber

    with pdfplumber.open(pdf_path) as pdf:
        return [(i, pdf.pages[i].extract_text() or "") for i in range(start, end)]


def extract_pymupdf_chunk(pdf_path: str, start: int, end: int) -> list[tuple[int, str]]:
    """Extract text from a chunk of pages using PyMuPDF."""
    import warnings

    warnings.filterwarnings("ignore", message=".*global interpreter lock.*")
    import fitz

    doc = fitz.open(pdf_path)
    results = [(i, doc[i].get_text() or "") for i in range(start, end)]
    doc.close()
    return results
