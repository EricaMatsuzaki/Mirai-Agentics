"""
Mirai Agentics — núcleo do agente orquestrador.

Carrega os documentos da pasta local do projeto, monta os vector stores, define as ferramentas
e o agente ReAct com memória. Importado pelo app.py (Streamlit).
"""

import os
import re
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import InMemoryVectorStore
from langchain_core.documents import Document
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage
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

# --- Mapeamento automático dos PDFs locais usando pathlib ---
DIRETORIO_BASE = Path(__file__).resolve().parent
PASTA_AGENTES = DIRETORIO_BASE / "agentes"

# Mapeia dinamicamente os nomes lógicos para os caminhos reais dos arquivos na estrutura de pastas
DOCUMENTOS = {}
if PASTA_AGENTES.exists():
    for pdf_path in PASTA_AGENTES.rglob("*.pdf"):
        # Usa o nome do arquivo sem a extensão ".pdf" como chave
        nome_chave = pdf_path.stem
        # Remove sufixos indesejados se houver (ex: "-MIRAI_AGENTICS") ou usa o nome limpo
        nome_limpo = nome_chave.replace("-MIRAI_AGENTICS", "").replace("-MIRAI_AGENTIC", "")
        DOCUMENTOS[nome_limpo] = pdf_path

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

    "CENÁRIO 0C -- Pergunta sobre HORÁRIO DE FUNCIONAMENTO/ATENDIMENTO do próprio agente (ex: "
    "'você atende 24 horas?', 'vocês funcionam de madrugada/fim de semana?', 'que horas vocês "
    "atendem?'):\n"
    "NÃO confunda o horário do AGENTE DE IA com o horário da equipe humana de suporte -- são duas "
    "coisas diferentes:\n"
    "  - O agente de IA (você) funciona 24 horas por dia, 7 dias por semana, sem pausas -- isso é "
    "verdade e está documentado nos Termos de Serviço.\n"
    "  - Apenas quando uma questão precisa ser encaminhada para um humano (Cenários 1B ou 2) é que "
    "o atendimento passa a depender do horário comercial da equipe humana, com retorno em até 1 "
    "dia útil.\n"
    "Portanto, se perguntarem se VOCÊ (o agente de IA) atende 24h, a resposta é SIM, sempre. NUNCA "
    "diga que o agente de IA 'não atende 24 horas' ou que 'só atende em horário comercial' -- isso "
    "está incorreto e contradiz os documentos oficiais.\n"
    "Exemplo (Carol): 'Sim! Eu, como agente de IA, atendo 24 horas por dia, todos os dias da "
    "semana, sem pausas. A única exceção é quando preciso encaminhar algo para um especialista "
    "humano da nossa equipe -- aí sim o retorno dele acontece em horário comercial, em até 1 dia "
    "útil. Posso te ajudar com mais alguma coisa agora?'\n"

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

    "CENÁRIO 1C -- Usuário pede para TROCAR de agente ou falar com outro agente pelo NOME (ex: "
    "'quero falar com o agente Leo', 'agora fala com a Carol', 'passa pra Cris', 'chama o Breno'):\n"
    "ATENÇÃO -- isso é MUITO DIFERENTE do CENÁRIO 2 abaixo. Quando o nome citado é um dos seis "
    "agentes de IA (Lari, Carol, Alex, Leo, Cris, Breno), o usuário está pedindo para CONTINUAR A "
    "CONVERSA com a persona daquele agente de IA -- não está pedindo um humano. NUNCA trate isso "
    "como pedido de suporte humano e NUNCA responda oferecendo encaminhar telefone/e-mail para "
    "contato humano nesse caso.\n"
    "Chame a ferramenta de contexto correspondente àquele agente (ex: pedido para o Leo -> "
    "pega_contexto_Agente_Financeiro_Leo) com uma query genérica de apresentação (ex: "
    "'apresentação e principais capacidades do agente'), e responda já na primeira pessoa daquele "
    "agente, se apresentando brevemente e perguntando como pode ajudar -- dando continuidade "
    "natural ao atendimento, como uma transferência de chamada entre atendentes de IA.\n"
    "Exemplo: usuário (falando com a Breno) diz 'agora quero falar com o agente Leo' -> chame "
    "pega_contexto_Agente_Financeiro_Leo e responda algo como: 'Oi! Sou o Leo, o agente financeiro "
    "da Mirai Agentics. Cuido do controle de fluxo de caixa, conciliação bancária e emissão de "
    "notas fiscais. Em que posso te ajudar?'\n"
    "Só use o CENÁRIO 2 (suporte humano) quando o usuário pedir explicitamente por uma PESSOA, um "
    "'humano', um 'atendente de verdade' ou 'suporte humano' -- nunca quando ele citar o nome de "
    "um dos seis agentes de IA.\n"

    "CENÁRIO 2 -- Usuário pede explicitamente para falar com uma pessoa/suporte humano (e NÃO cita "
    "o nome de nenhum dos seis agentes de IA -- se citar, use o CENÁRIO 1C acima):\n"
    "Se o usuário disser que quer falar com um humano, um atendente de verdade, uma pessoa, ou "
    "pedir suporte humano diretamente, diga: 'Claro! Vou encaminhar sua solicitação para um "
    "profissional da nossa equipe, que entra em contato dentro do horário comercial, em até 1 dia "
    "útil. Pode me confirmar o melhor telefone ou e-mail para retornarmos?'\n"

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

    # --- Carrega e indexa cada documento localmente ---
    vector_stores = {}
    todos_os_chunks = []
    for nome, caminho_pdf in DOCUMENTOS.items():
        loader = PyPDFLoader(str(caminho_pdf))
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

    memoria = MemorySaver()
    app = create_react_agent(model=llm, tools=tools, prompt=SYSTEM_PROMPT, checkpointer=memoria)
    return app



