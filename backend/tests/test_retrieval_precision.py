import numpy as np
from rank_bm25 import BM25Okapi
from app.rag.pipeline import RAGPipeline
from app.retrieval.tokenizer import tokenize
def test_exact_major_and_intent_outrank_generic_terms():
    p=RAGPipeline()
    p.chunks=[
        {'chunk_id':'generic','content':'Điểm ưu tiên ngành công nghệ và phương thức xét tuyển.', 'source':'a','page':1,'title':'a','document_id':'a'},
        {'chunk_id':'ict-score','content':'Công nghệ Thông tin. Điểm chuẩn theo phương thức THPT: 20 điểm.', 'source':'b','page':8,'title':'b','document_id':'b'},
    ]
    p.bm25=BM25Okapi([tokenize(c['content']) for c in p.chunks])
    assert p._sparse_ranking('điểm chuẩn ngành công nghệ thông tin là bao nhiêu')[0] == 1
