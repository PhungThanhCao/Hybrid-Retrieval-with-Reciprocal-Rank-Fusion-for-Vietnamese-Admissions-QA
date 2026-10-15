import hashlib, json, os, shutil, tempfile
from pathlib import Path
import numpy as np
from rank_bm25 import BM25Okapi
from ..config import settings
from ..storage.file_store import atomic_json, atomic_pickle
from ..retrieval.tokenizer import tokenize
from .loader import load_document
from .chunker import chunk_pages

class Embedder:
    def __init__(self, model_name: str): self.model_name=model_name; self._model=None
    def encode(self, texts: list[str]) -> np.ndarray:
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model=SentenceTransformer(self.model_name)
        vectors=self._model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return np.asarray(vectors, dtype='float32')

def document_hash(path: Path): return hashlib.sha256(path.read_bytes()).hexdigest()
def remove_document(document_id: str, docs_dir: Path|None=None) -> bool:
    """Remove only a document identified by its content hash, never a client path."""
    docs_dir = docs_dir or settings.docs_path
    for path in docs_dir.iterdir():
        if path.is_file() and path.suffix.lower() in {'.pdf', '.txt', '.md'} and document_hash(path) == document_id:
            path.unlink()
            return True
    return False
def build_index(docs_dir: Path|None=None, index_dir: Path|None=None, embedder: Embedder|None=None):
    docs_dir=docs_dir or settings.docs_path; index_dir=index_dir or settings.indexes_path
    files=sorted(p for p in docs_dir.iterdir() if p.is_file() and p.suffix.lower() in {'.pdf','.txt','.md'})
    chunks=[]; manifest_docs=[]
    for p in files:
        digest=document_hash(p); new=chunk_pages(digest,p.name,load_document(p),settings.chunk_size,settings.chunk_overlap)
        chunks.extend(new); manifest_docs.append({'id':digest,'source':p.name,'chunk_count':len(new),'sha256':digest})
    if not chunks: raise ValueError('Không tìm thấy tài liệu hợp lệ để lập chỉ mục.')
    embedder=embedder or Embedder(settings.embedding_model)
    vectors=embedder.encode([c['content'] for c in chunks]);
    if vectors.ndim != 2 or len(vectors) != len(chunks): raise ValueError('Embedding trả về dữ liệu không hợp lệ.')
    tokens=[tokenize(c['content']) for c in chunks]; bm25=BM25Okapi(tokens)
    stage=Path(tempfile.mkdtemp(prefix='indexes-',dir=index_dir.parent)); stage.mkdir(exist_ok=True)
    try:
        try:
            import faiss
            idx=faiss.IndexFlatIP(vectors.shape[1]); idx.add(vectors); faiss.write_index(idx,str(stage/'faiss.index'))
        except ImportError:
            np.save(stage/'vectors.npy',vectors)
        atomic_pickle(stage/'bm25.pkl',bm25); atomic_json(stage/'chunks.json',chunks)
        atomic_json(stage/'manifest.json',{'version':1,'embedding_model':settings.embedding_model,'chunk_size':settings.chunk_size,'chunk_overlap':settings.chunk_overlap,'tokenizer':'regex-v1','documents':manifest_docs})
        index_dir.mkdir(parents=True,exist_ok=True)
        for f in stage.iterdir(): os.replace(f,index_dir/f.name)
    finally: shutil.rmtree(stage,ignore_errors=True)
    return len(manifest_docs),len(chunks)