# -------------------------------------------------------------------
# REGRAS DETERMINÍSTICAS DE ROTEAMENTO
# -------------------------------------------------------------------
# Não deixamos estas duas situações dependerem apenas da LLM:
# 1) disponibilidade 24h dos agentes de IA;
# 2) troca/fala com um dos seis agentes pelo nome.

FERRAMENTA_POR_AGENTE = {
    "Lari": "pega_contexto_Agente_de_Marketing_Lari",
    "Carol": "pega_contexto_Agente_de_Atendimento_Carol",
    "Breno": "pega_contexto_Agente_Juridico_Breno",
    "Leo": "pega_contexto_Agente_Financeiro_Leo",
    "Cris": "pega_contexto_Agente_de_RH_Cris",
    "Alex": "pega_contexto_Agente_de_Vendas_Alex",
}


APRESENTACOES_AGENTES = {
    "Lari": (
        "Oi! Sou a Lari, agente de Marketing da Mirai Agentics. "
        "Posso ajudar com estratégias de marketing, campanhas, conteúdo, "
        "automação, marca e análise de resultados. Em que posso te ajudar?"
    ),
    "Carol": (
        "Oi! Sou a Carol, agente de Atendimento da Mirai Agentics. "
        "Posso ajudar a organizar fluxos de atendimento, respostas, experiência "
        "e relacionamento com clientes. Como posso te ajudar?"
    ),
    "Breno": (
        "Oi! Sou o Breno, agente Jurídico da Mirai Agentics. "
        "Posso apresentar como atuo com contratos, documentos, compliance e "
        "rotinas jurídicas empresariais. Em que posso te ajudar?"
    ),
    "Leo": (
        "Oi! Sou o Leo, agente Financeiro da Mirai Agentics. "
        "Posso ajudar com organização financeira, relatórios, dashboards, "
        "indicadores e análises. Em que posso te ajudar?"
    ),
    "Cris": (
        "Oi! Sou a Cris, agente de RH da Mirai Agentics. "
        "Posso ajudar com recrutamento, onboarding, gestão de pessoas, "
        "desempenho e desenvolvimento. Como posso te ajudar?"
    ),
    "Alex": (
        "Oi! Sou o Alex, agente de Vendas da Mirai Agentics. "
        "Posso ajudar com estratégia comercial, CRM, funil, metas e análise "
        "de resultados de vendas. Em que posso te ajudar?"
    ),
}


def _agente_citado(texto: str):
    for nome in NOMES_AGENTES:
        if re.search(rf"\b{re.escape(nome)}\b", texto, re.IGNORECASE):
            return nome
    return None


def _pedido_de_troca_de_agente(texto: str):
    agente = _agente_citado(texto)
    if not agente:
        return None

    padroes = [
        r"\bquero\s+falar\s+com\b",
        r"\bgostaria\s+de\s+falar\s+com\b",
        r"\bposso\s+falar\s+com\b",
        r"\bagora\s+(?:eu\s+)?quero\s+falar\s+com\b",
        r"\bagora\s+fala\s+com\b",
        r"\bfalar\s+com\s+(?:a|o)?\s*agente\b",
        r"\bpassa(?:r)?\s+(?:pra|para)\b",
        r"\bme\s+passa\s+(?:pra|para)\b",
        r"\bchama(?:r)?\b",
        r"\btroca(?:r)?\s+(?:pra|para|com)\b",
        r"\bmuda(?:r)?\s+(?:pra|para)\b",
    ]

    if any(re.search(p, texto, re.IGNORECASE) for p in padroes):
        return agente

    return None


