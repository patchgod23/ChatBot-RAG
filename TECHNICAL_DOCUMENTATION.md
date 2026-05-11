# BICE Seguros - Asistente RAG Pro (Documentación Técnica)

Este proyecto es un sistema de **Generación Aumentada por Recuperación (RAG)** de alto rendimiento, diseñado para la consulta automatizada de pólizas de seguros mediante IA generativa local.

---

## 🚀 El "Pitch" (Cómo explicarlo en 1 minuto)

> "Desarrollé un asistente de IA para **BICE Seguros** que permite consultar pólizas complejas usando lenguaje natural. A diferencia de un chat convencional, utiliza una arquitectura **RAG Directa**, lo que garantiza que las respuestas se basen exclusivamente en documentos oficiales de la compañía. Está optimizado para correr localmente con **Ollama**, asegurando **privacidad de datos** (los datos nunca salen de la infraestructura) y **costo cero** de inferencia."

---

## 🏗️ Arquitectura y Decisiones de Ingeniería

### 1. Pipeline RAG Directo vs. Agentes
*   **Decisión**: Migramos de un enfoque basado en Agentes (Tool-calling) a un Pipeline RAG Directo (Retrieval -> Context -> LLM).
*   **Justificación**: Los agentes requieren dos llamadas al LLM (una para decidir la herramienta y otra para responder). En entornos de CPU, esto duplicaba la latencia. El pipeline directo redujo el tiempo de respuesta en un **50%** manteniendo la precisión.

### 2. Stack Tecnológico
*   **Orquestador**: LangChain 0.2+ (usando el estándar moderno LCEL).
*   **Embeddings**: `all-MiniLM-L6-v2` (80MB). Elegido por su bajísima latencia en CPU frente a modelos pesados como BGE-M3, sin sacrificar precisión en textos cortos.
*   **LLM**: Llama 3.2 (vía Ollama). Optimizado con `num_ctx=2048` para limitar el uso de memoria.
*   **Vector Store**: ChromaDB con persistencia local.
*   **Frontend**: Streamlit con CSS personalizado (Forced Dark Mode) y lógica de "Sticky Input".

---

## 🛡️ Desafíos y Soluciones (Tus "War Stories")

### Desafío 1: Hallucinación en Exclusiones de Pólizas
*   **Problema**: El modelo confundía coberturas con exclusiones debido a la estructura de las listas en los PDFs.
*   **Solución**: Implementamos **"Context Labeling"**. Cada fragmento de texto entregado a la IA es etiquetado con su fuente y sección. Además, reforzamos el *System Prompt* con reglas de "Analista de Riesgos" para dar prioridad a las restricciones negativas.

### Desafío 2: Latencia de "Cold Start"
*   **Problema**: La primera consulta del usuario tardaba mucho porque los modelos no estaban en RAM.
*   **Solución**: Implementamos un **Warm-up Step** en el evento de inicio (startup) de FastAPI. El servidor realiza una inferencia "fantasma" al arrancar, dejando el modelo listo para el primer usuario.

### Desafío 3: Interfaz "Desencajada"
*   **Problema**: Streamlit perdía el foco del chat al procesar respuestas largas.
*   **Solución**: Refactorizamos el frontend moviendo el `st.chat_input` fuera de las columnas para hacerlo "Sticky" y usamos `st.status` para dar feedback visual inmediato al usuario mientras la IA "piensa".

---

## ❓ Preguntas de Entrevista (Q&A)

**Q: ¿Por qué no usaste OpenAI/ChatGPT API?**
> *A: Por dos razones críticas en banca/seguros: **Seguridad y Costo**. Usando Ollama local, garantizamos que la información sensible de las pólizas no sea enviada a servidores externos, cumpliendo con normativas de privacidad.*

**Q: ¿Cómo manejas el historial de la conversación?**
> *A: Utilizamos `InMemoryChatMessageHistory` vinculado a un `session_id`. Esto permite que el usuario haga preguntas de seguimiento (ej: "¿Y cuál es el deducible?") sin tener que repetir de qué seguro está hablando.*

**Q: ¿Qué métricas usarías para evaluar este RAG?**
> *A: Implementaría **RAGAS** para medir: 1. Faithfulness (que no invente), 2. Answer Relevance (que responda lo que se le pide) y 3. Context Precision (que el buscador traiga los fragmentos correctos).*

---

## 💡 Conceptos Clave para Dominar
*   **Chunking**: Dividimos los PDFs en trozos de 500 caracteres con solapamiento para no perder el contexto en los cortes.
*   **Embedding**: Convertimos texto en vectores matemáticos para que la IA busque por "significado" y no solo por "palabras exactas".
*   **Prompt Engineering**: Usamos un rol de experto y reglas de seguridad para "blindar" al modelo contra errores.
