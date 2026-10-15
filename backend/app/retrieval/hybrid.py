def rrf_fuse(dense: list[int], sparse: list[int], chunk_ids: list[str], k: int=60, top_k: int=5):
    scores={}
    for ranking in (dense, sparse):
        for rank, idx in enumerate(ranking, 1): scores[idx]=scores.get(idx,0)+1/(k+rank)
    return sorted(scores, key=lambda i:(-scores[i], chunk_ids[i]))[:top_k]
