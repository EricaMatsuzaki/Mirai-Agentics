"""
Interface de chat da Mirai Agentics (Streamlit).

Rode com: streamlit run app.py
"""

import os
import uuid
import streamlit as st
from mirai_core import build_app, conversar

st.set_page_config(
    page_title="Mirai Agentics",
    page_icon="assets/icone_mirai.png",
    layout="centered",
)

# Ícone institucional quadrado/circular (só a letra "M") -- usado no avatar do chat.
# É diferente do logotipo completo "MIRAI AGENTICS" (LOGO_PATH), que é retangular e
# fica cortado de forma estranha quando o Streamlit tenta encaixá-lo num círculo de avatar.
ICONE_INSTITUCIONAL = "assets/icone_mirai.png"
LOGO_PATH = "assets/logo_mirai_agentics.png"
IMAGEM_GRUPO = "assets/grupo_mirai_agentics.png"

AVATARES = {
    "Breno": "assets/avatar_breno.png",
    "Leo": "assets/avatar_leo.png",
    "Alex": "assets/avatar_alex.png",
    "Cris": "assets/avatar_cris.png",
    "Lari": "assets/avatar_lari.png",
    "Carol": "assets/avatar_carol.png",
    "Mirai Agentics": ICONE_INSTITUCIONAL,
}

POSTERS = {
    "Mirai Agentics": ("Mirai Agentics (Grupo)", IMAGEM_GRUPO),
    "Breno": ("Breno (Jurídico)", "assets/poster_breno.png"),
    "Leo": ("Leo (Financeiro)", "assets/poster_leo.png"),
    "Alex": ("Alex (Vendas)", "assets/poster_alex.png"),
    "Cris": ("Cris (RH)", "assets/poster_cris.png"),
    "Lari": ("Lari (Marketing)", "assets/poster_lari.png"),
    "Carol": ("Carol (Atendimento)", "assets/poster_carol.png"),
}

TAGLINE = (
    "**Mirai Agentics:** O futuro da autonomia. Startup de Inteligência Artificial "
    "focada na criação de Agentes de IA personalizados para automação empresarial."
)

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

# PDF institucional (folder/apresentação) oferecido como anexo quando a conversa é institucional.
# Se o arquivo não existir no repositório, o botão simplesmente não aparece -- não quebra o app.
FOLDER_INSTITUCIONAL_PDF = "agentes/institucional/Folder_Institucional-MIRAI_AGENTICS.pdf"


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
    st.session_state.persona_atual = "Mirai Agentics"


if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

if "historico" not in st.session_state:
    st.session_state.historico = []

# Guarda qual foi o último agente que efetivamente respondeu -- usado para:
#  1) manter o avatar certo quando uma resposta não tem indício explícito de persona
#     (corrige o bug do avatar "sumindo" e caindo pro logo institucional à toa);
#  2) abrir automaticamente o pôster daquele agente na sidebar;
#  3) decidir quando mostrar a imagem do grupo (perguntas institucionais).
if "persona_atual" not in st.session_state:
    st.session_state.persona_atual = "Mirai Agentics"

with st.sidebar:
    st.image(LOGO_PATH, width=200)
    st.markdown(TAGLINE)
    st.markdown("### Conheça os agentes")

    persona_ativa = st.session_state.persona_atual

    for nome, (label, caminho) in POSTERS.items():
        # O pôster do agente (ou do grupo, se a conversa for institucional) que está
        # atendendo agora abre sozinho -- os demais ficam fechados, mas continuam
        # clicáveis a qualquer momento.
        with st.expander(label, expanded=(nome == persona_ativa)):
            st.image(caminho, use_container_width=True)

for msg in st.session_state.historico:
    avatar = AVATARES.get(msg.get("agente"), ICONE_INSTITUCIONAL) if msg["role"] == "assistant" else None
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])

st.image(LOGO_PATH, width=300)
st.caption("Converse com o orquestrador de agentes. Ele decide sozinho qual especialista te atende.")

pergunta = st.chat_input("Digite sua pergunta...")

if pergunta:
    st.session_state.historico.append({"role": "user", "content": pergunta})
    with st.chat_message("user"):
        st.markdown(pergunta)

    app = get_app()

    with st.spinner("Roteando para o agente certo..."):
        resposta, persona_detectada = conversar(app, pergunta, thread_id=st.session_state.thread_id)

    # Se a resposta não trouxe nenhum indício de troca de agente (persona_detectada is None),
    # mantemos o último agente que estava atendendo, em vez de resetar pro logo institucional.
    if persona_detectada is not None:
        st.session_state.persona_atual = persona_detectada
    persona = st.session_state.persona_atual

    avatar_resposta = AVATARES.get(persona, ICONE_INSTITUCIONAL)
    cor = CORES_AGENTE.get(persona, "#5B3DF5")

    with st.chat_message("assistant", avatar=avatar_resposta):
        st.markdown(
            f"<div style='border-left: 3px solid {cor}; padding-left: 10px;'>"
            f"<b style='color:{cor}'>{persona}</b><br>{resposta}</div>",
            unsafe_allow_html=True,
        )
        # Oferece o folder institucional em PDF como anexo -- só aparece se o arquivo
        # existir no repositório. Continua funcionando normalmente se ele não existir.
        if persona == "Mirai Agentics" and os.path.exists(FOLDER_INSTITUCIONAL_PDF):
            with open(FOLDER_INSTITUCIONAL_PDF, "rb") as pdf_file:
                st.download_button(
                    "📄 Baixar folder institucional (PDF)",
                    data=pdf_file.read(),
                    file_name="Folder_Mirai_Agentics.pdf",
                    mime="application/pdf",
                )

    st.session_state.historico.append({"role": "assistant", "content": resposta, "agente": persona})

st.divider()
if st.button("🗑️  Apagar conversa", use_container_width=True):
    nova_conversa()
    st.rerun()
   
