from app.rag.pipeline import RAGPipeline
def test_small_talk_does_not_require_search():
    pipeline=RAGPipeline()
    answer,sources=pipeline.answer('Cảm ơn bạn nhé')
    assert 'Rất vui' in answer and sources == []
def test_follow_up_query_contains_prior_subject():
    pipeline=RAGPipeline()
    class Turn:
        def __init__(self,role,content): self.role,self.content=role,content
    query=pipeline.contextual_query('thế điểm chuẩn của ngành thì sao',[Turn('user','học phí ngành Công nghệ thông tin là bao nhiêu?')])
    assert 'Công nghệ thông tin' in query
