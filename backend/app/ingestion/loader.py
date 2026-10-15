from pathlib import Path
ALLOWED = {'.pdf', '.txt', '.md'}
def load_document(path: Path) -> list[tuple[int | None, str]]:
    if path.suffix.lower() not in ALLOWED: raise ValueError('Định dạng file chưa được hỗ trợ.')
    if not path.exists() or path.stat().st_size == 0: raise ValueError('File rỗng hoặc không tồn tại.')
    if path.suffix.lower() == '.pdf':
        try:
            import fitz
        except ImportError as e:
            raise RuntimeError('Thiếu PyMuPDF; hãy cài dependencies backend.') from e
        doc = fitz.open(path); pages = [(i + 1, p.get_text('text')) for i, p in enumerate(doc)]; doc.close()
        if not any(t.strip() for _, t in pages): raise ValueError('PDF không có text; MVP chưa hỗ trợ OCR.')
        return pages
    return [(None, path.read_text(encoding='utf-8', errors='replace'))]
