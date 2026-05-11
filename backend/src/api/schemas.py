from pydantic import BaseModel, Field
from typing import Optional, List

class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)
    session_id: str = Field(..., min_length=1)
    # Aceptamos mayúsculas y minúsculas para evitar errores 422
    tipo_seguro: Optional[str] = Field(None, pattern="^(auto|vida|hogar|Auto|Vida|Hogar|Todos)$")

class ChatResponse(BaseModel):
    answer: str
    sources: List[str]
    chunks_used: int
    session_id: str

class HealthResponse(BaseModel):
    status: str
    chroma_docs: int
