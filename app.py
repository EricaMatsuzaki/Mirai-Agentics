"""
Interface de chat da Mirai Agentics (Streamlit).

Rode com: streamlit run app.py
"""

import uuid
import streamlit as st
from mirai_core import build_app, conversar

st.set_page_config(
    page_title="Mirai Agentics",
    page_icon="assets/logo_mirai_agentics.png",
    layout="centered",
)

AVATARES = {
    "Breno": "assets/avatar_breno.png",
    "Leo": "assets/avatar_leo.png",
    "Alex": "assets/avatar_alex.png",
    "Cris": "assets/avatar_cris.png",
    "Lari": "assets/avatar_lari.png",
    "Carol": "assets/avatar_carol.png",
    "Mirai Agentics": "assets/logo_mirai_agentics.png",
}

POSTERS = {
    "Breno (Jurídico)": "assets/poster_breno.png",
    "Leo (Financeiro)": "assets/poster_leo.png",
    "Alex (Vendas)": "assets/poster_alex.png",
    "Cris (RH)": "assets/poster_cris.png",
    "Lari (Marketing)": "assets/poster_lari.png",
    "Carol (Atendimento)": "assets/poster_carol.png",
}

LOGO_PATH = "assets/logo_mirai_agentics.png"

# Cor de destaque por agente -- usada na barrinha lateral de cada balão de resposta
CORES_AGENTE = {
    "Breno": "#D4AF37",
    "Leo": "#7ED321",
    "Alex": "#2E86FF",
    "Cris": "#9B59F6",
    "Lari": "#EC4899",
    "Carol": "#22D3EE",
    "Mirai Agentics": "#5B3DF5",
}


# --- Visual futurista: fontes, brilho neon nos botões/inputs, cards da sidebar ---
def aplica_estilo_futurista():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@600;800&display=swap');

        h1, h2, h3 {
            font-family: 'Orbitron', sans-serif !important;
            text-shadow: 0 0 10px rgba(91, 61, 245, 0.55);
        }

        /* Campo de digitar pergunta */
        div[data-testid="stChatInput"] {
            border-radius: 18px !important;
            border: 1px solid rgba(91, 61, 245, 0.6) !important;
            box-shadow: 0 0 14px rgba(91, 61, 245, 0.35);
            background: rgba(20, 27, 51, 0.6) !important;
        }
        div[data-testid="stChatInput"]:focus-within {
            box-shadow: 0 0 20px rgba(34, 211, 238, 0.55);
            border-color: rgba(34, 211, 238, 0.8) !important;
        }

        /* Botão de enviar (seta) e botões em geral */
        button[kind="primary"], div[data-testid="stChatInput"] button, .stButton button {
            background: linear-gradient(135deg, #5B3DF5, #22D3EE) !important;
            border: none !important;
            color: white !important;
            border-radius: 12px !important;
            box-shadow: 0 0 10px rgba(91, 61, 245, 0.6);
            transition: box-shadow 0.2s ease, transform 0.2s ease;
        }
        button[kind="primary"]:hover, div[data-testid="stChatInput"] button:hover, .stButton button:hover {
            box-shadow: 0 0 18px rgba(34, 211, 238, 0.85);
            transform: translateY(-1px);
        }

        /* Balões de mensagem do chat */
        div[data-testid="stChatMessage"] {
            border-radius: 16px;
            border: 1px solid rgba(91, 61, 245, 0.25);
            box-shadow: 0 0 10px rgba(91, 61, 245, 0.12);
            padding: 4px;
        }

        /* Cards expansíveis dos agentes na sidebar */
        div[data-testid="stExpander"] {
            border: 1px solid rgba(91, 61, 245, 0.35) !important;
            border-radius: 14px !important;
            box-shadow: 0 0 8px rgba(91, 61, 245, 0.2);
            overflow: hidden;
        }
        div[data-testid="stExpander"]:hover {
            box-shadow: 0 0 16px rgba(34, 211, 238, 0.4);
        }

        /* Legenda/caption com leve brilho */
        .stCaption, [data-testid="stCaptionContainer"] {
            text-shadow: 0 0 6px rgba(91, 61, 245, 0.3);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


aplica_estilo_futurista()


@st.cache_resource(show_spinner="Carregando os agentes da Mirai Agentics...")
def get_app():
    return build_app()


def nova_conversa():
    st.session_state.thread_id = str(uuid.uuid4())
    st.session_state.historico = []


with st.sidebar:
    st.image(LOGO_PATH, width=200)
    st.markdown("### Conheça os agentes")
    for nome, caminho in POSTERS.items():
        with st.expander(nome):
            st.image(caminho, use_container_width=True)

    st.divider()
    if st.button("🗑️  Apagar conversa", use_container_width=True):
        nova_conversa()
        st.rerun()

st.image(LOGO_PATH, width=300)
st.caption("Converse com o orquestrador de agentes. Ele decide sozinho qual especialista te atende.")

if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

if "historico" not in st.session_state:
    st.session_state.historico = []

for msg in st.session_state.historico:
    avatar = AVATARES.get(msg.get("agente"), LOGO_PATH) if msg["role"] == "assistant" else None
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])

pergunta = st.chat_input("Digite sua pergunta...")

if pergunta:
    st.session_state.historico.append({"role": "user", "content": pergunta})
    with st.chat_message("user"):
        st.markdown(pergunta)

    app = get_app()

    with st.spinner("Roteando para o agente certo..."):
        resposta, persona = conversar(app, pergunta, thread_id=st.session_state.thread_id)

    # A persona já é conhecida ANTES de abrir o balão -- assim o avatar certo
    # aparece já na resposta ao vivo, não só depois de recarregar a página.
    avatar_resposta = AVATARES.get(persona, LOGO_PATH)
    cor = CORES_AGENTE.get(persona, "#5B3DF5")

    with st.chat_message("assistant", avatar=avatar_resposta):
        st.markdown(
            f"<div style='border-left: 3px solid {cor}; padding-left: 10px;'>"
            f"<b style='color:{cor}'>{persona}</b><br>{resposta}</div>",
            unsafe_allow_html=True,
        )

    st.session_state.historico.append({"role": "assistant", "content": resposta, "agente": persona})
