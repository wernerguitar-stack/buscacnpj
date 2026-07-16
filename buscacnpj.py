import streamlit as st
import requests
import re

# ==========================================
# CONFIGURAÇÃO DO BITRIX24
# Webhook da ws4tech integrado com sucesso!
# ==========================================
BITRIX_WEBHOOK_URL = "https://ws4tech.bitrix24.com.br/rest/1/x4wyfxuclu13flj2/"

# Mapeamento dos Campos Personalizados (UF_CRM_) do Bitrix24 fornecidos por você
CAMPOS_BITRIX = {
    "RAZAO_SOCIAL": "UF_CRM_1784162578702",
    "NOME_FANTASIA": "UF_CRM_1784162602989",
    "CNPJ": "UF_CRM_1784162622733",
    "TELEFONE": "UF_CRM_1784162638701",
    "EMAIL": "UF_CRM_1784162660645",
    "ENDERECO": "UF_CRM_1784162676181",
    "CIDADE_UF": "UF_CRM_1784162700708",
    "CEP": "UF_CRM_1784162711532",
    "ATIVIDADE_PRINCIPAL": "UF_CRM_1784162732284",
    "SOCIO_PROPRIETARIO": "UF_CRM_1784210440412",  # Novo campo mapeado
    "SITUACAO_CADASTRAL": "UF_CRM_1784210464921"   # Novo campo mapeado
}

def limpar_cnpj(cnpj_raw):
    """Remove qualquer caractere que não seja número do CNPJ."""
    return re.sub(r'\D', '', cnpj_raw)

def consultar_cnpj(cnpj):
    """Consulta a API pública da ReceitaWS."""
    url = f"https://receitaws.com.br/v1/cnpj/{cnpj}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            dados = response.json()
            if dados.get("status") != "ERROR":
                return dados, None
            return None, dados.get("message", "CNPJ não encontrado.")
        elif response.status_code == 429:
            return None, "Limite de requisições atingido na ReceitaWS (máximo 3 por minuto na versão grátis). Aguarde um instante e tente novamente."
        return None, f"Erro na API (Status {response.status_code})"
    except Exception as e:
        return None, f"Erro de conexão: {str(e)}"

