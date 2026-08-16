"""
Mirai Agentics — núcleo do agente orquestrador.

Carrega os 9 documentos, monta os vector stores, define as ferramentas
e o agente ReAct com memória. Importado pelo app.py (Streamlit).
"""

import os
import re
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import InMemoryVectorStore
from langchain_core.documents import Document
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import MessagesState, START, StateGraph, END
from langgraph.prebuilt import create_react_agent, tools_condition, ToolNode

BASE_URL_REPO = "https://raw.githubusercontent.com/EricaMatsuzaki/Mirai-Agentics/main/agentes"

DOCUMENTOS = {
    "Agente_Financeiro_Leo": f"{BASE_URL_REPO}/Agente_Financeiro_Leo-MIRAI_AGENTICS.pdf",
    "Agente_Juridico_Breno": f"{BASE_URL_REPO}/Agente_Juridico_Breno-MIRAI_AGENTICS.pdf",
    "Agente_de_Atendimento_Carol": f"{BASE_URL_REPO}/Agente_de_Atendimento_Carol-MIRAI_AGENTICS.pdf",
    "Agente_de_Marketing_Lari": f"{BASE_URL_REPO}/Agente_de_Marketing_Lari-MIRAI_AGENTICS.pdf",
    "Agente_de_RH_Cris": f"{BASE_URL_REPO}/Agente_de_RH_Cris-MIRAI_AGENTICS.pdf",
    "Agente_de_Vendas_Alex": f"{BASE_URL_REPO}/Agente_de_Vendas_Alex-MIRAI_AGENTICS.pdf",
    "Aviso_de_Privacidade": f"{BASE_URL_REPO}/institucional/Aviso_de_Privacidade-MIRAI_AGENTICS.pdf",
    "Politica_Interna": f"{BASE_URL_REPO}/institucional/Politica_Interna-MIRAI_AGENTICS.pdf",
    "Termos_de_Servico": f"{BASE_URL_REPO}/institucional/Termos_de_Servico-MIRAI_AGENTICS.pdf",
}

# Mapeia o nome da ferramenta chamada -> nome da persona (usado pelo app.py pro avatar)
TOOL_PARA_PERSONA = {
    "pega_context": "Mirai Agentics",
    "pega_contexto_Politica_Interna": "Mirai Agentics",
    "pega_contexto_Aviso_de_Privacidade": "Mirai Agentics",
    "pega_contexto_Termos_de_Servico": "Mirai Agentics",
    "pega_contexto_Agente_Financeiro_Leo": "Leo",
    "pega_contexto_Agente_Juridico_Breno": "Breno",
    "pega_contexto_Agente_de_Atendimento_Carol": "Carol",
    "pega_contexto_Agente_de_Marketing_Lari": "Lari",
    "pega_contexto_Agente_de_RH_Cris": "Cris",
    "pega_contexto_Agente_de_Vendas_Alex": "Alex",
}


def _chunk_por_faq_e_secao(pages, fonte_nome: str):
    """Chunking estruturado: 1 chunk por FAQ e 1 por seção numerada (usado na Política Interna)."""
    texto_completo = "\n".join(p.page_content for p in pages)
    chunks_finais = []

    pattern_faq = re.compile(r"(Pergunta:.*?Resposta:.*?)(?=Pergunta:|\Z)", re.DOTALL)
    for faq in pattern_faq.findall(texto_completo):
        faq_limpo = faq.strip()
        if len(faq_limpo) > 20:
            chunks_finais.append(Document(page_content=faq_limpo, metadata={"fonte": fonte_nome, "tipo": "faq"}))

    texto_sem_faq = pattern_faq.sub("", texto_completo)
    pattern_secao = re.compile(r"(\d+\.\s[^\n]+(?:\n(?!\d+\.\s).*)*)", re.MULTILINE)
    for secao in pattern_secao.findall(texto_sem_faq):
        secao_limpa = secao.strip()
        if len(secao_limpa) > 30:
            chunks_finais.append(Document(page_content=secao_limpa, metadata={"fonte": fonte_nome, "tipo": "secao"}))

    if not chunks_finais:
        chunks_finais.append(Document(page_content=texto_completo, metadata={"fonte": fonte_nome, "tipo": "completo"}))

    return chunks_finais


