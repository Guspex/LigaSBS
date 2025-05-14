import streamlit as st
import pandas as pd
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials



# ======================== CONFIGURAÇÕES =============================

# Autenticação com Google Sheets
def autenticar_planilha():
    escopo = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    info = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(info, escopo)
    cliente = gspread.authorize(creds)
    return cliente

# ======================== SELENIUM + SCRAPING =======================

def set_page_in_url(url, page_number):
    url_parts = list(urlparse(url))
    query = parse_qs(url_parts[4])
    query['page'] = [str(page_number)]
    url_parts[4] = urlencode(query, doseq=True)
    return urlunparse(url_parts)

def extrair_cartas_ligamagic(nome_jogador, tipo='have'):
    """
    Busca as cartas do arquivo cartas.json por nome de jogador e tipo ('have' ou 'want').

    Parâmetros:
      nome_jogador (str): Nome do jogador conforme está em cartas.json.
      tipo (str): 'have' ou 'want'.

    Retorna:
      Lista de cartas do respectivo jogador/tipo.
    """
    with open("cartas.json", encoding="utf-8") as f:
        jogadores = json.load(f)

    for jogador in jogadores:
        if jogador["nome"].strip().lower() == nome_jogador.strip().lower():
            return jogador.get(tipo, [])
    return []

# ======================== APP STREAMLIT =============================

st.set_page_config(page_title="Troca de Cartas Magic", layout="wide")
st.title("💬 Plataforma de Troca e Venda de Cartas - Magic: The Gathering")

# Carrega dados da planilha
with st.status("🔄 Carregando dados da planilha...", expanded=True) as status:
    cliente = autenticar_planilha()
    planilha = cliente.open_by_url("https://docs.google.com/spreadsheets/d/1FmicnHU9caYH0NrxO1W49OyyJsfu-vYTKd9rzkyzZ7E/edit#gid=0")
    aba = planilha.get_worksheet(0)
    dados = aba.get_all_records()
    status.update(label="✅ Dados carregados com sucesso!", state="complete")

# =========== CAMPO DE BUSCA POR CARTA =============
st.header("🔎 Buscar carta por nome")

busca = st.text_input("Digite o nome (ou parte) da carta", "")

# Estruturas auxiliares
jogadores = []

# Coleta dados de cada jogador
for linha in dados:
    nome = linha.get("Jogador")
    whatsapp = linha.get("Whatsapp (opcional)", "")
    link_have = linha.get("Link do Have", "").strip()
    link_want = linha.get("Link do Want", "").strip()

    lista_have = extrair_cartas_ligamagic(nome, tipo='have')
    lista_want = extrair_cartas_ligamagic(nome, tipo='want')

    jogadores.append({
        "nome": nome,
        "whatsapp": whatsapp,
        "have": lista_have,
        "want": lista_want
    })

# Mostra dados por jogador
for jogador in jogadores:
    st.subheader(f"🧙 {jogador['nome']}")
    if jogador['whatsapp']:
        st.write(f"📱 WhatsApp: `{jogador['whatsapp']}`")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Cartas disponíveis (Have):**")
        if jogador["have"]:
            st.dataframe(pd.DataFrame(jogador["have"]))
        else:
            st.info("Nenhuma carta cadastrada.")

    with col2:
        st.markdown("**Cartas desejadas (Want):**")
        if jogador["want"]:
            st.dataframe(pd.DataFrame(jogador["want"]))
        else:
            st.info("Nenhuma carta desejada cadastrada.")

    # Comparações com outros jogadores
    st.markdown("🟨 **Comparativo com outros jogadores:**")
    comparacoes = []

    for outro in jogadores:
        if outro["nome"] == jogador["nome"]:
            continue

        # Cartas que este jogador TEM e outro QUER
        nomes_have = {c["Nome"] for c in jogador["have"] if "Nome" in c}
        nomes_want_outro = {c["Nome"] for c in outro["want"] if "Nome" in c}
        em_demand = nomes_have & nomes_want_outro

        # Cartas que este jogador QUER e outro TEM
        nomes_want = {c["Nome"] for c in jogador["want"] if "Nome" in c}
        nomes_have_outro = {c["Nome"] for c in outro["have"] if "Nome" in c}
        pode_trocar = nomes_want & nomes_have_outro

        if em_demand or pode_trocar:
            texto = f"📌 Com **{outro['nome']}**:"
            if em_demand:
                texto += f"\n- {len(em_demand)} carta(s) que ele quer e você tem: `{', '.join(em_demand)}`"
            if pode_trocar:
                texto += f"\n- {len(pode_trocar)} carta(s) que você quer e ele tem: `{', '.join(pode_trocar)}`"
            st.markdown(texto)
            

if busca.strip():
    busca_normalizada = busca.strip().lower()
    resultado = []
    for jogador in jogadores:
        for carta in jogador.get("have", []):
            if busca_normalizada in carta.get("Nome", "").lower():
                resultado.append({
                    "Jogador": jogador["nome"],
                    "WhatsApp": jogador["whatsapp"],
                    "Carta": carta["Nome"],
                    "Qtd": carta.get("Quantidade", "")
                })
    if resultado:
        st.success(f"Encontrado(s) {len(resultado)} resultado(s):")
        st.dataframe(pd.DataFrame(resultado))
    else:
        st.warning("Nenhum jogador possui carta com esse nome.")

    st.markdown("---")