def criar_negocio_bitrix(dados_empresa):
    """Cria um novo negócio (Deal) no Bitrix24 com os dados coletados nos campos personalizados correspondentes."""
    # Endpoint para adicionar um negócio (Deal)
    url = f"{BITRIX_WEBHOOK_URL}crm.deal.add.json"
    
    # Extraindo dados e formatando conforme necessário
    razao_social = dados_empresa.get('nome', '')
    nome_fantasia = dados_empresa.get('fantasia', '') or 'Não informado'
    cnpj_formatado = dados_empresa.get('cnpj', '')
    telefone = dados_empresa.get('telefone', '')
    email = dados_empresa.get('email', '')
    
    # Extração das Novas Variáveis
    situacao_cadastral = dados_empresa.get('situacao', 'Não informada')
    
    qsa = dados_empresa.get('qsa', [])
    socio_proprietario = qsa[0].get('nome', 'Não informado') if qsa else 'Não informado'
    
    # Endereço completo formatado
    logradouro = dados_empresa.get('logradouro', '')
    numero = dados_empresa.get('numero', '')
    bairro = dados_empresa.get('bairro', '')
    endereco_completo = f"{logradouro}, {numero} - {bairro}"
    
    # Cidade / UF
    cidade = dados_empresa.get('municipio', '')
    uf = dados_empresa.get('uf', '')
    cidade_uf = f"{cidade} / {uf}" if cidade and uf else (cidade or uf)
    
    cep = dados_empresa.get('cep', '')
    
    # Atividade Principal
    atividades = dados_empresa.get('atividade_principal', [])
    atividade_principal = atividades[0].get('text', 'Não informada') if atividades else 'Não informada'
    
    # Construção do histórico para os comentários gerais
    comentarios = (
        f"<b>Razão Social:</b> {razao_social}<br>"
        f"<b>Nome Fantasia:</b> {nome_fantasia}<br>"
        f"<b>CNPJ:</b> {cnpj_formatado}<br>"
        f"<b>Sócio Proprietário:</b> {socio_proprietario}<br>"
        f"<b>Situação Cadastral:</b> {situacao_cadastral}<br>"
        f"<b>Telefone:</b> {telefone}<br>"
        f"<b>E-mail:</b> {email}<br>"
        f"<b>Endereço:</b> {endereco_completo}<br>"
        f"<b>Cidade/UF:</b> {cidade_uf}<br>"
        f"<b>CEP:</b> {cep}<br>"
        f"<b>Atividade Principal:</b> {atividade_principal}"
    )
    
    payload = {
        "fields": {
            "TITLE": f"Novo Cliente: {razao_social}",
            "STAGE_ID": "NEW",  # Envia para a primeira etapa do funil principal
            "OPENED": "Y",      # Deixa o card aberto e visível para a equipe
            "COMMENTS": comentarios, # Mantém também nos comentários gerais do card
            
            # Mapeamento dinâmico utilizando os seus IDs personalizados:
            CAMPOS_BITRIX["RAZAO_SOCIAL"]: razao_social,
            CAMPOS_BITRIX["NOME_FANTASIA"]: nome_fantasia,
            CAMPOS_BITRIX["CNPJ"]: cnpj_formatado,
            CAMPOS_BITRIX["TELEFONE"]: telefone,
            CAMPOS_BITRIX["EMAIL"]: email,
            CAMPOS_BITRIX["ENDERECO"]: endereco_completo,
            CAMPOS_BITRIX["CIDADE_UF"]: cidade_uf,
            CAMPOS_BITRIX["CEP"]: cep,
            CAMPOS_BITRIX["ATIVIDADE_PRINCIPAL"]: atividade_principal,
            CAMPOS_BITRIX["SOCIO_PROPRIETARIO"]: socio_proprietario,  # Novo campo enviado ao CRM
            CAMPOS_BITRIX["SITUACAO_CADASTRAL"]: situacao_cadastral   # Novo campo enviado ao CRM
        },
        "params": {
            "REGISTER_SONET_EVENT": "Y" # Dispara notificação no feed do Bitrix para a equipe
        }
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        res_json = response.json()
        if "result" in res_json:
            return res_json["result"], None # Retorna o ID do negócio criado
        return None, res_json.get("error_description", "Erro desconhecido ao integrar.")
    except Exception as e:
        return None, f"Falha na comunicação com o Bitrix: {str(e)}"

# ==========================================
# INTERFACE DO STREAMLIT
# ==========================================
st.set_page_config(page_title="Gerador de Negócios - Bitrix24", page_icon="💼", layout="centered")
# Ocultar elementos de marca do Streamlit, GitHub e "Manage app"
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .viewerBadge_container__106mG {display: none !important;}
    .viewerBadge_link__1S137 {display: none !important;}
    /* Garante que qualquer outro selo do Streamlit de rodapé suma */
    [data-testid="stHeader"] {display: none !important;}
    [data-testid="stDecoration"] {display: none !important;}
    </style>
    """, unsafe_allow_html=True)

# Cria 3 colunas para centralizar a logo (a do meio recebe a imagem)
col_esq, col_centro, col_dir = st.columns([1, 2, 1])

with col_centro:
    # Logo centralizada e maior (tamanho de 250px)
    st.image(
        "https://raw.githubusercontent.com/wernerguitar-stack/buscacnpj/main/4technew.png", 
        use_container_width=True
    )

# Subtítulo e legenda centralizados abaixo da logo
st.markdown("<h3 style='text-align: center; margin-top: -10px;'>Crie novos leads no Bitrix24</h3>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: gray;'>Conectado à organização ws4tech</p>", unsafe_allow_html=True)

st.write("---")
# Campo de entrada
cnpj_input = st.text_input("Digite o CNPJ da empresa (com ou sem pontuação):", placeholder="00.000.000/0000-00")

if st.button("Buscar CNPJ e Cadastrar", type="primary"):
    if not cnpj_input:
        st.warning("Por favor, digite um CNPJ para continuar.")
    else:
        cnpj_limpo = limpar_cnpj(cnpj_input)
        
        if len(cnpj_limpo) != 14:
            st.error("Um CNPJ válido deve conter exatamente 14 algarismos.")
        else:
            with st.spinner("Buscando dados cadastrais na ReceitaWS..."):
                dados, erro_api = consultar_cnpj(cnpj_limpo)
                
            if erro_api:
                st.error(f"Não foi possível consultar o CNPJ: {erro_api}")
            else:
                st.success("Dados cadastrais localizados!")
                
                # Obtendo dados para a visualização na tela
                situacao_cadastral_view = dados.get('situacao', 'Não informada')
                qsa_view = dados.get('qsa', [])
                socio_proprietario_view = qsa_view[0].get('nome', 'Não informado') if qsa_view else 'Não informado'
                
                # Exibe um resumo visual dos dados coletados antes de enviar
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Razão Social:** {dados.get('nome')}")
                    st.write(f"**Nome Fantasia:** {dados.get('fantasia') or 'Não informado'}")
                    st.write(f"**Sócio Proprietário:** {socio_proprietario_view}")
                with col2:
                    st.write(f"**Situação Cadastral:** {situacao_cadastral_view}")
                    st.write(f"**Telefone:** {dados.get('telefone')}")
                    st.write(f"**E-mail:** {dados.get('email')}")
                
                st.write("---")
                
                # Passo 2: Cadastra no seu Bitrix24 usando seu Webhook e IDs de campo mapeados
                with st.spinner("Criando card de negócio no Bitrix24 (ws4tech)..."):
                    deal_id, erro_bitrix = criar_negocio_bitrix(dados)
                    
                if erro_bitrix:
                    st.error(f"Erro ao criar registro no Bitrix24: {erro_bitrix}")
                else:
                    st.balloons()
                    st.success(f"🎉 **Negócio criado com sucesso!**")
                    
                    # URLs de Destino
                    url_desktop = f"https://ws4tech.bitrix24.com.br/crm/deal/details/{deal_id}/"
                    url_mobile = f"https://ws4tech.bitrix24.com.br/company/personal/user/0/tasks/task/view/0/?PATH_TO_DEAL=https://ws4tech.bitrix24.com.br/crm/deal/details/{deal_id}/"
                    
                    # Layout com duas colunas para os botões de acesso
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.link_button("💻 Abrir no Computador", url_desktop, use_container_width=True)
                    
                    with col2:
                        st.link_button("📱 Abrir no App Celular", url_mobile, use_container_width=True)
                    
                    st.info(f"ID do Card no Bitrix24: **{deal_id}**")
