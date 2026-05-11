import logging
from typing import Optional, Dict, Any, Generator

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from langchain.memory import ConversationBufferWindowMemory

from src.config import settings
from src.chain.tools import buscar_en_polizas
from src.chain.prompts import RAG_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

# Herramientas y LLM
tools = [buscar_en_polizas]
_llm = ChatOllama(
    base_url=settings.ollama_base_url,
    model=settings.llama_model,
    temperature=0,
    streaming=True
).bind_tools(tools)

_session_memories: Dict[str, ConversationBufferWindowMemory] = {}

def _get_or_create_memory(session_id: str) -> ConversationBufferWindowMemory:
    if session_id not in _session_memories:
        _session_memories[session_id] = ConversationBufferWindowMemory(
            k=settings.memory_window_k,
            return_messages=True
        )
    return _session_memories[session_id]

def _is_chitchat(question: str) -> bool:
    """Query Classification: Solo detecta charla trivial si el mensaje es corto."""
    chitchat_signals = ["hola", "como estas", "buenos dias", "buenas tardes", "gracias", "quien eres", "amigo", "va todo"]
    q = question.lower().strip()
    words = q.split()
    if len(words) > 3:
        return False
    return any(signal in q for signal in chitchat_signals)

def reset_session(session_id: str) -> None:
    if session_id in _session_memories:
        del _session_memories[session_id]

def ask_stream(question: str, session_id: str, tipo_seguro: Optional[str] = None) -> Generator[str, None, None]:
    """Orquestación Directa con Agente y Tools."""
    if _is_chitchat(question):
        yield "¡Hola! Soy tu asistente de BICE Seguros. Puedo ayudarte con tus dudas sobre pólizas y coberturas de Auto, Vida y Hogar. ¿En qué te puedo ayudar?"
        return

    memory = _get_or_create_memory(session_id)
    chat_history = memory.load_memory_variables({}).get("history", [])
    
    messages = [
        SystemMessage(content=RAG_SYSTEM_PROMPT),
        *chat_history,
        HumanMessage(content=question)
    ]
    
    try:
        ai_msg = _llm.invoke(messages)
        
        if ai_msg.tool_calls:
            yield "🔎 *Consultando base de conocimientos de BICE...*\n\n"
            
            raw_args = ai_msg.tool_calls[0]['args']
            
            # Extracción recursiva y robusta del query string
            def extract_query(args):
                if isinstance(args, str): return args
                if not isinstance(args, dict): return str(args)
                
                # Prioridad a llaves conocidas
                for key in ['terminos_busqueda', 'query', 'content', 'value', 'question']:
                    if key in args and isinstance(args[key], str):
                        return args[key]
                
                # Si es un dict tipo {'query': {'type': 'string', 'value': '...'}}
                for val in args.values():
                    if isinstance(val, dict):
                        res = extract_query(val)
                        if res and res != 'string': return res
                    if isinstance(val, str) and val != 'string':
                        return val
                return str(args)

            query_val = extract_query(raw_args)
            
            # Si el modelo alucina y manda 'string' o algo vacío, usamos la pregunta original como fallback
            if not query_val or query_val.lower() == 'string':
                logger.warning("Alucinación detectada en tool call, usando pregunta original.")
                query_val = question

            logger.info("Ejecutando herramienta con query: %s", query_val)
            context = buscar_en_polizas.invoke({"terminos_busqueda": str(query_val)})
            
            # Formato estándar de LangChain para respuestas de herramientas
            tool_message = ToolMessage(
                tool_call_id=ai_msg.tool_calls[0]['id'],
                content=str(context)
            )
            
            messages.append(ai_msg)
            messages.append(tool_message)
            
            logger.info("Generando respuesta final con contexto...")
            full_res = ""
            for chunk in _llm.stream(messages):
                full_res += chunk.content
                yield chunk.content
            
            logger.info("Respuesta completada.")
            memory.save_context({"input": question}, {"output": full_res})
        else:
            full_res = ""
            for chunk in _llm.stream(messages):
                full_res += chunk.content
                yield chunk.content
            memory.save_context({"input": question}, {"output": full_res})
            
    except Exception as e:
        logger.error("Error en Agente: %s", e, exc_info=True)
        yield f"\n[Error de conexión con el motor de IA: {str(e)}]"
