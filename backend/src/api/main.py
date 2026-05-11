import os
# Desactivar telemetría de Chroma
os.environ["ANONYMIZED_TELEMETRY"] = "False"

import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes.chat import router as chat_router
from src.api.schemas import HealthResponse
from src.retrieval.retriever import get_vector_store

# Configuración de Logging Global
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="BICE Seguros RAG API",
    description="Servicio backend para consulta de pólizas usando LangChain y Ollama",
    version="1.0.0"
)

@app.on_event("startup")
async def startup_event():
    """Carga los modelos pesados al iniciar el servidor para evitar demoras en la primera consulta."""
    logger.info("Iniciando pre-carga de modelos y base de datos...")
    try:
        get_vector_store()
        
        # Warm-up del LLM para evitar lag inicial (Cold Start)
        from src.chain.rag_chain import _llm
        try:
            _llm.invoke("Hola")
            logger.info("Warm-up del LLM completado con éxito.")
        except Exception as llm_e:
            logger.warning("No se pudo realizar el warm-up del LLM: %s", llm_e)
            
        logger.info("Pre-carga completada con éxito.")
    except Exception as e:
        logger.error("Error durante la pre-carga: %s", e)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rutas
app.include_router(chat_router, prefix="/api/v1")

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    body = await request.body()
    logger.error("Error de validación! Body: %s | Errores: %s", body.decode(), exc.errors())
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": body.decode()},
    )

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Verifica el estado del sistema y la base de datos vectorial."""
    chroma_count = 0
    store = get_vector_store()
    if store:
        try:
            chroma_count = store._collection.count()
        except Exception as e:
            logger.error("Error al contar documentos en Chroma: %s", e)
    
    return HealthResponse(status="ok", chroma_docs=chroma_count)
