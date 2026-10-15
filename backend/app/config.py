from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE = Path(__file__).resolve().parents[2]
BACKEND_DIR = Path(__file__).resolve().parents[1]
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE / '.env', extra='ignore')
    gemini_api_key: str = ''
    gemini_model: str = ''
    embedding_model: str = 'BAAI/bge-m3'
    documents_dir: str = '../data/documents'
    index_dir: str = '../data/indexes'
    dense_top_k: int = 10
    sparse_top_k: int = 10
    final_top_k: int = 5
    rrf_k: int = 60
    chunk_size: int = 700
    chunk_overlap: int = 100
    max_upload_mb: int = 10
    frontend_origin: str = 'http://localhost:5173'
    @property
    def docs_path(self):
        # Paths in .env are intentionally relative to backend/ (e.g. ../data/documents).
        return (BACKEND_DIR / self.documents_dir).resolve()
    @property
    def indexes_path(self): return (BACKEND_DIR / self.index_dir).resolve()
settings = Settings()
