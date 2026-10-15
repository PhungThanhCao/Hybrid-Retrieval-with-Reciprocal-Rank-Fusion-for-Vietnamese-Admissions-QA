import asyncio, os, re, threading, uuid
from pathlib import Path
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .schemas import ChatRequest, ChatResponse, Source
from .ingestion.indexer import build_index, remove_document
from .rag.pipeline import RAGPipeline

app=FastAPI(title='RAG Tư vấn Tuyển sinh')
app.add_middleware(CORSMiddleware,allow_origins=[settings.frontend_origin],allow_credentials=True,allow_methods=['*'],allow_headers=['*'])
pipeline=RAGPipeline(); lock=threading.RLock()
@app.on_event('startup')
def startup(): pipeline.load()
def clear_indexes():
    for name in ('faiss.index','vectors.npy','bm25.pkl','chunks.json','manifest.json'):
        (settings.indexes_path / name).unlink(missing_ok=True)
def refresh_pipeline():
    """Atomically replace the in-memory searcher after a completed rebuild."""
    global pipeline
    candidate=RAGPipeline()
    candidate.load()
    pipeline=candidate
@app.get('/api/health')
def health():
    return {'status':'ok','index_ready':pipeline.ready,'document_count':len({c['document_id'] for c in pipeline.chunks}),'chunk_count':len(pipeline.chunks)}
@app.get('/api/documents')
def documents():
    result={}
    for c in pipeline.chunks: result.setdefault(c['document_id'],{'id':c['document_id'],'source':c['source'],'chunk_count':0})['chunk_count']+=1
    return list(result.values())
@app.post('/api/chat',response_model=ChatResponse)
def chat(body:ChatRequest):
    with lock:
        if not pipeline.ready: raise HTTPException(503,{'code':'INDEX_NOT_READY','message':'Chưa có chỉ mục. Hãy nạp tài liệu trước.'})
        try: answer,chunks=pipeline.answer(body.question,body.history)
        except RuntimeError as e: raise HTTPException(502,{'code':'GENERATION_ERROR','message':str(e)})
    sources=[Source(ref_id=i,chunk_id=c['chunk_id'],source=c['source'],page=c['page'],title=c['title'],excerpt=c['content'][:350]) for i,c in enumerate(chunks,1)]
    return ChatResponse(answer=answer,sources=sources)
@app.post('/api/ingest')
async def ingest(file:UploadFile=File(...)):
    suffix=Path(file.filename or '').suffix.lower()
    if suffix not in {'.pdf','.txt','.md'}: raise HTTPException(400,'Chỉ chấp nhận PDF, TXT hoặc Markdown.')
    display_name=Path(file.filename or 'tai_lieu').stem
    safe_name=re.sub(r'[^\w. -]', '_', display_name, flags=re.UNICODE).strip(' .') or 'tai_lieu'
    name=f'{uuid.uuid4().hex}_{safe_name}{suffix}'; dest=settings.docs_path/name; settings.docs_path.mkdir(parents=True,exist_ok=True)
    total=0
    with dest.open('wb') as f:
        while part:=await file.read(1024*1024):
            total+=len(part)
            if total>settings.max_upload_mb*1024*1024: f.close(); dest.unlink(missing_ok=True); raise HTTPException(413,'File vượt quá dung lượng cho phép.')
            f.write(part)
    try:
        with lock:
            counts=await asyncio.to_thread(build_index); pipeline.load()
        return {'status':'ok','document_count':counts[0],'chunk_count':counts[1]}
    except Exception as e:
        dest.unlink(missing_ok=True); raise HTTPException(400,f'Không thể nạp tài liệu: {e}')
@app.delete('/api/documents/{document_id}')
async def delete_document(document_id: str):
    if not re.fullmatch(r'[a-f0-9]{64}', document_id): raise HTTPException(400,'Mã tài liệu không hợp lệ.')
    with lock:
        removed=remove_document(document_id)
        if not removed: raise HTTPException(404,'Không tìm thấy tài liệu.')
        remaining=[p for p in settings.docs_path.iterdir() if p.is_file() and p.suffix.lower() in {'.pdf','.txt','.md'}]
        if remaining:
            await asyncio.to_thread(build_index)
            refresh_pipeline()
        else:
            clear_indexes(); refresh_pipeline()
    return {'status':'ok','message':'Đã xóa tài liệu và cập nhật chỉ mục.'}
@app.delete('/api/documents')
async def delete_all_documents():
    with lock:
        for path in settings.docs_path.iterdir():
            if path.is_file() and path.suffix.lower() in {'.pdf','.txt','.md'}: path.unlink()
        clear_indexes(); refresh_pipeline()
    return {'status':'ok','message':'Đã xóa toàn bộ kiến thức và chỉ mục.'}
