import numpy as np
from rank_bm25 import BM25Okapi
from app.rag.pipeline import RAGPipeline
from app.retrieval.tokenizer import tokenize
class FakeEmbed:
    def encode(self,texts): return np.array([[1.,0.] for _ in texts],dtype='float32')
def test_empty_query_and_retrieval():
    p=RAGPipeline(embedder=FakeEmbed(),generator=lambda _: 'Có thông tin [1]')
    p.chunks=[{'chunk_id':'one','content':'CNTT 7480201','source':'x.md','page':None,'title':'CNTT','document_id':'d'}]
    p.bm25=BM25Okapi([tokenize(p.chunks[0]['content'])]);p.vectors=np.array([[1.,0.]],dtype='float32')
    assert p.retrieve('')==[]
    assert p.answer('mã 7480201')[0]=='Có thông tin [1]'
