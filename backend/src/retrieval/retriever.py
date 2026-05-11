import logging
from typing import Optional, List, Any

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

from src.config import settings

logger = logging.getLogger(__name__)

class RetrieverUnavailableError(Exception):
    """Excepción para cuando ChromaDB no está disponible o falla la conexión."""
    pass

_embeddings = None
_vector_store = None

def get_vector_store() -> Chroma:
    """Obtiene la instancia del vector store persistido con caché para evitar recargas lentas."""
    global _embeddings, _vector_store
    
    try:
        if _embeddings is None:
            logger.info("Cargando modelo de embeddings: %s", settings.embedding_model)
            _embeddings = HuggingFaceEmbeddings(model_name=settings.embedding_model)
        
        if _vector_store is None:
            logger.info("Inicializando conexión con ChromaDB en: %s", settings.chroma_path)
            _vector_store = Chroma(
                persist_directory=settings.chroma_path,
                embedding_function=_embeddings
            )
        return _vector_store
    except Exception as e:
        logger.error("ChromaDB no disponible: %s", e, exc_info=True)
        raise RetrieverUnavailableError(f"No se pudo conectar a ChromaDB: {e}") from e

def get_relevant_chunks(query: Any, tipo_seguro: Optional[str] = None) -> List[Document]:
    """Recupera chunks relevantes asegurando que la query sea un string."""
    
    # Extracción robusta si llega un diccionario
    if isinstance(query, dict):
        query = query.get("query") or query.get("content") or query.get("value") or list(query.values())[0]
    
    query = str(query)

    try:
        store = get_vector_store()
    except RetrieverUnavailableError:
        # Re-elevamos para que la API lo capture
        raise

    if not store:
        return []

    # Inferencia de filtro
    q_lower = query.lower()
    if not tipo_seguro:
        for t in ["auto", "vida", "hogar"]:
            if t in q_lower:
                tipo_seguro = t
                break

    filter_dict = None
    if tipo_seguro and tipo_seguro.lower() != "todos":
        filter_dict = {"tipo_seguro": tipo_seguro.lower()}

    try:
        results = store.similarity_search_with_score(
            query, 
            k=settings.retriever_k, 
            filter=filter_dict
        )
    except Exception as e:
        logger.error("Error en búsqueda de similitud: %s", e)
        return []

    if not results:
        return []

    # Reranking heurístico por score
    sorted_results = sorted(results, key=lambda x: x[1])
    
    # Retrieval Guard con Logging
    best_score = sorted_results[0][1]
    logger.info("Búsqueda finalizada. Mejor score: %f (umbral: %f)", best_score, settings.similarity_threshold)
    
    if best_score > settings.similarity_threshold:
        logger.warning("Guard Trigger: Similitud insuficiente (%f > %f)", best_score, settings.similarity_threshold)
        return []

    return [doc for doc, score in sorted_results[:settings.retriever_top_k]]
