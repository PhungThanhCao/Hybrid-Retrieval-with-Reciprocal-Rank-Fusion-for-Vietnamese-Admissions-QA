import json, pickle
from pathlib import Path
import numpy as np
import re
from rank_bm25 import BM25Okapi
from ..config import settings
from ..ingestion.indexer import Embedder
from ..retrieval.tokenizer import tokenize
from ..retrieval.hybrid import rrf_fuse
from .prompts import build_prompt

SAFE = 'Tôi chưa tìm thấy thông tin này trong tài liệu tuyển sinh được cung cấp.'
ROUTE_RESPONSES = {
    'greeting': 'Chào bạn! Tôi có thể hỗ trợ tra cứu thông tin tuyển sinh từ các tài liệu đã được nạp. Bạn muốn hỏi về ngành học, học phí, điểm chuẩn hay thời hạn đăng ký?',
    'thanks': 'Rất vui được hỗ trợ bạn! Nếu cần, bạn có thể hỏi tiếp về ngành học, học phí, điểm chuẩn hoặc hồ sơ tuyển sinh.',
    'capability': 'Tôi tra cứu thông tin từ các tài liệu tuyển sinh đã được nạp, chẳng hạn ngành học, mã ngành, học phí, điểm chuẩn, phương thức xét tuyển và thời hạn. Tôi không tự suy đoán khi tài liệu không có thông tin.'
}
REFERENTIAL = ('thế', 'còn', 'này', 'đó', 'kia', 'như vậy', 'sao', 'ngành này', 'ngành đó')
INTENT_TERMS = ('điểm chuẩn', 'học phí', 'mã ngành', 'chỉ tiêu', 'thời gian', 'hạn đăng ký', 'phương thức xét tuyển', 'hồ sơ', 'học bổng')
STOPWORDS = {'là','bao','nhiêu','cho','của','về','theo','các','có','gì','thì','sao','nào','một','tôi','bạn','ngành','điểm','chuẩn','học','phí','mã','thông','tin'}
class RAGPipeline:
    def __init__(self, index_dir:Path|None=None, embedder=None, generator=None):
        self.index_dir=index_dir or settings.indexes_path; self.embedder=embedder; self.generator=generator; self.chunks=[]; self.bm25=None; self.faiss=None; self.vectors=None
    @property
    def ready(self): return bool(self.chunks and self.bm25)
    def load(self):
        needed=['chunks.json','bm25.pkl','manifest.json']
        if not all((self.index_dir/x).exists() for x in needed): return False
        self.chunks=json.loads((self.index_dir/'chunks.json').read_text(encoding='utf-8'))
        # Only deserialize the app-created local index directory. Never load user-uploaded pickles.
        self.bm25=pickle.loads((self.index_dir/'bm25.pkl').read_bytes())
        try:
            import faiss
            self.faiss=faiss.read_index(str(self.index_dir/'faiss.index'))
        except (ImportError, RuntimeError):
            vector_file=self.index_dir/'vectors.npy'
            self.vectors=np.load(vector_file) if vector_file.exists() else None
        return self.ready
    def route(self, question: str) -> str | None:
        normalized=re.sub(r'[^\wÀ-ỹ ]',' ',question.lower()).strip()
        words=set(normalized.split())
        if len(words) <= 5 and words & {'chào','hello','hi','xin'}: return 'greeting'
        if len(words) <= 7 and ('cảm ơn' in normalized or 'thanks' in words): return 'thanks'
        if len(words) <= 12 and any(x in normalized for x in ('bạn là ai','bạn làm được gì','có thể làm gì','giúp được gì')): return 'capability'
        return None
    def contextual_query(self, question: str, history=None) -> str:
        """Expand follow-up questions before retrieval; history never becomes evidence."""
        lowered=question.lower()
        if not history or not any(marker in lowered for marker in REFERENTIAL): return question
        previous=[]
        for turn in reversed(history):
            if turn.role == 'user':
                previous.append(turn.content)
                break
        # The previous assistant answer often contains the resolved major/degree name.
        for turn in reversed(history):
            if turn.role == 'assistant':
                previous.append(turn.content[:700])
                break
        return f"{question}\nNgữ cảnh câu hỏi trước: {' '.join(previous)}"
    @staticmethod
    def _normal(text: str) -> str:
        return re.sub(r'\s+', ' ', text.lower()).strip()
    def _entity_phrases(self, query: str) -> list[str]:
        """Find meaningful multi-word phrases such as 'công nghệ thông tin'."""
        words=re.findall(r'[\wÀ-ỹ]+', query.lower(), flags=re.UNICODE)
        phrases=set()
        for length in range(2, 6):
            for start in range(len(words)-length+1):
                candidate=' '.join(words[start:start+length])
                tokens=candidate.split()
                # An entity must include at least two non-generic words.
                if sum(token not in STOPWORDS for token in tokens) >= 2:
                    phrases.add(candidate)
        return sorted(phrases,key=lambda value:(-len(value.split()),value))
    def _sparse_ranking(self, query: str) -> list[int]:
        """BM25 plus exact entity/intent matching to avoid generic-term false positives."""
        bm25_scores=self.bm25.get_scores(tokenize(query))
        normalized=[self._normal(chunk['content']) for chunk in self.chunks]
        phrases=self._entity_phrases(query)
        intents=[term for term in INTENT_TERMS if term in query.lower()]
        scored=[]
        for index, base_score in enumerate(bm25_scores):
            text=normalized[index]; bonus=0.0
            # A full entity match is much stronger evidence than individual keywords.
            for phrase in phrases:
                if phrase in text: bonus=max(bonus, 80 + len(phrase.split()) * 8)
            for intent in intents:
                if intent in text: bonus += 35
            scored.append((float(base_score)+bonus,index))
        return [index for _,index in sorted(scored,key=lambda pair:(-pair[0],self.chunks[pair[1]]['chunk_id']))[:settings.sparse_top_k]]
    def retrieve(self, question:str, history=None):
        if not self.ready or not question.strip(): return []
        query=self.contextual_query(question,history)
        if self.embedder is None: self.embedder=Embedder(settings.embedding_model)
        vector=self.embedder.encode([query])[0].astype('float32')
        if self.faiss is not None:
            _, ids=self.faiss.search(np.asarray([vector]),min(settings.dense_top_k,len(self.chunks))); dense=[int(i) for i in ids[0] if i>=0]
        else:
            scores=self.vectors @ vector; dense=np.argsort(-scores)[:settings.dense_top_k].tolist()
        sparse=self._sparse_ranking(query)
        ranked=rrf_fuse(dense,sparse,[c['chunk_id'] for c in self.chunks],settings.rrf_k,settings.final_top_k)
        # Keep the strongest exact entity+intent hit in the final context. It is a
        # deterministic precision guard, while the remaining slots remain RRF-ranked.
        intents=[term for term in INTENT_TERMS if term in lowered] if (lowered:=question.lower()) else []
        phrases=self._entity_phrases(query)
        priority=[]
        if intents and phrases:
            for index in sparse:
                text=self._normal(self.chunks[index]['content'])
                if any(intent in text for intent in intents) and any(phrase in text for phrase in phrases):
                    priority.append(index)
        ordered=[]
        for index in priority + ranked + sparse:
            if index not in ordered: ordered.append(index)
        return [self.chunks[i] for i in ordered[:settings.final_top_k]]
    def answer(self, question, history=None):
        route=self.route(question)
        if route: return ROUTE_RESPONSES[route],[]
        chunks=self.retrieve(question,history)
        if not chunks: return SAFE,[]
        if self.generator: answer=self.generator(build_prompt(question,chunks,history))
        else:
            if not settings.gemini_api_key or not settings.gemini_model: return SAFE,chunks
            try:
                from google import genai
                client=genai.Client(api_key=settings.gemini_api_key)
                answer=client.models.generate_content(model=settings.gemini_model,contents=build_prompt(question,chunks,history),config={'temperature':0.2}).text
            except Exception as e: raise RuntimeError('Không thể kết nối dịch vụ tạo câu trả lời. Vui lòng thử lại sau.') from e
        return answer or SAFE,chunks
