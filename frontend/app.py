import os
import uuid
import logging
import requests
import streamlit as st

# Configuración de Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuración de API
API_URL = os.getenv("API_URL", "http://localhost:8000")
CHAT_ENDPOINT = f"{API_URL}/api/v1/chat"

st.set_page_config(
    page_title="BICE Seguros - Asistente IA",
    page_icon="🛡️",
    layout="centered"
)

# Estilos personalizados
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stChatFloatingInputContainer { background-color: #ffffff; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ BICE Seguros")
st.subheader("Asistente Virtual Pro (Streaming)")

# Inicialización de estado
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

# Sidebar
with st.sidebar:
    st.image("https://www.bicevida.cl/wp-content/uploads/2021/08/logo-bice-vida.png", width=150)
    st.divider()
    tipo_seguro = st.selectbox(
        "Filtrar por tipo de seguro:",
        ["Todos", "Auto", "Vida", "Hogar"]
    )
    
    st.divider()
    # Indicador de estado del backend
    try:
        health_url = f"{API_URL}/health"
        res = requests.get(health_url, timeout=2).json()
        if res.get("status") == "ok":
            st.caption(f"🟢 Backend listo ({res.get('chroma_docs', 0)} documentos)")
    except:
        st.caption("🟠 Backend iniciando (cargando modelos...)")
    
    if st.button("🗑️ Nueva Conversación", use_container_width=True):
        try:
            requests.delete(f"{API_URL}/api/v1/session/{st.session_state.session_id}")
        except: pass
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.rerun()

# Renderizado de historial
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Input de Usuario
if prompt := st.chat_input("¿En qué puedo ayudarte?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        # Contenedor para el streaming
        response_placeholder = st.empty()
        full_response = ""
        
        try:
            payload = {
                "question": prompt,
                "session_id": st.session_state.session_id,
                "tipo_seguro": tipo_seguro.lower() if tipo_seguro != "Todos" else None
            }
            
            # Petición con stream=True
            with requests.post(CHAT_ENDPOINT, json=payload, stream=True, timeout=90) as r:
                if r.status_code == 200:
                    # Leemos los chunks de la respuesta del backend
                    for chunk in r.iter_content(chunk_size=None, decode_unicode=True):
                        if chunk:
                            full_response += chunk
                            response_placeholder.markdown(full_response + "▌")
                    
                    response_placeholder.markdown(full_response)
                    st.session_state.messages.append({"role": "assistant", "content": full_response})
                else:
                    st.error(f"Error {r.status_code} del servidor")
                    
        except Exception as e:
            st.error("Error de conexión. Verifica el backend.")
            logger.error("Error: %s", e)
