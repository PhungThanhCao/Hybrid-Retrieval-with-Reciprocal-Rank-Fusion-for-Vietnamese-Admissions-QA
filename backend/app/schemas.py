from pydantic import BaseModel, Field
class ChatTurn(BaseModel):
    role: str = Field(pattern='^(user|assistant)$')
    content: str = Field(min_length=1, max_length=1500)
class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    history: list[ChatTurn] = Field(default_factory=list, max_length=12)
class Source(BaseModel):
    ref_id: int; chunk_id: str; source: str; page: int | str | None = None; title: str; excerpt: str
class ChatResponse(BaseModel):
    answer: str; sources: list[Source]
