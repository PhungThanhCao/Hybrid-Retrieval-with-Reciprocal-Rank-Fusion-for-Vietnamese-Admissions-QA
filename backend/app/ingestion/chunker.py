import hashlib, re
def clean(text: str) -> str: return re.sub(r'\n{3,}', '\n\n', re.sub(r'[ \t]+', ' ', text)).strip()
def _title(part: str) -> str:
    m = re.search(r'(?m)^#{1,6}\s+(.+)$', part); return m.group(1).strip() if m else 'Nội dung tuyển sinh'
def chunk_pages(document_id: str, source: str, pages: list[tuple[int|None,str]], size=700, overlap=100):
    out=[]; ordinal=0
    for page, raw in pages:
        text=clean(raw)
        if not text: continue
        blocks=re.split(r'(?=^#{1,6}\s+)|\n\s*\n', text, flags=re.M)
        buffer=''; title='Nội dung tuyển sinh'
        for block in blocks:
            if not block.strip(): continue
            if block.lstrip().startswith('#'): title=_title(block)
            candidate=(buffer+'\n\n'+block).strip() if buffer else block.strip()
            if len(candidate.split()) > size and buffer:
                content=buffer; cid=hashlib.sha256(f'{document_id}:{page}:{ordinal}:{content}'.encode()).hexdigest()
                out.append({'chunk_id':cid,'document_id':document_id,'source':source,'page':page,'title':title,'content':content,'chunk_index':ordinal}); ordinal+=1
                tail=' '.join(buffer.split()[-overlap:]); buffer=(tail+'\n\n'+block).strip()
            else: buffer=candidate
        if buffer:
            cid=hashlib.sha256(f'{document_id}:{page}:{ordinal}:{buffer}'.encode()).hexdigest()
            out.append({'chunk_id':cid,'document_id':document_id,'source':source,'page':page,'title':title,'content':buffer,'chunk_index':ordinal}); ordinal+=1
    return out
