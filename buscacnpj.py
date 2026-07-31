import streamlit as st
import requests
import re

# ==========================================
# CONFIGURAÇÃO DO BITRIX24
# ==========================================
BITRIX_WEBHOOK_URL = "https://ws4tech.bitrix24.com.br/rest/1/x4wyfxuclu13flj2/"

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
    "SOCIO_PROPRIETARIO": "UF_CRM_1784210440412",
    "SITUACAO_CADASTRAL": "UF_CRM_1784210464921",
    "ENVIAR_APRESENTACAO": "UF_CRM_1784764305562" 
}

def limpar_cnpj(cnpj_raw):
    return re.sub(r'\D', '', cnpj_raw)

def consultar_cnpj(cnpj):
    url = f"https://receitaws.com.br/v1/cnpj/{cnpj}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            dados = response.json()
            if dados.get("status") != "ERROR":
                return dados, None
            return None, dados.get("message", "CNPJ não encontrado.")
        elif response.status_code == 429:
            return None, "Limite de requisições atingido na ReceitaWS. Aguarde um instante e tente novamente."
        return None, f"Erro na API (Status {response.status_code})"
    except Exception as e:
        return None, f"Erro de conexão: {str(e)}"

def criar_empresa_bitrix(dados_empresa):
    """Cria o cadastro da Empresa no CRM do Bitrix24 e retorna o ID da Empresa."""
    url = f"{BITRIX_WEBHOOK_URL}crm.company.add.json"
    
    razao_social = dados_empresa.get('nome', '')
    nome_fantasia = dados_empresa.get('fantasia', '') or razao_social
    cnpj_formatado = dados_empresa.get('cnpj', '')
    telefone = dados_empresa.get('telefone_editado', '')
    email = dados_empresa.get('email_editado', '')
    
    payload = {
        "fields": {
            "TITLE": razao_social,
            "COMPANY_TYPE": "CUSTOMER", # Cliente
            "PHONE": [{"VALUE": telefone, "VALUE_TYPE": "WORK"}] if telefone else [],
            "EMAIL": [{"VALUE": email, "VALUE_TYPE": "WORK"}] if email else [],
            CAMPOS_BITRIX["CNPJ"]: cnpj_formatado,
            CAMPOS_BITRIX["RAZAO_SOCIAL"]: razao_social,
            CAMPOS_BITRIX["NOME_FANTASIA"]: nome_fantasia
        }
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        res_json = response.json()
        if "result" in res_json:
            return res_json["result"], None
        return None, res_json.get("error_description", "Erro ao criar Empresa.")
    except Exception as e:
        return None, f"Falha ao cadastrar empresa: {str(e)}"

def criar_contato_bitrix(dados_empresa, company_id=None):
    """Cria o cadastro do Contato no CRM do Bitrix24 e o vincula à Empresa se informado."""
    url = f"{BITRIX_WEBHOOK_URL}crm.contact.add.json"
    
    nome_socio = dados_empresa.get('socio_editado', 'Contato sem nome')
    telefone = dados_empresa.get('telefone_editado', '')
    email = dados_empresa.get('email_editado', '')
    
    payload = {
        "fields": {
            "NAME": nome_socio,
            "TYPE_ID": "CLIENT",
            "COMPANY_ID": company_id if company_id else "",
            "PHONE": [{"VALUE": telefone, "VALUE_TYPE": "WORK"}] if telefone else [],
            "EMAIL": [{"VALUE": email, "VALUE_TYPE": "WORK"}] if email else []
        }
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        res_json = response.json()
        if "result" in res_json:
            return res_json["result"], None
        return None, res_json.get("error_description", "Erro ao criar Contato.")
    except Exception as e:
        return None, f"Falha ao cadastrar contato: {str(e)}"

def criar_negocio_bitrix(dados_empresa, enviar_apresentacao, company_id=None, contact_id=None):
    """Cria um novo negócio no Bitrix24 vinculando a Empresa e o Contato."""
    url = f"{BITRIX_WEBHOOK_URL}crm.deal.add.json"
    
    razao_social = dados_empresa.get('nome', '')
    nome_fantasia = dados_empresa.get('fantasia', '') or 'Não informado'
    cnpj_formatado = dados_empresa.get('cnpj', '')
    
    telefone = dados_empresa.get('telefone_editado', '')
    email = dados_empresa.get('email_editado', '')
    socio_proprietario = dados_empresa.get('socio_editado', '')
    situacao_cadastral = dados_empresa.get('situacao', 'Não informada')
    
    logradouro = dados_empresa.get('logradouro', '')
    numero = dados_empresa.get('numero', '')
    bairro = dados_empresa.get('bairro', '')
    endereco_completo = f"{logradouro}, {numero} - {bairro}"
    
    cidade = dados_empresa.get('municipio', '')
    uf = dados_empresa.get('uf', '')
    cidade_uf = f"{cidade} / {uf}" if cidade and uf else (cidade or uf)
    
    cep = dados_empresa.get('cep', '')
    atividades = dados_empresa.get('atividade_principal', [])
    atividade_principal = atividades[0].get('text', 'Não informada') if atividades else 'Não informada'
    
    status_apresentacao = "Sim" if enviar_apresentacao else "Não"
    
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
        f"<b>Atividade Principal:</b> {atividade_principal}<br>"
        f"<b>Enviar Apresentação:</b> {status_apresentacao}"
    )
    
    fields = {
        "TITLE": f"Novo Cliente: {razao_social}",
        "STAGE_ID": "NEW",
        "OPENED": "Y",
        "COMMENTS": comentarios,
        
        # 🔗 VÍNCULO COM EMPRESA E CONTATO
        "COMPANY_ID": company_id if company_id else "",
        "CONTACT_ID": contact_id if contact_id else "",
        
        # Mapeamento dos campos personalizados
        CAMPOS_BITRIX["RAZAO_SOCIAL"]: razao_social,
        CAMPOS_BITRIX["NOME_FANTASIA"]: nome_fantasia,
        CAMPOS_BITRIX["CNPJ"]: cnpj_formatado,
        CAMPOS_BITRIX["TELEFONE"]: telefone,
        CAMPOS_BITRIX["EMAIL"]: email,
        CAMPOS_BITRIX["ENDERECO"]: endereco_completo,
        CAMPOS_BITRIX["CIDADE_UF"]: cidade_uf,
        CAMPOS_BITRIX["CEP"]: cep,
        CAMPOS_BITRIX["ATIVIDADE_PRINCIPAL"]: atividade_principal,
        CAMPOS_BITRIX["SOCIO_PROPRIETARIO"]: socio_proprietario,
        CAMPOS_BITRIX["SITUACAO_CADASTRAL"]: situacao_cadastral,
        CAMPOS_BITRIX["ENVIAR_APRESENTACAO"]: "Y" if enviar_apresentacao else "N"
    }
    
    payload = {
        "fields": fields,
        "params": {
            "REGISTER_SONET_EVENT": "Y"
        }
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        res_json = response.json()
        if "result" in res_json:
            return res_json["result"], None
        return None, res_json.get("error_description", "Erro desconhecido ao integrar.")
    except Exception as e:
        return None, f"Falha na comunicação com o Bitrix: {str(e)}"

# ==========================================
# INTERFACE DO STREAMLIT
# ==========================================
st.set_page_config(page_title="Gerador de Negócios - Bitrix24", page_icon="💼", layout="centered")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .viewerBadge_container__106mG, .viewerBadge_link__1S137 {display: none !important;}
    [data-testid="stHeader"] {display: none !important;}
    [data-testid="stDecoration"] {display: none !important;}
    [data-testid="stStatusWidget"] {visibility: hidden; height: 0px; display: none !important;}
    .stAppDeployButton {display: none !important;}
    </style>
    """, unsafe_allow_html=True)

col_esq, col_centro, col_dir = st.columns([1, 2, 1])
with col_centro:
    st.image(
        "https://raw.githubusercontent.com/wernerguitar-stack/buscacnpj/main/4technew.png", 
        use_container_width=True
    )

st.markdown("<h3 style='text-align: center; margin-top: -10px;'>Crie novos leads no Bitrix24</h3>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: gray;'>Conectado à organização ws4tech</p>", unsafe_allow_html=True)

st.write("---")

if "dados_cnpj" not in st.session_state:
    st.session_state.dados_cnpj = None

cnpj_input = st.text_input("Digite o CNPJ da empresa (com ou sem pontuação):", placeholder="00.000.000/0000-00")

if st.button("Buscar CNPJ", type="secondary", use_container_width=True):
    if not cnpj_input:
        st.warning("Por favor, digite um CNPJ para continuar.")
        st.session_state.dados_cnpj = None
    else:
        cnpj_limpo = limpar_cnpj(cnpj_input)
        if len(cnpj_limpo) != 14:
            st.error("Um CNPJ válido deve conter exatamente 14 algarismos.")
            st.session_state.dados_cnpj = None
        else:
            with st.spinner("Buscando dados cadastrais na ReceitaWS..."):
                dados, erro_api = consultar_cnpj(cnpj_limpo)
            if erro_api:
                st.error(f"Não foi possível consultar o CNPJ: {erro_api}")
                st.session_state.dados_cnpj = None
            else:
                st.session_state.dados_cnpj = dados

if st.session_state.dados_cnpj:
    dados = st.session_state.dados_cnpj
    st.success("Dados cadastrais localizados!")
    
    qsa_view = dados.get('qsa', [])
    socio_padrao = qsa_view[0].get('nome', '') if qsa_view else ''
    telefone_padrao = dados.get('telefone', '')
    email_padrao = dados.get('email', '')
    
    st.write(f"**Razão Social:** {dados.get('nome')}")
    st.write(f"**Nome Fantasia:** {dados.get('fantasia') or 'Não informado'}")
    st.write(f"**Situação Cadastral:** {dados.get('situacao')}")
    
    st.write("---")
    st.caption("✏️ **Campos de contato:**")
    
    socio_editado = st.text_input("Sócio / Proprietário:", value=socio_padrao)
    telefone_editado = st.text_input("Telefone de Contato:", value=telefone_padrao)
    email_editado = st.text_input("E-mail de Contato:", value=email_padrao)
    
    enviar_apresentacao = st.checkbox("✉️ Enviar Apresentação Comercial automaticamente para este e-mail", value=True)
    
    st.write("---")
    
    if st.button("📌 Cadastrar CNPJ no Bitrix24", type="primary", use_container_width=True):
        dados['socio_editado'] = socio_editado
        dados['telefone_editado'] = telefone_editado
        dados['email_editado'] = email_editado
        
        with st.spinner("Cadastrando Empresa, Contato e Negócio no Bitrix24..."):
            # 1. Cria a Empresa no CRM
            company_id, erro_empresa = criar_empresa_bitrix(dados)
            
            # 2. Cria o Contato no CRM associado à Empresa
            contact_id, erro_contato = criar_contato_bitrix(dados, company_id=company_id)
            
            # 3. Cria o Negócio associado à Empresa e ao Contato
            deal_id, erro_bitrix = criar_negocio_bitrix(
                dados, 
                enviar_apresentacao, 
                company_id=company_id, 
                contact_id=contact_id
            )
            
        if erro_bitrix:
            st.error(f"Erro ao criar registro no Bitrix24: {erro_bitrix}")
        else:
            st.balloons()
            st.success("🎉 **Negócio, Empresa e Contato criados e vinculados com sucesso!**")
            
            url_desktop = f"https://ws4tech.bitrix24.com.br/crm/deal/details/{deal_id}/"
            url_mobile = f"https://ws4tech.bitrix24.com.br/company/personal/user/0/tasks/task/view/0/?PATH_TO_DEAL=https://ws4tech.bitrix24.com.br/crm/deal/details/{deal_id}/"
            
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                st.link_button("💻 Abrir no Computador", url_desktop, use_container_width=True)
            with col_b2:
                st.link_button("📱 Abrir no App Celular", url_mobile, use_container_width=True)
            
            st.info(f"IDs criados no Bitrix24 — Negócio: **{deal_id}** | Empresa: **{company_id}** | Contato: **{contact_id}**")
