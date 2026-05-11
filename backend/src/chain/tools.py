from langchain_core.tools import tool
from src.retrieval.retriever import get_relevant_chunks

@tool
def buscar_en_polizas(terminos_busqueda: str) -> str:
    """
    Busca información oficial en las pólizas de BICE Seguros Chile. 
    Argumento 'terminos_busqueda': Un string con los conceptos a buscar (ej: 'coberturas de robo auto').
    """
    chunks = get_relevant_chunks(terminos_busqueda)
    if not chunks:
        return "No se encontró información relevante en los documentos de seguros de BICE."
    
    context = "\n\n".join([f"Documento: {c.metadata.get('source')}\nContenido: {c.page_content}" for c in chunks])
    return context