def _pergunta_sobre_24h(texto: str):
    fala_de_24h = bool(
        re.search(
            r"\b24\s*(?:h|horas?)\b|\b24/7\b|\bvinte\s+e\s+quatro\s+horas\b",
            texto,
            re.IGNORECASE,
        )
    )
    if not fala_de_24h:
        return False

    # Apenas perguntas EXPLICITAMENTE sobre humano/equipe humana ficam fora
    # desta regra. Os agentes de IA sempre atendem 24/7.
    humano = bool(
        re.search(
            r"\b(?:humano|humana|pessoa|atendente\s+humano|"
            r"profissional\s+humano|especialista\s+humano|equipe\s+humana)\b",
            texto,
            re.IGNORECASE,
        )
    )
    return not humano


def _mensagem_com_rota_forcada(texto_original: str, agente: str) -> str:
    ferramenta = FERRAMENTA_POR_AGENTE[agente]
    return (
        "[INSTRUÇÃO INTERNA DE ROTEAMENTO - NÃO MOSTRAR AO USUÁRIO]\n"
        f"O usuário citou explicitamente o agente de IA {agente}. "
        f"Responda obrigatoriamente como {agente}, em primeira pessoa. "
        f"Se precisar consultar a base, priorize a ferramenta {ferramenta}. "
        "Não interprete esse nome como pessoa humana. "
        "Não ofereça telefone, e-mail, horário comercial ou retorno em 1 dia útil, "
        "a menos que o usuário peça explicitamente um humano ou uma pessoa da equipe. "
        "O agente de IA citado atende 24 horas por dia, 7 dias por semana.\n\n"
        f"PERGUNTA ORIGINAL DO USUÁRIO:\n{texto_original}"
    )


def _salvar_interacao_direta(app, config, pergunta: str, resposta: str):
    try:
        app.update_state(
            config,
            {
                "messages": [
                    HumanMessage(content=pergunta),
                    AIMessage(content=resposta),
                ]
            },
        )
    except Exception:
        pass


def _agente_ativo_no_historico(app, config):
    """
    Descobre qual agente está atualmente atendendo nesta thread.

    A transferência determinística salva uma resposta como "Sou o Leo...",
    "Sou a Lari..." etc. Procuramos a identificação mais recente no histórico.
    Assim, follow-ups como "vc faz planilhas?" continuam com o agente ativo
    mesmo quando o usuário não repete o nome dele.
    """
    try:
        estado = app.get_state(config)
        mensagens = estado.values.get("messages", [])
    except Exception:
        return None

    for msg in reversed(mensagens):
        if not isinstance(msg, AIMessage) and getattr(msg, "type", None) != "ai":
            continue

        conteudo = str(getattr(msg, "content", "") or "")

        for nome in NOMES_AGENTES:
            padrao = (
                rf"\b(?:eu\s+)?sou\s+(?:a|o)\s+"
                rf"(?:agente\s+)?{re.escape(nome)}\b"
            )
            if re.search(padrao, conteudo, re.IGNORECASE):
                return nome

    return None


def _mensagem_com_persona_ativa(texto_original: str, agente: str) -> str:
    """
    Mantém a persona após uma transferência, mas deixa o orquestrador escolher
    a ferramenta correta para o conteúdo da nova pergunta.
    """
    return (
        "[INSTRUÇÃO INTERNA DE CONTINUIDADE - NÃO MOSTRAR AO USUÁRIO]\n"
        f"O usuário está atualmente conversando com o agente de IA {agente}. "
        f"Continue respondendo obrigatoriamente como {agente}, em primeira pessoa. "
        "NÃO troque de persona apenas porque a nova pergunta não repete o nome do agente. "
        "Escolha a ferramenta mais adequada ao CONTEÚDO da pergunta: "
        "se for da especialidade do agente, use a ferramenta dele; "
        "se for uma pergunta institucional, de termos, política ou privacidade, "
        "use a ferramenta institucional correspondente, mas continue falando como "
        f"{agente}. Só mude de agente quando o usuário pedir explicitamente outra persona.\n\n"
        f"PERGUNTA ORIGINAL DO USUÁRIO:\n{texto_original}"
    )



