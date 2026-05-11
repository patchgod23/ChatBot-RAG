import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from src.api.schemas import ChatRequest
from src.chain.rag_chain import ask_stream, reset_session
from src.retrieval.retriever import RetrieverUnavailableError

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """Endpoint que devuelve un stream de texto."""
    try:
        # Devolvemos un StreamingResponse que consume el generador ask_stream
        return StreamingResponse(
            ask_stream(
                question=request.question,
                session_id=request.session_id,
                tipo_seguro=request.tipo_seguro
            ),
            media_type="text/plain"
        )
    except RetrieverUnavailableError as e:
        logger.error("Base de conocimiento no disponible: %s", e)
        raise HTTPException(status_code=503, detail="Base de conocimiento no disponible.")
    except Exception as e:
        logger.error("Error inesperado: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.delete("/session/{session_id}")
async def clear_session_endpoint(session_id: str):
    reset_session(session_id)
    return {"message": f"Sesión {session_id} limpiada"}