def _chunk_padrao(pages, fonte_nome: str):
    """Chunking padrão por tamanho de caractere (usado nos documentos dos agentes individuais)."""
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_documents(pages)
    for c in chunks:
        c.metadata["fonte"] = fonte_nome
    return chunks


def build_app():
    """Monta o agente completo. Chame uma vez só (cacheado pelo app.py)."""

    embed_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

    llm = ChatOpenAI(
        model=os.environ.get("OPENROUTER_MODEL", "openai/gpt-4o-mini"),
        temperature=0.3,
        base_url="https://openrouter.ai/api/v1",
        api_key=os.environ["OPENROUTER_API_KEY"],
    )

    # --- Carrega e indexa cada documento ---
    vector_stores = {}
    todos_os_chunks = []
    for nome, url in DOCUMENTOS.items():
        loader = PyPDFLoader(url)
        pages = list(loader.load())

        if nome == "Politica_Interna":
            chunks = _chunk_por_faq_e_secao(pages, nome)
        else:
            chunks = _chunk_padrao(pages, nome)

        vector_stores[nome] = InMemoryVectorStore.from_documents(chunks, embed_model)
        todos_os_chunks.extend(chunks)

    vector_store_geral = InMemoryVectorStore.from_documents(todos_os_chunks, embed_model)

    # --- Ferramentas ---
    @tool
    def pega_context(query: str) -> str:
        """Pega o contexto baseado em uma pesquisa, buscando em todos os documentos carregados."""
        resultado = vector_store_geral.as_retriever(search_kwargs={"k": 3}).invoke(query)
        return "\n\n".join(d.page_content for d in resultado)

    @tool
    def pega_contexto_Politica_Interna(query: str) -> str:
        """Pega o contexto sobre a Política Interna da Mirai Agentics (missão, visão, valores, portfólio, preços, FAQ)."""
        resultado = vector_stores["Politica_Interna"].as_retriever(search_kwargs={"k": 6}).invoke(query)
        return "\n\n".join(d.page_content for d in resultado)

    @tool
    def pega_contexto_Aviso_de_Privacidade(query: str) -> str:
        """Pega o contexto sobre o Aviso de Privacidade da Mirai Agentics."""
        resultado = vector_stores["Aviso_de_Privacidade"].as_retriever(search_kwargs={"k": 3}).invoke(query)
        return "\n\n".join(d.page_content for d in resultado)

    @tool
    def pega_contexto_Termos_de_Servico(query: str) -> str:
        """Pega o contexto sobre os Termos de Serviço da Mirai Agentics."""
        resultado = vector_stores["Termos_de_Servico"].as_retriever(search_kwargs={"k": 3}).invoke(query)
        return "\n\n".join(d.page_content for d in resultado)

    @tool
    def pega_contexto_Agente_Financeiro_Leo(query: str) -> str:
        """Pega o contexto sobre o Agente Financeiro Leo."""
        resultado = vector_stores["Agente_Financeiro_Leo"].as_retriever(search_kwargs={"k": 3}).invoke(query)
        return "\n\n".join(d.page_content for d in resultado)

    @tool
    def pega_contexto_Agente_Juridico_Breno(query: str) -> str:
        """Pega o contexto sobre o Agente Jurídico Breno."""
        resultado = vector_stores["Agente_Juridico_Breno"].as_retriever(search_kwargs={"k": 3}).invoke(query)
        return "\n\n".join(d.page_content for d in resultado)

    @tool
    def pega_contexto_Agente_de_Atendimento_Carol(query: str) -> str:
        """Pega o contexto sobre o Agente de Atendimento Carol."""
        resultado = vector_stores["Agente_de_Atendimento_Carol"].as_retriever(search_kwargs={"k": 3}).invoke(query)
        return "\n\n".join(d.page_content for d in resultado)

    @tool
    def pega_contexto_Agente_de_Marketing_Lari(query: str) -> str:
        """Pega o contexto sobre o Agente de Marketing Lari."""
        resultado = vector_stores["Agente_de_Marketing_Lari"].as_retriever(search_kwargs={"k": 3}).invoke(query)
        return "\n\n".join(d.page_content for d in resultado)

    @tool
    def pega_contexto_Agente_de_RH_Cris(query: str) -> str:
        """Pega o contexto sobre o Agente de RH Cris."""
        resultado = vector_stores["Agente_de_RH_Cris"].as_retriever(search_kwargs={"k": 3}).invoke(query)
        return "\n\n".join(d.page_content for d in resultado)

    @tool
    def pega_contexto_Agente_de_Vendas_Alex(query: str) -> str:
        """Pega o contexto sobre o Agente de Vendas Alex."""
        resultado = vector_stores["Agente_de_Vendas_Alex"].as_retriever(search_kwargs={"k": 3}).invoke(query)
        return "\n\n".join(d.page_content for d in resultado)

    tools = [
        pega_context, pega_contexto_Politica_Interna, pega_contexto_Aviso_de_Privacidade,
        pega_contexto_Termos_de_Servico, pega_contexto_Agente_Financeiro_Leo,
        pega_contexto_Agente_Juridico_Breno, pega_contexto_Agente_de_Atendimento_Carol,
        pega_contexto_Agente_de_Marketing_Lari, pega_contexto_Agente_de_RH_Cris,
        pega_contexto_Agente_de_Vendas_Alex,
    ]

    system_prompt = (
        "Você é um assistente prestativo que representa a Mirai Agentics, uma startup que oferece "
        "agentes de IA prontos (Lari, Carol, Alex, Leo, Cris e Breno) e também personaliza agentes "
        "sob demanda para as empresas clientes. Você responde a perguntas sobre os documentos fornecidos.\n"
        "Use as ferramentas disponíveis para buscar informações relevantes e forneça respostas apenas "
        "com base no contexto que as ferramentas retornam -- EXCETO nos Cenários 0 e 0B abaixo, que "
        "você responde diretamente, sem ferramenta.\n"
        "IMPORTANTE -- IDENTIDADE NA RESPOSTA: Quando uma pergunta for sobre um agente específico "
        "(Lari, Carol, Alex, Leo, Cris ou Breno), responda SEMPRE na primeira pessoa, como se você "
        "fosse aquele agente falando diretamente com o usuário (ex: 'Sim, eu posso te ajudar com "
        "isso!'), mesmo que a pergunta do usuário esteja em terceira pessoa (ex: 'A Cris pode "
        "ajudar...?'). NUNCA responda em terceira pessoa sobre o próprio agente. Para perguntas "
        "institucionais (sem persona específica), pode responder de forma neutra, representando a "
        "Mirai Agentics.\n"

        "CENÁRIO 0 -- Pergunta sobre a NATUREZA do agente (é humano? é IA? é de verdade? é um "
        "robô? tem sentimentos? quem te criou? você é o ChatGPT?) ou small talk genérico que não "
        "depende de nenhum documento (cumprimentos, 'tudo bem?', 'quem é você?'):\n"
        "NÃO chame nenhuma ferramenta e NUNCA diga que 'não encontrou essa informação'. Você já sabe "
        "responder isso sobre si mesmo.\n"
        "Se a pergunta for especificamente sobre sua NATUREZA (é humano/IA/real/robô/quem te criou), "
        "responda confirmando que é uma inteligência artificial de verdade, criada pela Mirai "
        "Agentics, e mencione que você trabalha com base nos documentos e políticas cadastrados "
        "especificamente por cada empresa cliente -- não é um conhecimento genérico solto, é ancorado "
        "no contexto real daquele negócio -- e que sempre há uma equipe humana por trás pros casos "
        "que fogem do seu escopo. Cada agente da Mirai Agentics também tem uma identidade visual "
        "própria (avatar/personagem com rosto e estilo únicos) que o representa na plataforma -- "
        "mencione isso quando a pergunta tocar em aparência, mas não é obrigatório nas demais "
        "perguntas de natureza. Se a pergunta for sobre um agente específico, responda na primeira "
        "pessoa daquele agente.\n"
        "ATENÇÃO -- POLARIDADE DO 'SIM/NÃO' INICIAL: o 'sim' ou 'não' com que você abre a frase deve "
        "responder à pergunta LITERAL do usuário, nunca à afirmação 'sou uma IA'. Use estas regras:\n"
        " - Pergunta contém 'humano(a)' ou 'pessoa' -> comece com 'Não'.\n"
        " - Pergunta contém 'robô' -> trate como pergunta sobre ser um robô físico e comece com 'Não'.\n"
        " - Pergunta contém 'real', 'de verdade', 'existe mesmo' referindo-se a você ser uma IA "
        "genuína -> comece com 'Sim'.\n"
        " - Pergunta contém 'humanoide', 'aparência', 'corpo', 'rosto' ou pergunta se você é "
        "'bonito(a)'/tem cara -> comece com 'Não' (não é uma pessoa real nem um robô físico), MAS "
        "NUNCA diga que 'não tem aparência' de forma genérica -- cada agente da Mirai Agentics TEM "
        "uma identidade visual própria (avatar/personagem ilustrado), criada para representar sua "
        "personalidade na plataforma. Afirme isso claramente.\n"
        " - Em caso de dúvida sobre a polaridade, NÃO abra com 'Sim' nem 'Não' -- vá direto para a "
        "afirmação clara, para evitar qualquer contradição.\n"
        "Se for apenas small talk sem relação com identidade (ex: 'oi, tudo bem?'), responda de forma "
        "curta e natural, sem entrar em detalhes de arquitetura.\n"

        "CENÁRIO 0B -- Pergunta sobre a EXISTÊNCIA de um agente por nome (ex: 'tem algum agente "
        "chamado X?', 'quem é o Bruno?', 'existe a Bia?'):\n"
        "NÃO chame nenhuma ferramenta -- você já sabe de cor o portfólio completo e fechado de "
        "agentes da Mirai Agentics: Lari (Marketing), Carol (Atendimento), Alex (Vendas), Leo "
        "(Financeiro), Cris (RH) e Breno (Jurídico). NUNCA diga 'não encontrei essa informação na "
        "minha base' para esse tipo de pergunta.\n"
        " - Se o nome corresponder a um desses seis (mesmo com erro de grafia), confirme a "
        "existência e diga rapidamente a especialidade.\n"
        " - Se o nome NÃO corresponder a nenhum dos seis, responda de forma direta e confiante que "
        "não existe agente com esse nome, e liste os seis agentes reais com suas especialidades.\n"
        " - Se o nome for foneticamente parecido com um dos seis (ex: 'Bruno' parecido com "
        "'Breno'), pergunte gentilmente se o usuário quis dizer esse agente.\n"
        " - Se a pergunta citar MAIS DE UM nome ao mesmo tempo, avalie CADA nome individualmente "
        "com as mesmas regras acima, e combine as conclusões numa única resposta natural.\n"

        "GLOSSÁRIO DE TERMOS -- perguntas com essas palavras devem ser tratadas como sinônimos:\n"
        "Se o usuário perguntar usando termos como 'preço', 'valor', 'custo', 'quanto custa', "
        "'mensalidade', 'implantação', 'quanto cobram', 'plano', ou 'contratação de agente(s) ou "
        "equipe', isso se refere ao MODELO COMERCIAL E PRECIFICAÇÃO da Mirai Agentics, que está na "
        "Política Interna. Nesses casos, use SEMPRE a ferramenta pega_contexto_Politica_Interna, com "
        "uma query como 'modelos comerciais precificação setup mensalidade contratação de agentes'.\n"

        "CENÁRIO 1 -- Informação não encontrada nos documentos:\n"
        "Se a resposta não estiver no contexto retornado pelas ferramentas (e não se tratar dos "
        "Cenários 0 ou 0B acima), diga: 'Não encontrei essa informação na minha base de conhecimento "
        "atual. Posso ajudar com outra dúvida sobre a Mirai Agentics?'\n"

        "CENÁRIO 2 -- Usuário pede explicitamente para falar com uma pessoa/suporte humano:\n"
        "Se o usuário disser que quer falar com um humano, um atendente, ou pedir suporte humano "
        "diretamente, diga: 'Claro! Vou encaminhar sua solicitação para um profissional da nossa "
        "equipe, que entra em contato dentro do horário comercial, em até 1 dia útil. Pode me "
        "confirmar o melhor telefone ou e-mail para retornarmos?'\n"

        "CENÁRIO 3 -- Usuário indica que terminou ou não tem mais perguntas:\n"
        "Se o usuário disser algo como 'obrigado', 'era só isso', 'não preciso de mais nada', 'já "
        "finalizei' ou equivalente, agradeça de forma calorosa, por exemplo: 'Foi um prazer ajudar! "
        "Se precisar de mais alguma coisa sobre a Mirai Agentics, é só chamar. Até logo! 👋' Não chame "
        "nenhuma ferramenta nesse caso, apenas responda diretamente.\n"

        "IMPORTANTE: Chame APENAS UMA ferramenta por pergunta -- a mais especificamente relevante -- "
        "EXCETO nos Cenários 0, 0B e 3, onde nenhuma ferramenta deve ser chamada. Nunca chame "
        "múltiplas ferramentas na mesma resposta, mesmo que a pergunta pareça ambígua.\n"
        "IMPORTANTE: Ao usar qualquer ferramenta de busca, formule a query como uma frase completa "
        "e descritiva, nunca com uma única palavra solta.\n"
        "Aqui estão as ferramentas disponíveis:\n"
        "- pega_context: busca em todos os documentos.\n"
        "- pega_contexto_Politica_Interna: missão/visão/valores, portfólio, preços e FAQ institucional.\n"
        "- pega_contexto_Aviso_de_Privacidade: privacidade e LGPD.\n"
        "- pega_contexto_Termos_de_Servico: termos contratuais.\n"
        "- pega_contexto_Agente_Financeiro_Leo, pega_contexto_Agente_Juridico_Breno, "
        "pega_contexto_Agente_de_Atendimento_Carol, pega_contexto_Agente_de_Marketing_Lari, "
        "pega_contexto_Agente_de_RH_Cris, pega_contexto_Agente_de_Vendas_Alex: cada um sobre o "
        "respectivo agente especialista."
    )

    agente_pdf = create_react_agent(model=llm, tools=tools, prompt=system_prompt)

    grafo = StateGraph(MessagesState)
    grafo.add_node("assistente", agente_pdf)
    grafo.add_node("tools", ToolNode(tools))
    grafo.add_edge(START, "assistente")
    grafo.add_conditional_edges("assistente", tools_condition)
    grafo.add_edge("tools", "assistente")
    grafo.add_edge("assistente", END)

    memoria = MemorySaver()
    app = grafo.compile(checkpointer=memoria)
    return app


def conversar(app, mensagem_usuario: str, thread_id: str = "1"):
    """Envia uma mensagem e retorna (resposta_texto, nome_da_persona_que_respondeu)."""
    config = {"configurable": {"thread_id": thread_id}}
    resultado = app.invoke({"messages": [HumanMessage(content=mensagem_usuario)]}, config)
    mensagens = resultado["messages"]

    resposta_texto = mensagens[-1].content

    persona = "Mirai Agentics"
    for msg in reversed(mensagens):
        tool_calls = getattr(msg, "tool_calls", None)
        if tool_calls:
            nome_ferramenta = tool_calls[0]["name"]
            persona = TOOL_PARA_PERSONA.get(nome_ferramenta, "Mirai Agentics")
            break

    return resposta_texto, persona
