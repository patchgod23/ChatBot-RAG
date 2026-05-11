import os
import glob
import logging
from typing import List

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

from src.config import settings

logger = logging.getLogger(__name__)

def _get_tipo_seguro(filename: str) -> str:
    """Infiere el tipo de seguro basado en el nombre del archivo."""
    fn = filename.lower()
    if "auto" in fn:
        return "auto"
    if "vida" in fn:
        return "vida"
    if "hogar" in fn:
        return "hogar"
    return "otro"

def _load_documents(docs_path: str) -> List[Document]:
    """Carga documentos PDF y TXT desde una ruta."""
    pdf_pattern = os.path.join(docs_path, "*.pdf")
    txt_pattern = os.path.join(docs_path, "*.txt")
    files = glob.glob(pdf_pattern) + glob.glob(txt_pattern)
    
    docs: List[Document] = []
    for f in files:
        fname = os.path.basename(f)
        try:
            loader = PyPDFLoader(f) if f.endswith(".pdf") else TextLoader(f, encoding="utf-8")
            loaded_docs = loader.load()
            tipo = _get_tipo_seguro(fname)
            
            for d in loaded_docs:
                d.page_content = " ".join(d.page_content.split()).strip()
                d.metadata.update({"source": fname, "tipo_seguro": tipo})
            docs.extend(loaded_docs)
            logger.info("Cargado archivo: %s", fname)
        except Exception as e:
            logger.error("Error cargando %s: %s", fname, e)
            
    return docs

def ingest_documents() -> None:
    """Pipeline completo de ingesta de documentos."""
    logger.info("Iniciando pipeline de ingesta...")
    
    if not os.path.exists(settings.docs_path):
        os.makedirs(settings.docs_path, exist_ok=True)
        logger.warning("Ruta de documentos vacía: %s", settings.docs_path)
        return

    documents = _load_documents(settings.docs_path)
    if not documents:
        logger.warning("No se encontraron documentos para ingestar.")
        return

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap
    )
    
    chunks = splitter.split_documents(documents)
    
    # Indexar chunks
    counts: dict[str, int] = {}
    for c in chunks:
        src = c.metadata["source"]
        counts[src] = counts.get(src, 0) + 1
        c.metadata["chunk_index"] = counts[src]

    logger.info("Generados %d chunks. Indexando en ChromaDB...", len(chunks))

    embeddings = HuggingFaceEmbeddings(
        model_name=settings.embedding_model
    )
    
    Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=settings.chroma_path
    )
    
    logger.info("Pipeline de ingesta finalizado con éxito.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ingest_documents()