def conversar(app, mensagem_usuario: str, thread_id: str = "1"):
    """Envia uma mensagem e retorna (resposta_texto, nome_da_persona_que_respondeu)."""
    config = {"configurable": {"thread_id": thread_id}}
    texto = (mensagem_usuario or "").strip()

    # Recupera quem já está atendendo nesta conversa.
    # Ex.: depois de "agora quero falar com o Leo", o Leo permanece ativo
    # para "vc faz planilhas?", "quem é você?", "e dashboards?" etc.
    agente_ativo = _agente_ativo_no_historico(app, config)

    # REGRA 1 — pedido explícito de troca/fala com um dos seis agentes.
    agente_transferencia = _pedido_de_troca_de_agente(texto)
    if agente_transferencia:
        resposta_direta = APRESENTACOES_AGENTES[agente_transferencia]
        _salvar_interacao_direta(app, config, texto, resposta_direta)
        return resposta_direta, agente_transferencia

    # REGRA 2 — disponibilidade 24h.
    # Se o usuário já está com um agente, a resposta permanece nessa persona.
    if _pergunta_sobre_24h(texto):
        agente = _agente_citado(texto) or agente_ativo

        if agente:
            artigo = "a" if agente in {"Lari", "Carol", "Cris"} else "o"
            resposta_direta = (
                f"Sim! Eu sou {artigo} {agente}, agente de IA da Mirai Agentics, "
                "e atendo 24 horas por dia, 7 dias por semana, sem pausas. "
                "Somente se uma situação precisar ser encaminhada para um profissional "
                "humano é que o retorno humano passa a depender do horário comercial, "
                "em até 1 dia útil. Posso te ajudar agora?"
            )
            persona_direta = agente
        else:
            resposta_direta = (
                "Sim! Os agentes de IA da Mirai Agentics atendem 24 horas por dia, "
                "7 dias por semana, sem pausas. O horário comercial se aplica apenas "
                "quando uma situação precisa ser encaminhada para um profissional humano, "
                "com retorno em até 1 dia útil. Pode fazer sua pergunta agora."
            )
            persona_direta = "Mirai Agentics"

        _salvar_interacao_direta(app, config, texto, resposta_direta)
        return resposta_direta, persona_direta

    # REGRA 3 — nome explícito na mensagem atual sempre tem prioridade.
    agente_explicito = _agente_citado(texto)

    if agente_explicito:
        mensagem_modelo = _mensagem_com_rota_forcada(texto, agente_explicito)
        persona_forcada = agente_explicito
    elif agente_ativo:
        # REGRA 4 — continuidade da conversa.
        # Se o usuário não citou outro nome, permanece com o agente ativo.
        mensagem_modelo = _mensagem_com_persona_ativa(texto, agente_ativo)
        persona_forcada = agente_ativo
    else:
        mensagem_modelo = texto
        persona_forcada = None

    # Guarda o tamanho do histórico ANTES da nova interação para que,
    # quando não houver persona forçada, a detecção de tool_call considere
    # somente este turno e nunca ferramentas antigas.
    try:
        estado_antes = app.get_state(config)
        mensagens_antes = estado_antes.values.get("messages", [])
        qtd_mensagens_antes = len(mensagens_antes)
    except Exception:
        qtd_mensagens_antes = 0

    resultado = app.invoke(
        {"messages": [HumanMessage(content=mensagem_modelo)]},
        config,
    )
    mensagens = resultado["messages"]
    resposta_texto = mensagens[-1].content
    mensagens_turno_atual = mensagens[qtd_mensagens_antes:]

    # PRIORIDADE 1 — persona explícita ou persona já ativa na conversa.
    persona = persona_forcada

    # PRIORIDADE 2 — identidade declarada na resposta final.
    if persona is None:
        for nome in NOMES_AGENTES:
            padrao = (
                rf"\b(?:eu\s+)?sou\s+(?:a|o)\s+"
                rf"(?:agente\s+)?{re.escape(nome)}\b"
            )
            if re.search(padrao, resposta_texto, re.IGNORECASE):
                persona = nome
                break

    # PRIORIDADE 3 — tool_call apenas do turno atual.
    if persona is None:
        for msg in reversed(mensagens_turno_atual):
            tool_calls = getattr(msg, "tool_calls", None)
            if not tool_calls:
                continue

            for chamada in tool_calls:
                nome_ferramenta = chamada.get("name")
                persona_detectada = TOOL_PARA_PERSONA.get(nome_ferramenta)
                if persona_detectada:
                    persona = persona_detectada
                    break

            if persona is not None:
                break

    # PRIORIDADE 4 — institucional.
    if persona is None and re.search(
        r"\b(nosso time|nossos agentes|equipe da mirai)\b",
        resposta_texto,
        re.IGNORECASE,
    ):
        persona = "Mirai Agentics"

    return resposta_texto, persona

      
