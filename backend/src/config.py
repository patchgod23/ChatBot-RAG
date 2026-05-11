from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Ollama
    ollama_base_url: str = "http://host.docker.internal:11434"
    llama_model: str = "llama3.2"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    
    # Paths
    chroma_path: str = "./chroma_db"
    docs_path: str = "./data/docs"
    
    # RAG Parameters
    chunk_size: int = 500
    chunk_overlap: int = 100
    retriever_k: int = 4
    retriever_top_k: int = 3
    similarity_threshold: float = 10.0 # Umbral relajado para depuración
    memory_window_k: int = 5

    class Config:
        env_file = ".env"

settings = Settings()
