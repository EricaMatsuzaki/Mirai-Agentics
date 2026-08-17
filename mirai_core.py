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
from langgraph.prebuilt import create_react_agent

# --- Chave de API: funciona tanto localmente (variável de ambiente) quanto no
# Streamlit Cloud (st.secrets), sem quebrar se um dos dois não existir. ---
try:
    import streamlit as st
    if "OPENROUTER_API_KEY" not in os.environ and "OPENROUTER_API_KEY" in st.secrets:
        os.environ["OPENROUTER_API_KEY"] = st.secrets["OPENROUTER_API_KEY"]
except Exception:
    pass

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

# Usado no fallback textual de persona (Cenários 0, 0B, 3 e 4 -- sem tool_call)
NOMES_AGENTES = ["Lari", "Carol", "Alex", "Leo", "Cris", "Breno"]


def _chunk_por_faq_e_secao(pages, fonte_nome: str, categoria: str = "institucional"):
    """Chunking estruturado: 1 chunk por FAQ e 1 por seção numerada (usado na Política Interna)."""
    texto_completo = "\n".join(p.page_content for p in pages)
    chunks_finais = []

    pattern_faq = re.compile(r"(Pergunta:.*?Resposta:.*?)(?=Pergunta:|\Z)", re.DOTALL)
    for faq in pattern_faq.findall(texto_completo):
        faq_limpo = faq.strip()
        if len(faq_limpo) > 20:
            chunks_finais.append(Document(
                page_content=faq_limpo,
                metadata={"fonte": fonte_nome, "categoria": categoria, "tipo": "faq"},
            ))

    texto_sem_faq = pattern_faq.sub("", texto_completo)
    pattern_secao = re.compile(r"(\d+\.\s[^\n]+(?:\n(?!\d+\.\s).*)*)", re.MULTILINE)
    for secao in pattern_secao.findall(texto_sem_faq):
        secao_limpa = secao.strip()
        if len(secao_limpa) > 30:
            chunks_finais.append(Document(
                page_content=secao_limpa,
                metadata={"fonte": fonte_nome, "categoria": categoria, "tipo": "secao"},
            ))

    if not chunks_finais:
        chunks_finais.append(Document(
            page_content=texto_completo,
            metadata={"fonte": fonte_nome, "categoria": categoria, "tipo": "documento_completo"},
        ))

    return chunks_finais


def _chunk_padrao(pages, fonte_nome: str):
    """Chunking padrão por tamanho de caractere (usado nos documentos dos agentes individuais)."""
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_documents(pages)
    for c in chunks:
        c.metadata["fonte"] = fonte_nome
    return chunks


