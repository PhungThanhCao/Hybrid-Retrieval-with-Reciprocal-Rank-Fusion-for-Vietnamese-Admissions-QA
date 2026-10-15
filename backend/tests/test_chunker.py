from app.ingestion.chunker import chunk_pages
def test_chunk_preserves_codes_and_money():
    chunks=chunk_pages('doc','x.md',[(None,'# Học phí\nMã 7480201 năm 2026 có mức 25.000.000 đồng.')],20,3)
    assert '7480201' in chunks[0]['content'] and '25.000.000 đồng' in chunks[0]['content']
