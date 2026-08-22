"""
Interface de chat da Mirai Agentics (Streamlit).

Rode com:
    streamlit run app.py
"""

import os
import uuid
import base64
from pathlib import Path

import streamlit as st
from mirai_core import build_app, conversar

# ============================================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================================

st.set_page_config(
    page_title="Mirai Agentics",
    page_icon="assets/icone_mirai.png",
    layout="wide",
    initial_sidebar_state="expanded",
)

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

FUNCOES = {
    "Mirai Agentics": "Orquestrador de Agentes",
    "Breno": "Especialista Jurídico",
    "Leo": "Especialista Financeiro",
    "Alex": "Especialista em Vendas",
    "Cris": "Especialista em RH",
    "Lari": "Especialista em Marketing",
    "Carol": "Especialista em Atendimento",
}

LABELS = {
    "Mirai Agentics": "Mirai Agentics (Grupo)",
    "Breno": "Breno (Jurídico)",
    "Leo": "Leo (Financeiro)",
    "Alex": "Alex (Vendas)",
    "Cris": "Cris (RH)",
    "Lari": "Lari (Marketing)",
    "Carol": "Carol (Atendimento)",
}

CORES_AGENTE = {
    "Mirai Agentics": "#8B5CF6",
    "Breno": "#F5B82E",
    "Leo": "#7ED321",
    "Alex": "#22B8FF",
    "Cris": "#A855F7",
    "Lari": "#EC4899",
    "Carol": "#22D3EE",
}

# Sugestões principais. Não aparecem no sidebar.
SUGESTOES = [
    ("Lari", "Oi Agente Lari do marketing, o que você pode fazer por minha empresa?"),
    ("Mirai Agentics", "A Mirai Agentics cria agentes personalizados?"),
    ("Carol", "Oi Agente Carol, como você pode melhorar o fluxo de atendimentos?"),
    ("Cris", "Quantos agentes a Mirai Agentics têm?"),
    ("Alex", "Vocês Agentes são robôs humanoides? Vão substituir as pessoas?"),
]

FOLDER_INSTITUCIONAL_PDF = (
    "agentes/institucional/Folder_Institucional-MIRAI_AGENTICS.pdf"
)


# ============================================================
# UTILIDADES DE IMAGEM
# ============================================================

def imagem_base64(caminho: str) -> str:
    """Converte imagem local para data URI, para usar dentro dos cards HTML."""
    path = Path(caminho)
    if not path.exists():
        return ""
    mime = "image/png"
    if path.suffix.lower() in {".jpg", ".jpeg"}:
        mime = "image/jpeg"
    data = base64.b64encode(path.read_bytes()).decode("utf-8")
    return f"data:{mime};base64,{data}"


# ============================================================
# ESTILO VISUAL
# ============================================================