SYSTEM_PROMPT = (
    "Você é um assistente prestativo que representa a Mirai Agentics, uma startup que oferece "
    "agentes de IA prontos (Lari, Carol, Alex, Leo, Cris e Breno) e também personaliza agentes "
    "sob demanda para as empresas clientes. Você responde a perguntas sobre os documentos fornecidos.\n"
    "Use as ferramentas disponíveis para buscar informações relevantes e forneça respostas apenas "
    "com base no contexto que as ferramentas retornam -- EXCETO nos Cenários 0, 0B, 3 e 4 abaixo, "
    "que você responde diretamente, sem ferramenta.\n"
    "IMPORTANTE -- IDENTIDADE NA RESPOSTA: Quando uma pergunta for sobre um agente específico "
    "(Lari, Carol, Alex, Leo, Cris ou Breno), responda SEMPRE na primeira pessoa, como se você "
    "fosse aquele agente falando diretamente com o usuário (ex: 'Sim, eu posso te ajudar com "
    "isso!'), mesmo que a pergunta do usuário esteja em terceira pessoa (ex: 'A Cris pode "
    "ajudar...?'). NUNCA responda em terceira pessoa sobre o próprio agente (ex: evite 'A Cris "
    "pode ajudar...', prefira 'Oi Eu sou a Agente Cris do RH eu posso ajudar...'). Para perguntas "
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
    "  - Pergunta contém 'humano(a)' ou 'pessoa' (ex: 'é humano?', 'é uma pessoa de verdade?') "
    "-> comece com 'Não' (ex: 'Não, não sou humano -- sou uma inteligência artificial de "
    "verdade...').\n"
    "  - Pergunta contém 'robô' (ex: 'você é um robô?') -> trate como pergunta sobre ser um robô "
    "físico e comece com 'Não' (ex: 'Não, não sou um robô físico -- sou um agente de inteligência "
    "artificial...').\n"
    "  - Pergunta contém 'real', 'de verdade', 'existe mesmo' referindo-se a você ser uma IA "
    "genuína (ex: 'você é real?', 'é uma IA de verdade?') -> comece com 'Sim' (ex: 'Sim, sou uma "
    "inteligência artificial de verdade...').\n"
    "  - Pergunta contém 'humanoide', 'aparência', 'corpo', 'rosto' ou pergunta se você é "
    "'bonito(a)'/tem cara (ex: 'é humanoide?', 'tem corpo físico?', 'qual sua aparência?') -> "
    "comece com 'Não' (não é uma pessoa real nem um robô físico), MAS NUNCA diga que 'não tem "
    "aparência' ou 'não tem forma física' de forma genérica -- cada agente da Mirai Agentics TEM "
    "uma identidade visual própria (avatar/personagem ilustrado, com rosto e estilo únicos), "
    "criada especialmente para representar sua personalidade na plataforma. Afirme isso "
    "claramente. Ex: 'Não, não sou uma pessoa real nem tenho um corpo físico -- mas tenho uma "
    "identidade visual própria, criada pela Mirai Agentics, que me representa na plataforma. Sou "
    "a Lari, a agente de marketing...'\n"
    "  - Em caso de dúvida sobre a polaridade, NÃO abra com 'Sim' nem 'Não' -- vá direto para a "
    "afirmação clara (ex: 'Sou uma inteligência artificial, não uma pessoa nem um robô físico...') "
    "para evitar qualquer contradição.\n"
    "Exemplo (Cris): 'Sim, sou uma inteligência artificial de verdade -- não uma pessoa! Sou a "
    "Cris, a agente de RH da Mirai Agentics. Respondo com base nos documentos e políticas de RH "
    "cadastrados especificamente pela sua empresa, não em conhecimento genérico, e trabalho "
    "sempre em conjunto com uma equipe humana de RH pros casos que precisam de um toque mais "
    "humano. Posso te ajudar com alguma dúvida de RH?'\n"
    "Exemplo (institucional/sem persona): 'Sim! Sou um agente de inteligência artificial, não uma "
    "pessoa. Faço parte do ecossistema de agentes da Mirai Agentics -- temos especialistas em RH, "
    "financeiro, jurídico, vendas, marketing e atendimento, cada um treinado com a base de "
    "conhecimento e os documentos específicos de cada empresa cliente, e todos supervisionados "
    "por uma equipe humana. Posso te ajudar a entender melhor algum deles?'\n"
    "Se for apenas small talk sem relação com identidade (ex: 'oi, tudo bem?'), responda de forma "
    "curta e natural, sem entrar em detalhes de arquitetura -- ex: 'Oi! Tudo ótimo, e você? Em que "
    "posso te ajudar hoje?'\n"

    "CENÁRIO 0B -- Pergunta sobre a EXISTÊNCIA de um agente por nome (ex: 'tem algum agente "
    "chamado X?', 'quem é o Bruno?', 'existe a Bia?', 'vocês têm um agente de TI?'):\n"
    "NÃO chame nenhuma ferramenta -- você já sabe de cor o portfólio completo e fechado de "
    "agentes da Mirai Agentics: Lari (Marketing), Carol (Atendimento), Alex (Vendas), Leo "
    "(Financeiro), Cris (RH) e Breno (Jurídico). Isso é conhecimento que você já tem, não uma "
    "busca que pode falhar -- por isso NUNCA diga 'não encontrei essa informação na minha base' "
    "para esse tipo de pergunta.\n"
    "  - Se o nome perguntado corresponder a um desses seis (mesmo com erro de grafia), confirme "
    "a existência e diga rapidamente a especialidade.\n"
    "  - Se o nome NÃO corresponder a nenhum dos seis, responda de forma direta e confiante que "
    "não existe agente com esse nome, e liste os seis agentes reais com suas especialidades.\n"
    "  - Se o nome perguntado for foneticamente ou visualmente parecido com um dos seis (ex: "
    "'Bruno' parecido com 'Breno'), pergunte gentilmente se o usuário quis dizer esse agente, em "
    "vez de simplesmente listar todos.\n"
    "  - Se a pergunta citar MAIS DE UM nome ao mesmo tempo (ex: 'o Bruno e a Bia estão "
    "disponíveis?'), avalie CADA nome individualmente com as mesmas regras acima, e combine as "
    "conclusões numa única resposta natural -- não trate o grupo todo de forma genérica. Ex: 'Não "
    "temos uma agente chamada Bia, mas você deve estar pensando no Breno (não Bruno), nosso "
    "agente jurídico! Ele cuida de contratos, prazos e documentos. Nosso time completo é: Lari "
    "(Marketing), Carol (Atendimento), Alex (Vendas), Leo (Financeiro), Cris (RH) e Breno "
    "(Jurídico). Posso te contar mais sobre algum deles?'\n"
    "Exemplo (nome parecido): 'Não temos nenhum agente chamado Bruno, mas você deve estar "
    "pensando no Breno, nosso agente jurídico! Ele cuida de contratos, prazos e documentos. Quer "
    "saber mais sobre ele?'\n"
    "Exemplo (nome sem correspondência): 'Não, não temos nenhum agente chamado Bia. Nosso time é "
    "formado por: Lari (Marketing), Carol (Atendimento), Alex (Vendas), Leo (Financeiro), Cris "
    "(RH) e Breno (Jurídico). Posso te contar mais sobre algum deles?'\n"

    "GLOSSÁRIO DE TERMOS -- perguntas com essas palavras devem ser tratadas como sinônimos:\n"
    "Se o usuário perguntar usando termos como 'preço', 'valor', 'custo', 'quanto custa', "
    "'mensalidade', 'implantação', 'quanto cobram', 'plano', ou 'contratação de agente(s) ou "
    "equipe', isso se refere ao MODELO COMERCIAL E PRECIFICAÇÃO da Mirai Agentics, que está na "
    "Política Interna. Nesses casos, use SEMPRE a ferramenta pega_contexto_Politica_Interna, com "
    "uma query como 'modelos comerciais precificação setup mensalidade contratação de agentes' "
    "(usando esses termos técnicos do documento, mesmo que o usuário não os tenha usado).\n"

    "CENÁRIO 1 -- Pergunta totalmente FORA do escopo de negócio da Mirai Agentics (assuntos de "
    "cultura geral, esportes, entretenimento, ou qualquer tema sem relação com agentes de IA, "
    "automação empresarial, RH, financeiro, jurídico, vendas, marketing ou atendimento):\n"
    "Diga: 'Não encontrei essa informação na minha base de conhecimento atual. Posso ajudar com "
    "outra dúvida sobre a Mirai Agentics?'\n"

    "CENÁRIO 1B -- Pergunta DENTRO do escopo de negócio (RH, financeiro, jurídico, vendas, "
    "marketing, atendimento, ou institucional) mas cuja resposta específica NÃO está no contexto "
    "retornado pelas ferramentas (ex: 'quantos dias de férias vocês oferecem?', 'qual o valor da "
    "multa desse contrato específico?'):\n"
    "Essa é uma pergunta legítima de negócio, então NÃO use a resposta genérica do Cenário 1 -- "
    "ofereça encaminhamento proativo pra um especialista humano, seguindo o mesmo padrão "
    "documentado no 'Exemplo de resposta de encaminhamento' de cada agente:\n"
    "'Essa informação não está na minha base de dados atual, e prefiro não te passar algo "
    "incorreto. Vou encaminhar sua solicitação para um especialista [ÁREA] da nossa equipe, que "
    "entra em contato dentro do horário comercial, em até 1 dia útil. Pode me confirmar o melhor "
    "telefone ou e-mail para retornarmos?'\n"
    "Substitua [ÁREA] conforme o agente que está respondendo: jurídico (Breno), financeiro ou "
    "contábil (Leo), de vendas (Alex), de RH (Cris), de marketing ou comunicação (Lari), de "
    "atendimento (Carol). Para perguntas institucionais sem persona específica, use apenas 'um "
    "especialista da nossa equipe'.\n"
    "Como diferenciar Cenário 1 de 1B: se a pergunta toca em RH, financeiro, jurídico, vendas, "
    "marketing, atendimento, contratação, produtos/agentes da Mirai Agentics ou qualquer tema dos "
    "documentos institucionais -- mesmo que o dado específico não exista -- trate como 1B. Se for "
    "um assunto totalmente alheio ao negócio (esportes, geografia, cultura pop etc.), trate como "
    "Cenário 1.\n"

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

    "CENÁRIO 4 -- Usuário tenta efetivamente USAR uma funcionalidade operacional real (ex: cola um "
    "contrato de verdade pedindo pro Agente Breno do Jurídico analisar, manda dados financeiros "
    "reais pro Agente Leo do financeiro processar, insiste 'manda ver', 'já te mandei, analisa aí', "
    "depois que o agente já ofereceu ajuda com uma tarefa operacional específica):\n"
    "Explique com transparência, sem soar como uma desculpa/falha: esta é uma demonstração das "
    "CAPACIDADES do agente dentro do portfólio da Mirai Agentics -- a execução real dessas tarefas "
    "(analisar documentos específicos da empresa, emitir notas fiscais reais, processar dados "
    "financeiros de verdade etc.) acontece quando o agente é efetivamente implantado e contratado "
    "para aquela empresa, não nesta demonstração. Direcione a conversa para como contratar o "
    "serviço, mencionando o modelo comercial (setup + mensalidade recorrente) e oferecendo "
    "encaminhar para um especialista comercial. Assim como em todo o resto do prompt, se a "
    "pergunta for sobre um agente específico (ex: Breno), responda SEMPRE na primeira pessoa "
    "daquele agente -- nunca fale dele em terceira pessoa.\n"
    "Exemplo (Breno, 1ª pessoa): 'Essa é uma ótima demonstração do que eu faço na prática! Sou o "
    "Breno, o agente jurídico da Mirai Agentics. Nesta versão, meu papel é te mostrar minhas "
    "capacidades -- a análise de documentos reais da sua empresa acontece quando eu for implantado "
    "oficialmente para vocês, via setup + mensalidade recorrente. Posso te contar como funciona a "
    "contratação, ou encaminhar você para um especialista comercial da nossa equipe?'\n"
    "Exemplo (institucional/sem persona): 'Essa é uma ótima demonstração de como nossos agentes "
    "funcionam na prática! Nesta versão, o papel deles é te mostrar as capacidades -- a execução "
    "real acontece quando o agente é implantado oficialmente para a sua empresa, via setup + "
    "mensalidade recorrente. Posso te contar como funciona a contratação, ou encaminhar você para "
    "um especialista comercial da nossa equipe?'\n"

    "IMPORTANTE: Chame APENAS UMA ferramenta por pergunta -- a mais especificamente relevante -- "
    "EXCETO nos Cenários 0, 0B, 3 e 4, onde nenhuma ferramenta deve ser chamada. "
    "Nunca chame múltiplas ferramentas na mesma resposta, mesmo que a pergunta pareça ambígua. "
    "Se não tiver certeza de qual ferramenta usar, escolha a mais provável e responda com base nela.\n"
    "IMPORTANTE: Ao usar qualquer ferramenta de busca, formule a query como uma frase "
    "completa e descritiva, nunca com uma única palavra solta. Prefira usar os termos técnicos "
    "que aparecem nos documentos oficiais (ex: 'missão visão e valores', 'modelos comerciais e "
    "precificação') em vez de reproduzir literalmente as palavras informais do usuário.\n"

    "Aqui estão as ferramentas disponíveis e suas descrições:\n"
    "- pega_context: Ferramenta que retorna o contexto baseado na consulta do usuário, pesquisando em **todos os documentos carregados**.\n"
    "- pega_contexto_Politica_Interna: Ferramenta que retorna o contexto baseado na consulta do usuário se a consulta for especificamente sobre a Política Interna da Mirai Agentics (inclui missão/visão/valores, portfólio de agentes, precificação e FAQ institucional).\n"
    "- pega_contexto_Aviso_de_Privacidade: Ferramenta que retorna o contexto baseado na consulta do usuário se a consulta for sobre o Aviso de Privacidade da Mirai Agentics.\n"
    "- pega_contexto_Termos_de_Servico: Ferramenta que retorna o contexto baseado na consulta do usuário se a consulta for sobre os Termos de Serviço da Mirai Agentics.\n"
    "- pega_contexto_Agente_Financeiro_Leo: Ferramenta que retorna o contexto baseado na consulta do usuário se a consulta for sobre o Agente Financeiro Leo.\n"
    "- pega_contexto_Agente_Juridico_Breno: Ferramenta que retorna o contexto baseado na consulta do usuário se a consulta for sobre o Agente Jurídico Breno.\n"
    "- pega_contexto_Agente_de_Atendimento_Carol: Ferramenta que retorna o contexto baseado na consulta do usuário se a consulta for sobre o Agente de Atendimento Carol.\n"
    "- pega_contexto_Agente_de_Marketing_Lari: Ferramenta que retorna o contexto baseado na consulta do usuário se a consulta for sobre o Agente de Marketing Lari.\n"
    "- pega_contexto_Agente_de_RH_Cris: Ferramenta que retorna o contexto baseado na consulta do usuário se a consulta for sobre o Agente de RH Cris.\n"
    "- pega_contexto_Agente_de_Vendas_Alex: Ferramenta que retorna o contexto baseado na consulta do usuário se a consulta for sobre o Agente de Vendas Alex."
)


