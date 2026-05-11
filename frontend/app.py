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

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="BICE Seguros AI",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- ESTILOS DARK MODE PULIDOS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    .stApp {
        background-color: #0e1117 !important;
        color: #ffffff !important;
    }

    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display:none;}

    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #161b22 !important;
        border-right: 1px solid #30363d !important;
    }

    /* Burbujas de Chat */
    .stChatMessage {
        border-radius: 12px !important;
        padding: 1.5rem !important;
        margin-bottom: 1.5rem !important;
        max-width: 80% !important;
    }

    [data-testid="stChatMessageUser"] {
        background-color: #1e3a8a !important;
        border: 1px solid #2563eb !important;
        margin-left: auto !important;
    }

    [data-testid="stChatMessageAssistant"] {
        background-color: #1f2937 !important;
        border: 1px solid #374151 !important;
        margin-right: auto !important;
    }

    /* Header Compacto */
    .bice-header {
        background: linear-gradient(90deg, #001a33 0%, #003366 100%);
        padding: 1.2rem;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 2rem;
        border: 1px solid #004d99;
    }

    /* Espacio para que el input no tape el último mensaje */
    .block-container {
        padding-bottom: 150px !important;
    }
    
    /* Forzar el Input al fondo (Sticky) */
    .stChatFloatingInputContainer {
        bottom: 20px !important;
        background-color: #0e1117 !important;
        padding: 1rem !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://www.bicevida.cl/wp-content/uploads/2021/08/logo-bice-vida.png", width=180)
    st.divider()
    
    try:
        res = requests.get(f"{API_URL}/health", timeout=2).json()
        if res.get("status") == "ok":
            st.success("🟢 Sistema Online")
    except:
        st.error("🔴 Backend Offline")

    if st.button("🗑️ Nueva Consulta", use_container_width=True):
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.rerun()

    st.caption("BICE AI v1.6")

# --- CHAT CONTAINER ---
col1, col2, col3 = st.columns([1, 5, 1])

with col2:
    st.markdown("""
        <div class="bice-header">
            <h2 style='margin:0; font-weight:700; color:white;'>BICE Seguros</h2>
            <p style='margin:0; opacity: 0.8; color:white;'>Asistente Inteligente de Pólizas</p>
        </div>
    """, unsafe_allow_html=True)

    # Inicialización
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "¡Hola! Soy tu asistente **BICE**. ¿Sobre qué póliza tienes dudas?"}
        ]

    # Renderizado histórico
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# --- INPUT (Fuera de columnas para ser Sticky) ---
if prompt := st.chat_input("Escribe tu consulta aquí..."):
    # Añadir mensaje de usuario al estado
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Rerender para mostrar el mensaje del usuario inmediatamente
    st.rerun()

# Lógica para procesar la respuesta si el último mensaje es del usuario
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    last_user_msg = st.session_state.messages[-1]["content"]
    
    with col2:
        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            full_response = ""
            
            with st.status("🔍 Analizando documentos oficiales...", expanded=False) as status:
                try:
                    payload = {"question": last_user_msg, "session_id": st.session_state.session_id}
                    with requests.post(CHAT_ENDPOINT, json=payload, stream=True, timeout=90) as r:
                        if r.status_code == 200:
                            for chunk in r.iter_content(chunk_size=None, decode_unicode=True):
                                if chunk:
                                    full_response += chunk
                                    response_placeholder.markdown(full_response + "▌")
                            
                            response_placeholder.markdown(full_response)
                            st.session_state.messages.append({"role": "assistant", "content": full_response})
                            status.update(label="✅ Consulta finalizada", state="complete")
                        else:
                            st.error("Error en el servidor.")
                except Exception as e:
                    st.error("Error de conexión.")
