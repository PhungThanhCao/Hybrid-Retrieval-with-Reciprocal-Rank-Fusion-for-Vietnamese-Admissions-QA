from app.retrieval.hybrid import rrf_fuse
from app.retrieval.tokenizer import tokenize
def test_rrf_rewards_both_and_tie_breaks():
    # Both chunks occur in both rankings; equal scores use stable chunk_id tie-break.
    assert rrf_fuse([0,1],[1,0],['b','a'],60,2)==[1,0]
    assert '7480201' in tokenize('Mã 7480201 năm 2026')