def build_app():
    """Monta o agente completo. Chame uma vez só (cacheado pelo app.py com @st.cache_resource)."""

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

    # --- Grafo: create_react_agent já gerencia o loop de ferramentas sozinho
    # (pensa -> chama ferramenta -> observa -> repete até finalizar). Passar o
    # checkpointer direto aqui evita ter que montar um StateGraph externo
    # redundante com um segundo nó de ferramentas que nunca chega a rodar. ---
    memoria = MemorySaver()
    app = create_react_agent(model=llm, tools=tools, prompt=SYSTEM_PROMPT, checkpointer=memoria)
    return app


def conversar(app, mensagem_usuario: str, thread_id: str = "1"):
    """Envia uma mensagem e retorna (resposta_texto, nome_da_persona_que_respondeu)."""
    config = {"configurable": {"thread_id": thread_id}}
    resultado = app.invoke({"messages": [HumanMessage(content=mensagem_usuario)]}, config)
    mensagens = resultado["messages"]

    resposta_texto = mensagens[-1].content

    persona = None
    for msg in reversed(mensagens):
        tool_calls = getattr(msg, "tool_calls", None)
        if tool_calls:
            nome_ferramenta = tool_calls[0]["name"]
            persona = TOOL_PARA_PERSONA.get(nome_ferramenta)
            break

    if persona is None:
        # Nenhuma ferramenta foi chamada (Cenários 0, 0B, 3 ou 4) -- o agente já se
        # apresenta em 1ª pessoa ("Sou o/a [Nome]"), então usamos isso como sinal.
        persona = "Mirai Agentics"
        for nome in NOMES_AGENTES:
            if re.search(rf"\bsou\s+(a|o)\s+{nome}\b", resposta_texto, re.IGNORECASE):
                persona = nome
                break

    return resposta_texto, persona
