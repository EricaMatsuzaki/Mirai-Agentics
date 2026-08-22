"""
Interface de chat da Mirai Agentics (Streamlit).

Rode com:
    streamlit run app.py
"""

import os
import uuid
import base64
import html
import re
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

POSTERS = {
    "Mirai Agentics": IMAGEM_GRUPO,
    "Breno": "assets/poster_breno.png",
    "Leo": "assets/poster_leo.png",
    "Alex": "assets/poster_alex.png",
    "Cris": "assets/poster_cris.png",
    "Lari": "assets/poster_lari.png",
    "Carol": "assets/poster_carol.png",
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
SUGESTOES_AGENTES = [
    ("Lari", "Oi Agente Lari do marketing, o que você pode fazer por minha empresa?"),
    ("Carol", "Oi Agente Carol, como você pode melhorar o fluxo de atendimentos?"),
    ("Breno", "Oi Agente Breno do jurídico, você substitui um advogado?"),
    ("Leo", "Oi Agente Leo você pode analisar, atualizar e enviar por email esse dashboard pra mim?"),
    ("Cris", "Oi Agente Cris do RH você pode ajudar na integração (onboarding) de novos funcionários?"),
    ("Alex", "Oi Agente Alex você pode ajudar aumentar as vendas da minha empresa?"),
]

SUGESTOES_INSTITUCIONAIS = [
    "Quantos agentes a Mirai Agentics têm? Vocês fazem agentes personalizados?",
    "Vocês Agentes são robôs humanoides? Vão substituir as pessoas?",
]

FOLDER_INSTITUCIONAL_PDF = (
    "agentes/institucional/Folder_Institucional-MIRAI_AGENTICS.pdf"
)

PERFIS_AGENTES = {
    "Mirai Agentics": {
        "sobre": (
            "O orquestrador da Mirai Agentics identifica a área da pergunta e "
            "encaminha a conversa para o especialista de IA mais adequado."
        ),
        "capacidades": [
            "Orquestração inteligente entre especialistas",
            "Automação de processos e tarefas",
            "Respostas ancoradas na base de conhecimento da empresa",
            "Personalização de agentes para diferentes negócios",
        ],
    },
    "Breno": {
        "sobre": (
            "Especialista jurídico da Mirai Agentics, criado para apoiar rotinas "
            "jurídicas empresariais com organização, automação e segurança."
        ),
        "capacidades": [
            "Segurança jurídica",
            "Contratos e documentos",
            "Compliance empresarial",
            "Organização de informações e rotinas jurídicas",
        ],
    },
    "Leo": {
        "sobre": (
            "Especialista financeiro da Mirai Agentics, focado em análise, "
            "organização financeira e apoio a decisões baseadas em dados."
        ),
        "capacidades": [
            "Análise financeira",
            "Controle de custos",
            "Planejamento orçamentário",
            "Relatórios, dashboards e indicadores",
            "Apoio a decisões e crescimento",
        ],
    },
    "Alex": {
        "sobre": (
            "Especialista em vendas da Mirai Agentics, voltado para processos "
            "comerciais, relacionamento com clientes e crescimento de resultados."
        ),
        "capacidades": [
            "Estratégia de vendas",
            "Gestão de clientes e CRM",
            "Metas e KPIs",
            "Funil de vendas otimizado",
            "Análise de resultados",
        ],
    },
    "Cris": {
        "sobre": (
            "Especialista em Recursos Humanos da Mirai Agentics, criada para "
            "apoiar a jornada dos colaboradores e automatizar processos de pessoas."
        ),
        "capacidades": [
            "Recrutamento inteligente",
            "Onboarding estratégico",
            "Gestão de pessoas",
            "Avaliação de desempenho",
            "Pesquisa de clima",
            "Treinamento e desenvolvimento",
        ],
    },
    "Lari": {
        "sobre": (
            "Especialista em Marketing da Mirai Agentics, focada em fortalecer "
            "marcas, atrair clientes e transformar estratégias em resultados."
        ),
        "capacidades": [
            "Estratégias de Marketing Digital",
            "Gestão de marca e posicionamento",
            "Campanhas e automação",
            "Produção de conteúdo criativo",
            "Análise de dados e performance",
        ],
    },
    "Carol": {
        "sobre": (
            "Especialista em Atendimento da Mirai Agentics, criada para melhorar "
            "a experiência do cliente, agilizar respostas e fortalecer relacionamentos."
        ),
        "capacidades": [
            "Atendimento automatizado",
            "Respostas e relacionamento com clientes",
            "Experiência e satisfação do cliente",
            "Organização de fluxos de atendimento",
            "Atendimento de IA 24 horas por dia, 7 dias por semana",
        ],
    },
}


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



def resposta_para_html(texto: str) -> str:
    """
    Converte a resposta do agente em HTML simples e seguro.
    Mantém parágrafos, bullets e negrito básico para que toda a
    resposta fique dentro da mesma caixa neon.
    """
    texto = str(texto or "")
    linhas = texto.splitlines()
    partes = []
    lista_aberta = False

    def inline_format(valor: str) -> str:
        valor = html.escape(valor)
        valor = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", valor)
        return valor

    for linha in linhas:
        limpa = linha.strip()

        if limpa.startswith(("- ", "* ")):
            if not lista_aberta:
                partes.append("<ul class='reply-list'>")
                lista_aberta = True
            partes.append(f"<li>{inline_format(limpa[2:])}</li>")
            continue

        if lista_aberta:
            partes.append("</ul>")
            lista_aberta = False

        if not limpa:
            partes.append("<div class='reply-gap'></div>")
        else:
            partes.append(f"<div class='reply-line'>{inline_format(limpa)}</div>")

    if lista_aberta:
        partes.append("</ul>")

    return "".join(partes)


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
                radial-gradient(circle at 10% 8%, rgba(236,72,153,.22), transparent 18%),
                radial-gradient(circle at 22% 15%, rgba(124,58,237,.18), transparent 17%),
                radial-gradient(circle at 34% 6%, rgba(14,165,233,.14), transparent 16%),
                radial-gradient(circle at 72% 8%, rgba(34,211,238,.17), transparent 18%),
                radial-gradient(circle at 86% 14%, rgba(168,85,247,.19), transparent 18%),
                radial-gradient(circle at 94% 6%, rgba(236,72,153,.12), transparent 14%),
                radial-gradient(circle at 70% 76%, rgba(236,72,153,.08), transparent 22%),
                radial-gradient(circle at 20% 78%, rgba(59,130,246,.07), transparent 24%),
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
            opacity: .38;
            background-image:
                linear-gradient(rgba(59,130,246,.13) 1px, transparent 1px),
                linear-gradient(90deg, rgba(34,211,238,.08) 1px, transparent 1px),
                linear-gradient(30deg, rgba(168,85,247,.05) 1px, transparent 1px),
                linear-gradient(-30deg, rgba(14,165,233,.035) 1px, transparent 1px);
            background-size: 56px 56px, 56px 56px, 112px 112px, 112px 112px;
            mask-image: linear-gradient(to bottom, black 0%, rgba(0,0,0,.86) 58%, transparent 98%);
        }

        /* Pontos e brilhos no fundo */
        .stApp::after {
            content: "";
            position: fixed;
            inset: 0;
            z-index: 0;
            pointer-events: none;
            opacity: .92;
            background:
                radial-gradient(circle at 6% 8%, rgba(236,72,153,1) 0 1.4px, transparent 2.7px),
                radial-gradient(circle at 12% 18%, rgba(59,130,246,.95) 0 1px, transparent 2.1px),
                radial-gradient(circle at 18% 6%, rgba(34,211,238,.95) 0 1.2px, transparent 2.3px),
                radial-gradient(circle at 24% 12%, rgba(168,85,247,1) 0 1.5px, transparent 2.8px),
                radial-gradient(circle at 31% 4%, rgba(236,72,153,.95) 0 1px, transparent 2.2px),
                radial-gradient(circle at 38% 15%, rgba(34,211,238,.9) 0 1.2px, transparent 2.4px),
                radial-gradient(circle at 45% 7%, rgba(139,92,246,.95) 0 1.3px, transparent 2.6px),
                radial-gradient(circle at 53% 13%, rgba(59,130,246,.9) 0 1px, transparent 2.2px),
                radial-gradient(circle at 60% 5%, rgba(34,211,238,.95) 0 1.2px, transparent 2.5px),
                radial-gradient(circle at 68% 14%, rgba(236,72,153,.95) 0 1px, transparent 2.2px),
                radial-gradient(circle at 76% 6%, rgba(168,85,247,1) 0 1.4px, transparent 2.7px),
                radial-gradient(circle at 83% 17%, rgba(34,211,238,.95) 0 1.1px, transparent 2.3px),
                radial-gradient(circle at 91% 8%, rgba(236,72,153,.95) 0 1.2px, transparent 2.5px),
                radial-gradient(circle at 97% 15%, rgba(59,130,246,.9) 0 1px, transparent 2.1px),
                radial-gradient(circle at 14% 64%, rgba(59,130,246,.75) 0 1px, transparent 2px),
                radial-gradient(circle at 25% 78%, rgba(168,85,247,.82) 0 1.1px, transparent 2.2px),
                radial-gradient(circle at 42% 69%, rgba(34,211,238,.65) 0 1px, transparent 2px),
                radial-gradient(circle at 71% 72%, rgba(236,72,153,.78) 0 1.1px, transparent 2.2px),
                radial-gradient(circle at 88% 82%, rgba(34,211,238,.80) 0 1.2px, transparent 2.3px),
                radial-gradient(circle at 52% 88%, rgba(139,92,246,.72) 0 1px, transparent 2px);
        }

        .stApp .block-container::before {
            content: "";
            position: fixed;
            inset: 0;
            pointer-events: none;
            z-index: 0;
            background:
                radial-gradient(circle at 18% 9%, rgba(255,255,255,.8) 0 1px, rgba(236,72,153,.55) 2px, transparent 7px),
                radial-gradient(circle at 37% 11%, rgba(255,255,255,.8) 0 1px, rgba(34,211,238,.45) 2px, transparent 6px),
                radial-gradient(circle at 72% 10%, rgba(255,255,255,.85) 0 1px, rgba(168,85,247,.5) 2px, transparent 7px),
                radial-gradient(circle at 89% 13%, rgba(255,255,255,.8) 0 1px, rgba(236,72,153,.45) 2px, transparent 6px),
                radial-gradient(circle at 64% 68%, rgba(255,255,255,.75) 0 1px, rgba(34,211,238,.38) 2px, transparent 6px);
            opacity: .8;
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
            color: #FFFFFF;
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


        /* Cards nativos: clique rápido, sem navegar para outra URL */
        section[data-testid="stSidebar"] [class*="st-key-agentbox_"] {
            border-radius: 14px;
            padding: 5px 7px;
            margin-bottom: 8px;
            background: rgba(4,10,25,.86);
        }

        section[data-testid="stSidebar"] [class*="st-key-agentbox_"] img {
            width: 48px !important;
            height: 48px !important;
            min-width: 48px !important;
            object-fit: cover !important;
            border-radius: 50% !important;
        }

        section[data-testid="stSidebar"] [class*="st-key-agentbtn_"] button {
            min-height: 48px !important;
            width: 100% !important;
            justify-content: flex-start !important;
            text-align: left !important;
            padding: 5px 28px 5px 5px !important;
            border: 0 !important;
            background: transparent !important;
            box-shadow: none !important;
            color: #F8FAFC !important;
            font-weight: 700 !important;
            font-size: .84rem !important;
            position: relative !important;
        }

        section[data-testid="stSidebar"] [class*="st-key-agentbtn_"] button:hover {
            transform: none !important;
            box-shadow: none !important;
        }

        section[data-testid="stSidebar"] [class*="st-key-agentbtn_"] button::after {
            content: "›";
            position: absolute;
            right: 5px;
            top: 50%;
            transform: translateY(-54%);
            font-size: 1.45rem;
        }

        .st-key-agentbox_mirai {
            border: 1px solid #8B5CF6 !important;
            box-shadow: 0 0 17px rgba(139,92,246,.26);
        }
        .st-key-agentbox_breno {
            border: 1px solid #F5B82E !important;
            box-shadow: 0 0 17px rgba(245,184,46,.24);
        }
        .st-key-agentbox_leo {
            border: 1px solid #7ED321 !important;
            box-shadow: 0 0 17px rgba(126,211,33,.24);
        }
        .st-key-agentbox_alex {
            border: 1px solid #22B8FF !important;
            box-shadow: 0 0 17px rgba(34,184,255,.24);
        }
        .st-key-agentbox_cris {
            border: 1px solid #A855F7 !important;
            box-shadow: 0 0 17px rgba(168,85,247,.24);
        }
        .st-key-agentbox_lari {
            border: 1px solid #EC4899 !important;
            box-shadow: 0 0 17px rgba(236,72,153,.28);
        }
        .st-key-agentbox_carol {
            border: 1px solid #22D3EE !important;
            box-shadow: 0 0 17px rgba(34,211,238,.26);
        }

        .st-key-agentbtn_mirai button::after { color:#8B5CF6; }
        .st-key-agentbtn_breno button::after { color:#F5B82E; }
        .st-key-agentbtn_leo button::after { color:#7ED321; }
        .st-key-agentbtn_alex button::after { color:#22B8FF; }
        .st-key-agentbtn_cris button::after { color:#A855F7; }
        .st-key-agentbtn_lari button::after { color:#EC4899; }
        .st-key-agentbtn_carol button::after { color:#22D3EE; }

        /* Quando aberto, mostramos somente o pôster */
        .sidebar-poster-wrap {
            margin: -2px 0 12px;
            padding: 7px;
            border-radius: 12px;
            background: rgba(2,6,23,.88);
            border: 1px solid rgba(100,116,139,.18);
        }


        /* ====================================================
           SIDEBAR — TEXTO BRANCO + GLOW MAIS FORTE POR AGENTE
           ==================================================== */

        section[data-testid="stSidebar"] [class*="st-key-agentbox_"] button,
        section[data-testid="stSidebar"] [class*="st-key-agentbox_"] button p,
        section[data-testid="stSidebar"] [class*="st-key-agentbox_"] button span,
        section[data-testid="stSidebar"] [class*="st-key-agentbox_"] [data-testid="stCaptionContainer"],
        section[data-testid="stSidebar"] [class*="st-key-agentbox_"] [data-testid="stCaptionContainer"] p,
        section[data-testid="stSidebar"] [class*="st-key-agentbox_"] [data-testid="stCaptionContainer"] span {
            color: #FFFFFF !important;
            -webkit-text-fill-color: #FFFFFF !important;
            opacity: 1 !important;
        }

        section[data-testid="stSidebar"] [class*="st-key-agentbtn_"] button {
            font-weight: 700 !important;
            color: #FFFFFF !important;
            text-shadow: 0 0 8px rgba(255,255,255,.08);
        }

        section[data-testid="stSidebar"] [class*="st-key-agentbox_"] [data-testid="stCaptionContainer"] {
            color: #FFFFFF !important;
        }

        .st-key-agentbox_mirai {
            background: linear-gradient(90deg, rgba(139,92,246,.14), rgba(3,8,24,.94) 45%) !important;
            border: 1px solid #8B5CF6 !important;
            box-shadow: 0 0 14px rgba(139,92,246,.34), 0 0 28px rgba(139,92,246,.16), inset 0 0 22px rgba(139,92,246,.05) !important;
        }

        .st-key-agentbox_breno {
            background: linear-gradient(90deg, rgba(245,184,46,.16), rgba(3,8,24,.94) 45%) !important;
            border: 1px solid #F5B82E !important;
            box-shadow: 0 0 14px rgba(245,184,46,.36), 0 0 28px rgba(245,184,46,.17), inset 0 0 22px rgba(245,184,46,.055) !important;
        }

        .st-key-agentbox_leo {
            background: linear-gradient(90deg, rgba(126,211,33,.16), rgba(3,8,24,.94) 45%) !important;
            border: 1px solid #7ED321 !important;
            box-shadow: 0 0 14px rgba(126,211,33,.36), 0 0 28px rgba(126,211,33,.17), inset 0 0 22px rgba(126,211,33,.055) !important;
        }

        .st-key-agentbox_alex {
            background: linear-gradient(90deg, rgba(34,184,255,.16), rgba(3,8,24,.94) 45%) !important;
            border: 1px solid #22B8FF !important;
            box-shadow: 0 0 14px rgba(34,184,255,.36), 0 0 28px rgba(34,184,255,.17), inset 0 0 22px rgba(34,184,255,.055) !important;
        }

        .st-key-agentbox_cris {
            background: linear-gradient(90deg, rgba(168,85,247,.16), rgba(3,8,24,.94) 45%) !important;
            border: 1px solid #A855F7 !important;
            box-shadow: 0 0 14px rgba(168,85,247,.36), 0 0 28px rgba(168,85,247,.17), inset 0 0 22px rgba(168,85,247,.055) !important;
        }

        .st-key-agentbox_lari {
            background: linear-gradient(90deg, rgba(236,72,153,.18), rgba(3,8,24,.94) 45%) !important;
            border: 1px solid #EC4899 !important;
            box-shadow: 0 0 15px rgba(236,72,153,.40), 0 0 30px rgba(236,72,153,.18), inset 0 0 24px rgba(236,72,153,.06) !important;
        }

        .st-key-agentbox_carol {
            background: linear-gradient(90deg, rgba(34,211,238,.17), rgba(3,8,24,.94) 45%) !important;
            border: 1px solid #22D3EE !important;
            box-shadow: 0 0 15px rgba(34,211,238,.38), 0 0 30px rgba(34,211,238,.18), inset 0 0 24px rgba(34,211,238,.06) !important;
        }

        .st-key-agentbox_mirai img { box-shadow: 0 0 13px rgba(139,92,246,.50) !important; }
        .st-key-agentbox_breno img { box-shadow: 0 0 13px rgba(245,184,46,.52) !important; }
        .st-key-agentbox_leo img { box-shadow: 0 0 13px rgba(126,211,33,.52) !important; }
        .st-key-agentbox_alex img { box-shadow: 0 0 13px rgba(34,184,255,.52) !important; }
        .st-key-agentbox_cris img { box-shadow: 0 0 13px rgba(168,85,247,.52) !important; }
        .st-key-agentbox_lari img { box-shadow: 0 0 14px rgba(236,72,153,.56) !important; }
        .st-key-agentbox_carol img { box-shadow: 0 0 14px rgba(34,211,238,.56) !important; }


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
            font-family: 'Inter', sans-serif !important;
            font-weight: 700;
            letter-spacing: .015em;
            color: #F8FAFC;
            font-size: 1.02rem;
            margin-bottom: 12px;
            text-shadow: 0 0 12px rgba(139,92,246,.24);
        }

        /* Botões/sugestões por agente */
        .stButton > button {
            border-radius: 14px !important;
            color: #F8FAFC !important;
            font-weight: 600 !important;
            min-height: 58px;
            background: rgba(5, 11, 27, .90) !important;
            transition: transform .18s ease, box-shadow .18s ease, border-color .18s ease;
        }

        .stButton > button:hover {
            transform: translateY(-2px);
        }

        .st-key-sug_lari button,
        .st-key-sug_carol button,
        .st-key-sug_breno button,
        .st-key-sug_leo button,
        .st-key-sug_cris button,
        .st-key-sug_alex button {
            min-height: 58px !important;
            padding: 10px 14px !important;
            line-height: 1.35 !important;
        }

        .st-key-sug_lari button {
            border: 1px solid #EC4899 !important;
            background: linear-gradient(135deg, rgba(236,72,153,.14), rgba(5,11,27,.95) 55%) !important;
            box-shadow: 0 0 14px rgba(236,72,153,.26), 0 0 30px rgba(236,72,153,.12), inset 0 0 24px rgba(236,72,153,.045);
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
            background: linear-gradient(135deg, rgba(34,211,238,.12), rgba(5,11,27,.95) 55%) !important;
            box-shadow: 0 0 14px rgba(34,211,238,.26), 0 0 30px rgba(34,211,238,.12), inset 0 0 24px rgba(34,211,238,.045);
        }
        .st-key-sug_carol button:hover {
            box-shadow: 0 0 26px rgba(34,211,238,.42);
        }

        .st-key-sug_cris button {
            border: 1px solid #A855F7 !important;
            background: linear-gradient(135deg, rgba(168,85,247,.13), rgba(5,11,27,.95) 55%) !important;
            box-shadow: 0 0 14px rgba(168,85,247,.28), 0 0 30px rgba(168,85,247,.12), inset 0 0 24px rgba(168,85,247,.045);
        }
        .st-key-sug_cris button:hover {
            box-shadow: 0 0 26px rgba(168,85,247,.42);
        }

        .st-key-sug_alex button {
            border: 1px solid #22B8FF !important;
            background: linear-gradient(135deg, rgba(34,184,255,.12), rgba(5,11,27,.95) 55%) !important;
            box-shadow: 0 0 14px rgba(34,184,255,.28), 0 0 30px rgba(34,184,255,.12), inset 0 0 24px rgba(34,184,255,.045);
        }
        .st-key-sug_alex button:hover {
            box-shadow: 0 0 26px rgba(46,134,255,.42);
        }

        .st-key-sug_breno button {
            border: 1px solid #F5B82E !important;
            background: linear-gradient(135deg, rgba(245,184,46,.13), rgba(5,11,27,.95) 55%) !important;
            box-shadow: 0 0 14px rgba(245,184,46,.28), 0 0 30px rgba(245,184,46,.12), inset 0 0 24px rgba(245,184,46,.04);
        }

        .st-key-sug_leo button {
            border: 1px solid #7ED321 !important;
            background: linear-gradient(135deg, rgba(126,211,33,.13), rgba(5,11,27,.95) 55%) !important;
            box-shadow: 0 0 14px rgba(126,211,33,.28), 0 0 30px rgba(126,211,33,.12), inset 0 0 24px rgba(126,211,33,.04);
        }

        .st-key-sug_inst_1 button,
        .st-key-sug_inst_2 button {
            min-height: 40px !important;
            font-size: .82rem !important;
            border: 1px solid rgba(96,165,250,.58) !important;
            box-shadow: 0 0 12px rgba(59,130,246,.13);
        }

        /* Chat */
        div[data-testid="stChatMessage"] {
            background: rgba(3,9,24,.74);
            border: 1px solid rgba(100,116,139,.24);
            border-radius: 18px;
            padding: 12px 15px;
            margin: 10px 0;
            box-shadow: 0 10px 28px rgba(0,0,0,.18);
        }

        div[data-testid="stChatMessage"] p,
        div[data-testid="stChatMessage"] li,
        div[data-testid="stChatMessage"] span {
            color: #FFFFFF !important;
            opacity: 1 !important;
        }

        /* Usuário: avatar normal */
        div[data-testid="stChatMessageAvatarUser"],
        div[data-testid="stChatMessageAvatarUser"] img,
        div[data-testid="stChatMessageAvatarUser"] [data-testid="stAvatarIcon"] {
            width: 40px !important;
            height: 40px !important;
            min-width: 40px !important;
            border-radius: 50% !important;
        }

        /* Agente: avatar grande */
        div[data-testid="stChatMessageAvatarAssistant"] {
            width: 118px !important;
            height: 118px !important;
            min-width: 118px !important;
            align-self: flex-start !important;
        }

        div[data-testid="stChatMessageAvatarAssistant"] img,
        div[data-testid="stChatMessageAvatarAssistant"] [data-testid="stAvatarIcon"] {
            width: 118px !important;
            height: 118px !important;
            object-fit: cover !important;
            border-radius: 50% !important;
        }

        /* Nome do agente */
        .agent-chat-name {
            font-family: 'Orbitron', sans-serif;
            font-weight: 700;
            letter-spacing: .035em;
            font-size: .90rem;
            margin-bottom: 7px;
        }

        .reply-card {
            border-radius: 16px;
            padding: 13px 16px;
            background: rgba(3,9,25,.76);
            border: 1px solid var(--reply-color);
            box-shadow:
                0 0 20px color-mix(in srgb, var(--reply-color) 32%, transparent),
                inset 0 0 22px color-mix(in srgb, var(--reply-color) 5%, transparent);
        }

        .reply-card p,
        .reply-card li,
        .reply-card span {
            color: #FFFFFF !important;
            opacity: 1 !important;
        }

        .reply-card {
            color: #FFFFFF !important;
            margin-top: 4px;
        }

        .reply-line {
            color: #FFFFFF !important;
            font-size: .98rem;
            line-height: 1.62;
            margin: 3px 0;
        }

        .reply-list {
            color: #FFFFFF !important;
            margin: 8px 0 8px 1.15rem;
            padding-left: .8rem;
        }

        .reply-list li {
            color: #FFFFFF !important;
            line-height: 1.55;
            margin: 4px 0;
        }

        .reply-gap {
            height: 8px;
        }

        /* Input */
        div[data-testid="stChatInput"] {
            border-radius: 22px !important;
            border: 1px solid rgba(236,72,153,.82) !important;
            background: #F8FAFC !important;
            box-shadow:
                -7px 0 22px rgba(236,72,153,.22),
                7px 0 22px rgba(34,211,238,.20),
                0 0 16px rgba(139,92,246,.14) !important;
        }

        div[data-testid="stChatInput"]:focus-within {
            border-color: #22D3EE !important;
            box-shadow:
                -7px 0 26px rgba(236,72,153,.28),
                7px 0 28px rgba(34,211,238,.28) !important;
        }

        div[data-testid="stChatInput"] textarea,
        div[data-testid="stChatInput"] input {
            color: #111827 !important;
            -webkit-text-fill-color: #111827 !important;
            opacity: 1 !important;
            caret-color: #111827 !important;
            background: transparent !important;
            font-weight: 500 !important;
        }

        div[data-testid="stChatInput"] textarea::placeholder,
        div[data-testid="stChatInput"] input::placeholder {
            color: #6B7280 !important;
            -webkit-text-fill-color: #6B7280 !important;
            opacity: 1 !important;
        }

        div[data-testid="stBottomBlockContainer"],
        div[data-testid="stBottomBlockContainer"] > div,
        div[data-testid="stBottom"],
        div[data-testid="stBottom"] > div,
        [data-testid="stBottomBlockContainer"] {
            background: rgba(2, 6, 23, .96) !important;
            box-shadow: none !important;
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


if "poster_aberto" not in st.session_state:
    st.session_state.poster_aberto = None


def alternar_poster(nome: str):
    """Abre/fecha somente o pôster do agente clicado no sidebar."""
    if st.session_state.poster_aberto == nome:
        st.session_state.poster_aberto = None
    else:
        st.session_state.poster_aberto = nome


# ============================================================
# SIDEBAR — ABRE/FECHA PÔSTER SEM RERUN
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
        avatar_path = IMAGEM_GRUPO if nome == "Mirai Agentics" else AVATARES[nome]

        avatar_uri = imagem_base64(avatar_path)
        poster_uri = imagem_base64(POSTERS[nome])

        classe_grupo = "group" if nome == "Mirai Agentics" else ""

        st.markdown(
            f"""
            <details class="agent-details {classe_grupo}" style="--agent-color:{cor};">
                <summary class="agent-summary">
                    <img
                        class="agent-summary-avatar"
                        src="{avatar_uri}"
                        alt="{nome}"
                    >
                    <div class="agent-summary-text">
                        <div class="agent-summary-name">{LABELS[nome]}</div>
                        <div class="agent-summary-role">{FUNCOES[nome]}</div>
                    </div>
                </summary>

                <div class="agent-poster-inline">
                    <img
                        src="{poster_uri}"
                        alt="Pôster de {nome}"
                    >
                </div>
            </details>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        """
        <div style="
            margin-top:20px;
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
# SUGESTÕES PRINCIPAIS — SEM FOTOS, COM GLOW POR AGENTE
# ============================================================

if not st.session_state.historico:
    st.markdown("<div class='mirai-panel'>", unsafe_allow_html=True)
    st.markdown(
        "<div class='mirai-title'>✦ Sugestões de perguntas para nossos agentes ✦</div>",
        unsafe_allow_html=True,
    )

    chaves = {
        "Lari": "sug_lari",
        "Carol": "sug_carol",
        "Breno": "sug_breno",
        "Leo": "sug_leo",
        "Cris": "sug_cris",
        "Alex": "sug_alex",
    }

    # Duas colunas, como no modelo visual:
    # Lari | Carol
    # Breno | Cris
    # Leo | Alex
    pares = [
        (SUGESTOES_AGENTES[0], SUGESTOES_AGENTES[1]),
        (SUGESTOES_AGENTES[2], SUGESTOES_AGENTES[4]),
        (SUGESTOES_AGENTES[3], SUGESTOES_AGENTES[5]),
    ]

    for esquerda, direita in pares:
        c1, c2 = st.columns(2, gap="medium")

        for col, (agente, texto_sugestao) in (
            (c1, esquerda),
            (c2, direita),
        ):
            with col:
                if st.button(
                    texto_sugestao,
                    key=chaves[agente],
                    use_container_width=True,
                ):
                    st.session_state.pergunta_pendente = texto_sugestao
                    st.rerun()

    # Institucionais em tiras mais finas.
    if st.button(
        SUGESTOES_INSTITUCIONAIS[0],
        key="sug_inst_1",
        use_container_width=True,
    ):
        st.session_state.pergunta_pendente = SUGESTOES_INSTITUCIONAIS[0]
        st.rerun()

    if st.button(
        SUGESTOES_INSTITUCIONAIS[1],
        key="sug_inst_2",
        use_container_width=True,
    ):
        st.session_state.pergunta_pendente = SUGESTOES_INSTITUCIONAIS[1]
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
            resposta_html = resposta_para_html(msg["content"])
            st.markdown(
                (
                    f"<div class='agent-chat-name' style='color:{cor};'>{html.escape(agente)}</div>"
                    f"<div class='reply-card' style='--reply-color:{cor};'>"
                    f"{resposta_html}"
                    "</div>"
                ),
                unsafe_allow_html=True,
            )
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
        resposta_html = resposta_para_html(resposta)
        st.markdown(
            (
                f"<div class='agent-chat-name' style='color:{cor};'>{html.escape(persona)}</div>"
                f"<div class='reply-card' style='--reply-color:{cor};'>"
                f"{resposta_html}"
                "</div>"
            ),
            unsafe_allow_html=True,
        )

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
