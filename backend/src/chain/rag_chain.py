import os
# Desactivar telemetría de Chroma antes de cualquier import de src
os.environ["ANONYMIZED_TELEMETRY"] = "False"

import logging
from typing import Optional, Dict, Any, Generator

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.chat_history import InMemoryChatMessageHistory

from src.config import settings
from src.retrieval.retriever import get_relevant_chunks
from src.chain.prompts import RAG_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

# LLM Directo (Sin Tools para máxima velocidad)
_llm = ChatOllama(
    base_url=settings.ollama_base_url,
    model=settings.llama_model,
    temperature=0,
    streaming=True,
    num_ctx=2048,
    num_predict=512
)

# Diccionario para almacenar historiales por sesión
_session_histories: Dict[str, InMemoryChatMessageHistory] = {}

def get_session_history(session_id: str) -> InMemoryChatMessageHistory:
    if session_id not in _session_histories:
        _session_histories[session_id] = InMemoryChatMessageHistory()
    return _session_histories[session_id]

def reset_session(session_id: str) -> None:
    if session_id in _session_histories:
        _session_histories[session_id].clear()

def ask_stream(question: str, session_id: str, tipo_seguro: Optional[str] = None) -> Generator[str, None, None]:
    """Pipeline RAG Directo: Retrieval -> Prompt -> LLM."""
    try:
        history = get_session_history(session_id)
        
        # 1. Recuperación Directa
        chunks = get_relevant_chunks(question, tipo_seguro=tipo_seguro)
        
        if not chunks:
            context_text = "No se encontró información relevante."
        else:
            context_text = ""
            for i, c in enumerate(chunks):
                fuente = c.metadata.get("source", "Póliza BICE")
                context_text += f"--- FRAGMENTO {i+1} (Fuente: {fuente}) ---\n{c.page_content}\n\n"
            logger.info("Contexto recuperado (%d chunks)", len(chunks))

        # 2. Inyección de Contexto en el System Prompt
        system_content = RAG_SYSTEM_PROMPT.format(context=context_text)
        
        # 3. Preparar Mensajes
        messages = [
            SystemMessage(content=system_content),
            *history.messages,
            HumanMessage(content=question)
        ]
        
        # 4. Generación Final (Streaming)
        logger.info("Generando respuesta final...")
        full_res = ""
        for chunk in _llm.stream(messages):
            full_res += chunk.content
            yield chunk.content
        
        # 5. Guardar en memoria
        history.add_user_message(question)
        history.add_ai_message(full_res)
        
        logger.info("Respuesta completada.")

    except Exception as e:
        logger.error("Error en flujo RAG Directo: %s", e, exc_info=True)
        yield f"\n[Error técnico: {str(e)}]"
