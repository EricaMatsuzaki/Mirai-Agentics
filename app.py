"""
Interface de chat da Mirai Agentics (Streamlit).

Rode com:
    streamlit run app.py
"""

import os
import uuid
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

POSTERS = {
    "Mirai Agentics": ("Mirai Agentics (Grupo)", IMAGEM_GRUPO),
    "Breno": ("Breno (Jurídico)", "assets/poster_breno.png"),
    "Leo": ("Leo (Financeiro)", "assets/poster_leo.png"),
    "Alex": ("Alex (Vendas)", "assets/poster_alex.png"),
    "Cris": ("Cris (RH)", "assets/poster_cris.png"),
    "Lari": ("Lari (Marketing)", "assets/poster_lari.png"),
    "Carol": ("Carol (Atendimento)", "assets/poster_carol.png"),
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

CORES_AGENTE = {
    "Breno": "#D4AF37",
    "Leo": "#7ED321",
    "Alex": "#2E86FF",
    "Cris": "#9B59F6",
    "Lari": "#EC4899",
    "Carol": "#22D3EE",
    "Mirai Agentics": "#8B5CF6",
}

# Uma pergunta de entrada para cada agente
PERGUNTAS_AGENTES = {
    "Mirai Agentics": "Como a Mirai Agentics pode ajudar minha empresa?",
    "Breno": "Breno, você pode me ajudar com contratos e documentos jurídicos?",
    "Leo": "Leo, como você pode ajudar a organizar o financeiro da minha empresa?",
    "Alex": "Alex, quais estratégias de vendas podem aumentar meus resultados?",
    "Cris": "Cris, como você pode ajudar no recrutamento e na gestão de pessoas?",
    "Lari": "Lari, como você pode fortalecer minha marca e atrair mais clientes?",
    "Carol": "Carol, como você pode melhorar a experiência e o atendimento aos meus clientes?",
}

FOLDER_INSTITUCIONAL_PDF = (
    "agentes/institucional/Folder_Institucional-MIRAI_AGENTICS.pdf"
)

TAGLINE = (
    "<b>Mirai Agentics:</b> O futuro da autonomia. Startup de Inteligência Artificial "
    "focada na criação de Agentes de IA personalizados para automação empresarial."
)


# ============================================================
# ESTILO VISUAL
# ============================================================

def aplica_estilo_futurista():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@500;600;700;800&family=Inter:wght@400;500;600;700&display=swap');

        :root {
            --mirai-roxo: #8B5CF6;
            --mirai-azul: #2E86FF;
            --mirai-ciano: #22D3EE;
            --mirai-rosa: #EC4899;
            --mirai-fundo: #030712;
            --mirai-card: rgba(7, 12, 28, 0.84);
            --mirai-borda: rgba(99, 102, 241, 0.28);
            --mirai-texto: #F8FAFC;
            --mirai-muted: #94A3B8;
        }

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }

        /* Fundo geral */
        .stApp {
            color: var(--mirai-texto);
            background:
                radial-gradient(circle at 18% 10%, rgba(91,61,245,.16), transparent 28%),
                radial-gradient(circle at 85% 18%, rgba(34,211,238,.10), transparent 24%),
                radial-gradient(circle at 72% 80%, rgba(236,72,153,.08), transparent 22%),
                linear-gradient(180deg, #020617 0%, #050817 48%, #02040c 100%);
            background-attachment: fixed;
        }

        .stApp::before {
            content: "";
            position: fixed;
            inset: 0;
            pointer-events: none;
            opacity: .16;
            background-image:
                linear-gradient(rgba(99,102,241,.22) 1px, transparent 1px),
                linear-gradient(90deg, rgba(34,211,238,.12) 1px, transparent 1px);
            background-size: 56px 56px;
            mask-image: linear-gradient(to bottom, black, transparent 72%);
            z-index: 0;
        }

        /* Área principal */
        .block-container {
            max-width: 1380px;
            padding-top: 1.2rem;
            padding-bottom: 6.5rem;
        }

        /* Sidebar */
        section[data-testid="stSidebar"] {
            background:
                radial-gradient(circle at 20% 0%, rgba(139,92,246,.16), transparent 30%),
                linear-gradient(180deg, rgba(3,7,18,.98), rgba(4,9,24,.98));
            border-right: 1px solid rgba(99,102,241,.26);
        }

        section[data-testid="stSidebar"] > div {
            padding-top: 1rem;
        }

        section[data-testid="stSidebar"] img {
            border-radius: 14px;
        }

        /* Tipografia */
        h1, h2, h3 {
            font-family: 'Orbitron', sans-serif !important;
            letter-spacing: .04em;
            text-shadow: 0 0 16px rgba(91,61,245,.45);
        }

        p, li, span, label {
            color: #E5E7EB;
        }

        /* Cabeçalho */
        .mirai-hero {
            text-align: center;
            padding: 8px 10px 4px;
            margin-bottom: 12px;
        }

        .mirai-hero-sub {
            color: #CBD5E1;
            font-size: 1rem;
            text-align: center;
            margin-top: -4px;
            margin-bottom: 14px;
        }

        /* Painéis */
        .mirai-panel {
            background: linear-gradient(180deg, rgba(7,12,28,.86), rgba(4,8,20,.84));
            border: 1px solid rgba(99,102,241,.30);
            border-radius: 22px;
            padding: 18px 18px 10px;
            box-shadow:
                0 0 0 1px rgba(34,211,238,.03) inset,
                0 18px 60px rgba(0,0,0,.28),
                0 0 32px rgba(91,61,245,.08);
            margin-bottom: 18px;
        }

        .mirai-section-title {
            text-align: center;
            font-family: 'Orbitron', sans-serif;
            font-weight: 700;
            letter-spacing: .04em;
            font-size: .98rem;
            color: #F8FAFC;
            margin: 2px 0 4px;
        }

        .mirai-section-subtitle {
            text-align: center;
            color: #94A3B8;
            font-size: .83rem;
            margin-bottom: 10px;
        }

        /* Botões */
        .stButton > button {
            min-height: 54px;
            border-radius: 14px !important;
            border: 1px solid rgba(99,102,241,.38) !important;
            background:
                linear-gradient(135deg, rgba(91,61,245,.19), rgba(34,211,238,.09)) !important;
            color: #F8FAFC !important;
            box-shadow:
                0 0 12px rgba(91,61,245,.10),
                0 0 0 1px rgba(255,255,255,.015) inset;
            transition: transform .18s ease, box-shadow .18s ease, border-color .18s ease;
            font-weight: 600 !important;
        }

        .stButton > button:hover {
            transform: translateY(-2px);
            border-color: rgba(34,211,238,.72) !important;
            box-shadow:
                0 0 20px rgba(34,211,238,.17),
                0 0 24px rgba(139,92,246,.13);
        }

        /* Expander dos agentes */
        div[data-testid="stExpander"] {
            background: rgba(6, 11, 26, .74);
            border: 1px solid rgba(99,102,241,.32) !important;
            border-radius: 15px !important;
            overflow: hidden;
            box-shadow: 0 0 16px rgba(91,61,245,.07);
            margin-bottom: 8px;
        }

        div[data-testid="stExpander"]:hover {
            border-color: rgba(34,211,238,.55) !important;
            box-shadow: 0 0 20px rgba(34,211,238,.10);
        }

        /* Chat */
        div[data-testid="stChatMessage"] {
            background: linear-gradient(180deg, rgba(8,14,32,.80), rgba(5,10,24,.84));
            border: 1px solid rgba(99,102,241,.26);
            border-radius: 18px;
            padding: 10px 14px;
            margin: 10px 0;
            box-shadow: 0 10px 28px rgba(0,0,0,.18);
        }

        div[data-testid="stChatMessage"] img {
            box-shadow: 0 0 20px rgba(139,92,246,.24);
        }

        /* Campo de chat */
        div[data-testid="stChatInput"] {
            border-radius: 22px !important;
            border: 1px solid rgba(139,92,246,.75) !important;
            background: rgba(5,10,26,.96) !important;
            box-shadow:
                0 0 18px rgba(236,72,153,.18),
                0 0 24px rgba(34,211,238,.13) !important;
        }

        div[data-testid="stChatInput"]:focus-within {
            border-color: rgba(34,211,238,.95) !important;
            box-shadow:
                0 0 22px rgba(34,211,238,.25),
                0 0 28px rgba(236,72,153,.15) !important;
        }

        div[data-testid="stChatInput"] button {
            background: linear-gradient(135deg, #7C3AED, #0EA5E9) !important;
            border-radius: 999px !important;
            color: white !important;
        }

        /* Sidebar — microcopy */
        .sidebar-tagline {
            color: #CBD5E1;
            line-height: 1.55;
            font-size: .93rem;
            margin: 6px 0 18px;
        }

        .sidebar-title {
            font-family: 'Orbitron', sans-serif;
            font-weight: 700;
            letter-spacing: .06em;
            color: #A78BFA;
            margin: 10px 0 10px;
        }

        .agent-meta {
            border: 1px solid rgba(99,102,241,.26);
            border-radius: 14px;
            padding: 10px 12px;
            background: rgba(8,14,32,.64);
            margin: 0 0 6px;
        }

        .agent-meta strong {
            font-size: .94rem;
        }

        .agent-role {
            color: #94A3B8;
            font-size: .78rem;
            margin-top: 2px;
        }

        /* Rodapé */
        .mirai-footer {
            text-align: center;
            color: #64748B;
            font-size: .78rem;
            margin-top: 16px;
            padding-bottom: 6px;
        }

        /* Botão apagar conversa */
        .clear-wrap div[data-testid="stButton"] button {
            min-height: 38px !important;
            color: #F472B6 !important;
            border-color: rgba(236,72,153,.48) !important;
            background: rgba(36,8,28,.48) !important;
        }

        /* Esconde decoração padrão excessiva */
        header[data-testid="stHeader"] {
            background: transparent;
        }

        /* Responsividade */
        @media (max-width: 900px) {
            .block-container {
                padding-left: .8rem;
                padding-right: .8rem;
                padding-top: .5rem;
            }

            .mirai-hero-sub {
                font-size: .9rem;
            }

            .stButton > button {
                min-height: 48px;
                font-size: .82rem !important;
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
# SIDEBAR
# ============================================================

with st.sidebar:
    st.image(LOGO_PATH, use_container_width=True)

    st.markdown(
        f"<div class='sidebar-tagline'>{TAGLINE}</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div class='sidebar-title'>CONHEÇA OS AGENTES</div>",
        unsafe_allow_html=True,
    )

    persona_ativa = st.session_state.persona_atual

    for nome, (label, caminho_poster) in POSTERS.items():
        cor = CORES_AGENTE[nome]
        funcao = FUNCOES[nome]

        st.markdown(
            f"""
            <div class="agent-meta" style="border-left:3px solid {cor};">
                <strong style="color:{cor};">{label}</strong>
                <div class="agent-role">{funcao}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Mantém o pôster acessível, mas sem deixar a lateral pesada.
        with st.expander(
            "Ver apresentação",
            expanded=(nome == persona_ativa),
            key=f"poster_{nome}_{persona_ativa}",
        ):
            st.image(caminho_poster, use_container_width=True)

        # Pergunta sugerida individual daquele agente.
        if st.button(
            f"✦ {PERGUNTAS_AGENTES[nome]}",
            key=f"pergunta_sidebar_{nome}",
            use_container_width=True,
        ):
            st.session_state.pergunta_pendente = PERGUNTAS_AGENTES[nome]
            st.rerun()

    st.markdown("---")
    st.markdown(
        """
        <div style="
            border:1px solid rgba(99,102,241,.26);
            border-radius:14px;
            padding:12px;
            background:rgba(8,14,32,.64);
            font-size:.82rem;
            color:#94A3B8;">
            <b style="color:#A78BFA;">✦ Mirai Agentics</b><br>
            Autonomia • Inteligência • Resultados
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# CABEÇALHO PRINCIPAL
# ============================================================

st.markdown("<div class='mirai-hero'>", unsafe_allow_html=True)
col_logo_1, col_logo_2, col_logo_3 = st.columns([1, 1.35, 1])
with col_logo_2:
    st.image(LOGO_PATH, use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

st.markdown(
    """
    <div class="mirai-hero-sub">
        Converse com o orquestrador de agentes.
        Ele decide sozinho qual especialista te atende.
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# SUGESTÕES — UMA POR AGENTE
# ============================================================

if not st.session_state.historico:
    st.markdown("<div class='mirai-panel'>", unsafe_allow_html=True)
    st.markdown(
        "<div class='mirai-section-title'>✦ SUGESTÕES DE PERGUNTAS</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div class='mirai-section-subtitle'>Escolha um agente ou uma pergunta para começar.</div>",
        unsafe_allow_html=True,
    )

    nomes = list(PERGUNTAS_AGENTES.keys())

    # Primeira linha: 4 cards
    cols = st.columns(4)
    for col, nome in zip(cols, nomes[:4]):
        with col:
            if st.button(
                PERGUNTAS_AGENTES[nome],
                key=f"quick_1_{nome}",
                use_container_width=True,
            ):
                st.session_state.pergunta_pendente = PERGUNTAS_AGENTES[nome]
                st.rerun()

    # Segunda linha: 3 cards centralizados
    espacador_esq, c1, c2, c3, espacador_dir = st.columns([0.35, 1, 1, 1, 0.35])
    for col, nome in zip((c1, c2, c3), nomes[4:]):
        with col:
            if st.button(
                PERGUNTAS_AGENTES[nome],
                key=f"quick_2_{nome}",
                use_container_width=True,
            ):
                st.session_state.pergunta_pendente = PERGUNTAS_AGENTES[nome]
                st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


# ============================================================
# HISTÓRICO DO CHAT
# ============================================================

for msg in st.session_state.historico:
    if msg["role"] == "assistant":
        agente = msg.get("agente", "Mirai Agentics")
        avatar = AVATARES.get(agente, ICONE_INSTITUCIONAL)
        cor = CORES_AGENTE.get(agente, "#8B5CF6")

        with st.chat_message("assistant", avatar=avatar):
            st.markdown(
                f"<div style='font-family:Orbitron,sans-serif; font-weight:700; "
                f"font-size:.86rem; color:{cor}; margin-bottom:6px;'>"
                f"{agente.upper()}</div>",
                unsafe_allow_html=True,
            )
            st.markdown(msg["content"])
    else:
        with st.chat_message("user"):
            st.markdown(msg["content"])


# ============================================================
# ENTRADA DO USUÁRIO
# ============================================================

pergunta_digitada = st.chat_input("Digite sua pergunta...")

# Corrige o comportamento das sugestões:
# ao clicar num botão, a pergunta fica pendente e entra no mesmo fluxo do chat.
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
            f"<div style='font-family:Orbitron,sans-serif; font-weight:700; "
            f"font-size:.86rem; color:{cor}; margin-bottom:6px;'>"
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
# RODAPÉ / LIMPAR CHAT
# ============================================================

st.markdown("<div class='clear-wrap'>", unsafe_allow_html=True)

clear_left, clear_mid, clear_right = st.columns([1.4, 1, 1.4])
with clear_mid:
    if st.button(
        "🗑️ Apagar conversa",
        use_container_width=True,
        key="apagar_conversa",
    ):
        nova_conversa()
        st.rerun()

st.markdown("</div>", unsafe_allow_html=True)

st.markdown(
    """
    <div class="mirai-footer">
        Mirai Agentics — Inteligência que conecta. Agentes que transformam.
    </div>
    """,
    unsafe_allow_html=True,
)
