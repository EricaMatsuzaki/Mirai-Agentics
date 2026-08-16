"""
Interface de chat da Mirai Agentics (Streamlit).

Rode com: streamlit run app.py
"""

import uuid
import streamlit as st
from mirai_core import build_app, conversar

st.set_page_config(page_title="Mirai Agentics", page_icon="assets/logo_mirai_agentics.png")

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


@st.cache_resource(show_spinner="Carregando os agentes da Mirai Agentics...")
def get_app():
    return build_app()


with st.sidebar:
    st.image(LOGO_PATH, width=200)
    st.markdown("### Conheça os agentes")
    for nome, caminho in POSTERS.items():
        with st.expander(nome):
            st.image(caminho, use_container_width=True)

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

    with st.chat_message("assistant", avatar=LOGO_PATH):
        with st.spinner("Roteando para o agente certo..."):
            resposta, persona = conversar(app, pergunta, thread_id=st.session_state.thread_id)
        st.markdown(f"**{persona}**\n\n{resposta}")

    st.session_state.historico.append({"role": "assistant", "content": resposta, "agente": persona})