def aplica_estilo_futurista():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@500;600;700;800&family=Inter:wght@400;500;600;700&display=swap');

        :root {
            --mirai-bg: #020617;
            --mirai-panel: rgba(3, 8, 24, .84);
            --mirai-panel-2: rgba(6, 12, 31, .88);
            --mirai-text: #F8FAFC;
            --mirai-muted: #A6B0C3;
        }

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }

        .stApp {
            color: var(--mirai-text);
            background:
                radial-gradient(circle at 16% 8%, rgba(139,92,246,.16), transparent 26%),
                radial-gradient(circle at 88% 12%, rgba(34,211,238,.11), transparent 26%),
                radial-gradient(circle at 78% 75%, rgba(236,72,153,.075), transparent 25%),
                linear-gradient(180deg, #020617 0%, #020713 46%, #02040D 100%);
            background-attachment: fixed;
        }

        /* Grade tecnológica */
        .stApp::before {
            content: "";
            position: fixed;
            inset: 0;
            z-index: 0;
            pointer-events: none;
            opacity: .28;
            background-image:
                linear-gradient(rgba(45,109,255,.15) 1px, transparent 1px),
                linear-gradient(90deg, rgba(34,211,238,.09) 1px, transparent 1px);
            background-size: 58px 58px;
            mask-image: linear-gradient(to bottom, black 0%, rgba(0,0,0,.72) 48%, transparent 92%);
        }

        /* Pontos e brilhos no fundo */
        .stApp::after {
            content: "";
            position: fixed;
            inset: 0;
            z-index: 0;
            pointer-events: none;
            opacity: .55;
            background:
                radial-gradient(circle at 8% 14%, rgba(217,70,239,.95) 0 1px, transparent 2px),
                radial-gradient(circle at 14% 26%, rgba(59,130,246,.9) 0 1px, transparent 2px),
                radial-gradient(circle at 23% 8%, rgba(34,211,238,.85) 0 1px, transparent 2px),
                radial-gradient(circle at 34% 19%, rgba(139,92,246,.9) 0 1px, transparent 2px),
                radial-gradient(circle at 47% 7%, rgba(14,165,233,.85) 0 1px, transparent 2px),
                radial-gradient(circle at 63% 15%, rgba(236,72,153,.85) 0 1px, transparent 2px),
                radial-gradient(circle at 74% 8%, rgba(34,211,238,.9) 0 1px, transparent 2px),
                radial-gradient(circle at 89% 22%, rgba(168,85,247,.95) 0 1px, transparent 2px),
                radial-gradient(circle at 96% 10%, rgba(56,189,248,.85) 0 1px, transparent 2px),
                radial-gradient(circle at 20% 72%, rgba(59,130,246,.75) 0 1px, transparent 2px),
                radial-gradient(circle at 73% 66%, rgba(236,72,153,.75) 0 1px, transparent 2px),
                radial-gradient(circle at 92% 76%, rgba(34,211,238,.8) 0 1px, transparent 2px);
        }

        [data-testid="stAppViewContainer"] > .main,
        section[data-testid="stSidebar"] {
            position: relative;
            z-index: 1;
        }

        .block-container {
            max-width: 1420px;
            padding-top: 1rem;
            padding-bottom: 7rem;
        }

        header[data-testid="stHeader"] {
            background: transparent;
        }

        /* Sidebar */
        section[data-testid="stSidebar"] {
            background:
                radial-gradient(circle at 30% 0%, rgba(124,58,237,.14), transparent 30%),
                linear-gradient(180deg, rgba(2,6,23,.99), rgba(1,6,18,.99));
            border-right: 1px solid rgba(96,165,250,.24);
        }

        section[data-testid="stSidebar"] > div {
            padding-top: .85rem;
        }

        .sidebar-copy {
            color: #E5E7EB;
            line-height: 1.62;
            font-size: .88rem;
            margin: 8px 0 22px;
        }

        .sidebar-title {
            font-family: 'Orbitron', sans-serif;
            font-weight: 700;
            letter-spacing: .07em;
            color: #B56BFF;
            margin: 8px 0 12px;
            text-shadow: 0 0 13px rgba(168,85,247,.4);
        }

        .agent-card {
            display: flex;
            align-items: center;
            gap: 11px;
            min-height: 65px;
            padding: 8px 12px;
            margin: 0 0 10px;
            border-radius: 14px;
            border: 1px solid var(--agent-color);
            border-left: 2px solid var(--agent-color);
            background:
                linear-gradient(90deg, color-mix(in srgb, var(--agent-color) 10%, transparent), rgba(4,10,25,.84) 35%);
            box-shadow:
                0 0 12px color-mix(in srgb, var(--agent-color) 25%, transparent),
                inset 0 0 16px rgba(255,255,255,.015);
        }

        .agent-card.active {
            box-shadow:
                0 0 20px color-mix(in srgb, var(--agent-color) 48%, transparent),
                inset 0 0 20px color-mix(in srgb, var(--agent-color) 8%, transparent);
        }

        .agent-card img {
            width: 48px;
            height: 48px;
            object-fit: cover;
            border-radius: 50%;
            border: 1px solid var(--agent-color);
            box-shadow: 0 0 13px color-mix(in srgb, var(--agent-color) 55%, transparent);
            flex: 0 0 48px;
        }

        .agent-card.group img {
            border-radius: 12px;
        }

        .agent-name {
            font-weight: 700;
            color: #F8FAFC;
            font-size: .91rem;
            line-height: 1.15;
        }

        .agent-role {
            color: #A7B0C2;
            font-size: .73rem;
            margin-top: 4px;
            line-height: 1.2;
        }

        /* Hero */
        .mirai-hero {
            text-align: center;
            padding-top: 6px;
        }

        .mirai-sub {
            text-align: center;
            color: #E2E8F0;
            font-size: 1rem;
            margin: 4px 0 16px;
        }

        /* Painel principal */
        .mirai-panel {
            border: 1px solid rgba(96,165,250,.28);
            background:
                radial-gradient(circle at 30% 0%, rgba(124,58,237,.07), transparent 35%),
                linear-gradient(180deg, rgba(2,7,23,.78), rgba(2,6,18,.88));
            border-radius: 24px;
            padding: 19px 20px 15px;
            box-shadow:
                0 0 0 1px rgba(34,211,238,.025) inset,
                0 14px 55px rgba(0,0,0,.30),
                0 0 34px rgba(91,61,245,.06);
            margin-bottom: 18px;
        }

        .mirai-title {
            text-align: center;
            font-family: 'Orbitron', sans-serif;
            font-weight: 700;
            letter-spacing: .04em;
            color: #F8FAFC;
            font-size: .98rem;
            margin-bottom: 12px;
        }

        /* Botões/sugestões por agente */
        .stButton > button {
            border-radius: 14px !important;
            color: #F8FAFC !important;
            font-weight: 600 !important;
            min-height: 108px;
            background: rgba(5, 11, 27, .90) !important;
            transition: transform .18s ease, box-shadow .18s ease, border-color .18s ease;
        }

        .stButton > button:hover {
            transform: translateY(-2px);
        }

        .st-key-sug_lari button {
            border: 1px solid #EC4899 !important;
            box-shadow: 0 0 18px rgba(236,72,153,.22), inset 0 0 20px rgba(236,72,153,.04);
        }
        .st-key-sug_lari button:hover {
            box-shadow: 0 0 26px rgba(236,72,153,.42);
        }

        .st-key-sug_mirai button {
            border: 1px solid #2E86FF !important;
            box-shadow: 0 0 18px rgba(46,134,255,.22), inset 0 0 20px rgba(46,134,255,.04);
        }
        .st-key-sug_mirai button:hover {
            box-shadow: 0 0 26px rgba(46,134,255,.42);
        }

        .st-key-sug_carol button {
            border: 1px solid #22D3EE !important;
            box-shadow: 0 0 18px rgba(34,211,238,.22), inset 0 0 20px rgba(34,211,238,.04);
        }
        .st-key-sug_carol button:hover {
            box-shadow: 0 0 26px rgba(34,211,238,.42);
        }

        .st-key-sug_cris button {
            border: 1px solid #A855F7 !important;
            box-shadow: 0 0 18px rgba(168,85,247,.22), inset 0 0 20px rgba(168,85,247,.04);
        }
        .st-key-sug_cris button:hover {
            box-shadow: 0 0 26px rgba(168,85,247,.42);
        }

        .st-key-sug_alex button {
            border: 1px solid #2E86FF !important;
            box-shadow: 0 0 18px rgba(46,134,255,.22), inset 0 0 20px rgba(46,134,255,.04);
        }
        .st-key-sug_alex button:hover {
            box-shadow: 0 0 26px rgba(46,134,255,.42);
        }

        /* Chat */
        div[data-testid="stChatMessage"] {
            background: rgba(3,9,24,.74);
            border: 1px solid rgba(100,116,139,.24);
            border-radius: 18px;
            padding: 10px 14px;
            margin: 10px 0;
            box-shadow: 0 10px 28px rgba(0,0,0,.18);
        }

        /* Avatar maior no chat */
        div[data-testid="stChatMessageAvatarUser"],
        div[data-testid="stChatMessageAvatarAssistant"] {
            width: 86px !important;
            height: 86px !important;
            min-width: 86px !important;
        }

        div[data-testid="stChatMessageAvatarUser"] img,
        div[data-testid="stChatMessageAvatarAssistant"] img {
            width: 86px !important;
            height: 86px !important;
            object-fit: cover !important;
            border-radius: 50% !important;
            box-shadow: 0 0 24px rgba(236,72,153,.30);
        }

        div[data-testid="stChatMessage"] [data-testid="stAvatarIcon"] {
            width: 86px !important;
            height: 86px !important;
        }

        /* Nome do agente */
        .agent-chat-name {
            font-family: 'Orbitron', sans-serif;
            font-weight: 700;
            letter-spacing: .045em;
            font-size: .88rem;
            margin-bottom: 6px;
        }

        /* Input */
        div[data-testid="stChatInput"] {
            border-radius: 22px !important;
            border: 1px solid rgba(236,72,153,.88) !important;
            background:
                linear-gradient(90deg, rgba(38,10,54,.96), rgba(5,13,35,.98) 40%, rgba(3,20,45,.97)) !important;
            box-shadow:
                -8px 0 24px rgba(236,72,153,.26),
                8px 0 24px rgba(34,211,238,.22),
                0 0 18px rgba(139,92,246,.20) !important;
        }

        div[data-testid="stChatInput"]:focus-within {
            border-color: #22D3EE !important;
            box-shadow:
                -8px 0 28px rgba(236,72,153,.34),
                8px 0 30px rgba(34,211,238,.32) !important;
        }

        div[data-testid="stChatInput"] button {
            background: linear-gradient(135deg, #7C3AED, #0EA5E9) !important;
            color: white !important;
            border-radius: 999px !important;
        }

        /* Botão limpar */
        .st-key-apagar_conversa button {
            min-height: 40px !important;
            border: 1px solid rgba(236,72,153,.55) !important;
            color: #F472B6 !important;
            background: rgba(28,7,24,.72) !important;
            box-shadow: 0 0 13px rgba(236,72,153,.10);
        }

        .mirai-footer {
            text-align: center;
            color: #667085;
            font-size: .76rem;
            margin-top: 12px;
        }

        @media (max-width: 900px) {
            .block-container {
                padding-left: .7rem;
                padding-right: .7rem;
            }

            .stButton > button {
                min-height: 72px;
                font-size: .82rem !important;
            }

            .agent-card img {
                width: 42px;
                height: 42px;
                flex-basis: 42px;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


aplica_estilo_futurista()


# ============================================================
# APP / MEMÓRIA
# ============================================================

@st.cache_resource(show_spinner="Carregando os agentes da Mirai Agentics...")
def get_app():
    return build_app()


def nova_conversa():
    st.session_state.thread_id = str(uuid.uuid4())
    st.session_state.historico = []
    st.session_state.persona_atual = "Mirai Agentics"
    st.session_state.pop("pergunta_pendente", None)


if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

if "historico" not in st.session_state:
    st.session_state.historico = []

if "persona_atual" not in st.session_state:
    st.session_state.persona_atual = "Mirai Agentics"


# ============================================================
# SIDEBAR — SOMENTE AGENTES, SEM PERGUNTAS
# ============================================================

with st.sidebar:
    st.image(LOGO_PATH, use_container_width=True)

    st.markdown(
        """
        <div class="sidebar-copy">
            <b>Mirai Agentics:</b> O futuro da autonomia. Startup de Inteligência Artificial
            focada na criação de Agentes de IA personalizados para automação empresarial.
        </div>
        <div class="sidebar-title">CONHEÇA OS AGENTES</div>
        """,
        unsafe_allow_html=True,
    )

    persona_ativa = st.session_state.persona_atual

    for nome in [
        "Mirai Agentics",
        "Breno",
        "Leo",
        "Alex",
        "Cris",
        "Lari",
        "Carol",
    ]:
        cor = CORES_AGENTE[nome]
        avatar_uri = imagem_base64(
            IMAGEM_GRUPO if nome == "Mirai Agentics" else AVATARES[nome]
        )
        classe_ativa = "active" if nome == persona_ativa else ""
        classe_grupo = "group" if nome == "Mirai Agentics" else ""

        st.markdown(
            f"""
            <div
                class="agent-card {classe_ativa} {classe_grupo}"
                style="--agent-color:{cor};"
            >
                <img src="{avatar_uri}" alt="{nome}">
                <div>
                    <div class="agent-name">{LABELS[nome]}</div>
                    <div class="agent-role">{FUNCOES[nome]}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        """
        <div style="
            margin-top:22px;
            border:1px solid rgba(96,165,250,.22);
            border-radius:14px;
            padding:12px;
            background:rgba(4,10,25,.70);
            font-size:.78rem;">
            <b style="color:#8AB4FF;">✦ Mirai Agentics</b><br>
            <span style="color:#8E9AAF;">Autonomia • Inteligência • Resultados</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# CABEÇALHO
# ============================================================

st.markdown("<div class='mirai-hero'>", unsafe_allow_html=True)
logo_esq, logo_centro, logo_dir = st.columns([1, 1.55, 1])
with logo_centro:
    st.image(LOGO_PATH, use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

st.markdown(
    """
    <div class="mirai-sub">
        Converse com o orquestrador de agentes.
        Ele decide sozinho qual especialista te atende.
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# SUGESTÕES PRINCIPAIS
# ============================================================

if not st.session_state.historico:
    st.markdown("<div class='mirai-panel'>", unsafe_allow_html=True)
    st.markdown(
        "<div class='mirai-title'>✦ SUGESTÕES DE PERGUNTAS PARA NOSSOS AGENTES</div>",
        unsafe_allow_html=True,
    )

    cols = st.columns(5)

    chaves = {
        "Lari": "sug_lari",
        "Mirai Agentics": "sug_mirai",
        "Carol": "sug_carol",
        "Cris": "sug_cris",
        "Alex": "sug_alex",
    }

    for col, (agente, texto) in zip(cols, SUGESTOES):
        with col:
            if st.button(
                texto,
                key=chaves[agente],
                use_container_width=True,
            ):
                st.session_state.pergunta_pendente = texto
                st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


# ============================================================
# HISTÓRICO
# ============================================================

for msg in st.session_state.historico:
    if msg["role"] == "assistant":
        agente = msg.get("agente", "Mirai Agentics")
        avatar = AVATARES.get(agente, ICONE_INSTITUCIONAL)
        cor = CORES_AGENTE.get(agente, "#8B5CF6")

        with st.chat_message("assistant", avatar=avatar):
            st.markdown(
                f"<div class='agent-chat-name' style='color:{cor};'>"
                f"{agente.upper()}</div>",
                unsafe_allow_html=True,
            )
            st.markdown(msg["content"])
    else:
        with st.chat_message("user"):
            st.markdown(msg["content"])


# ============================================================
# INPUT / PROCESSAMENTO
# ============================================================

pergunta_digitada = st.chat_input("Digite sua pergunta...")
pergunta_pendente = st.session_state.pop("pergunta_pendente", None)
pergunta = pergunta_digitada or pergunta_pendente

if pergunta:
    st.session_state.historico.append(
        {"role": "user", "content": pergunta}
    )

    with st.chat_message("user"):
        st.markdown(pergunta)

    app = get_app()

    with st.spinner("Roteando para o agente certo..."):
        resposta, persona_detectada = conversar(
            app,
            pergunta,
            thread_id=st.session_state.thread_id,
        )

    if persona_detectada is not None:
        st.session_state.persona_atual = persona_detectada

    persona = st.session_state.persona_atual
    avatar_resposta = AVATARES.get(persona, ICONE_INSTITUCIONAL)
    cor = CORES_AGENTE.get(persona, "#8B5CF6")

    with st.chat_message("assistant", avatar=avatar_resposta):
        st.markdown(
            f"<div class='agent-chat-name' style='color:{cor};'>"
            f"{persona.upper()}</div>",
            unsafe_allow_html=True,
        )
        st.markdown(resposta)

        if (
            persona == "Mirai Agentics"
            and os.path.exists(FOLDER_INSTITUCIONAL_PDF)
        ):
            with open(FOLDER_INSTITUCIONAL_PDF, "rb") as pdf_file:
                st.download_button(
                    "📄 Baixar folder institucional (PDF)",
                    data=pdf_file.read(),
                    file_name="Folder_Mirai_Agentics.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )

    st.session_state.historico.append(
        {
            "role": "assistant",
            "content": resposta,
            "agente": persona,
        }
    )

    st.rerun()


# ============================================================
# LIMPAR / RODAPÉ
# ============================================================

clear_left, clear_mid, clear_right = st.columns([1.45, 1, 1.45])

with clear_mid:
    if st.button(
        "🗑️ Apagar conversa",
        key="apagar_conversa",
        use_container_width=True,
    ):
        nova_conversa()
        st.rerun()

st.markdown(
    """
    <div class="mirai-footer">
        Mirai Agentics — Inteligência que conecta. Agentes que transformam.
    </div>
    """,
    unsafe_allow_html=True,
)
