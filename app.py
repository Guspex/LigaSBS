import streamlit as st
import pandas as pd
import requests
import json
from bs4 import BeautifulSoup
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

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

def extrair_cartas_ligamagic(url):
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.binary_location = "/usr/bin/chromium"
    
        driver = webdriver.Chrome(options=chrome_options)
        cartas = []
        page = 1

        while page <= max_paginas:
            url_pagina = set_page_in_url(url, page)
            driver.get(url_pagina)
            time.sleep(2)  # Ajuste se necessário
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            tabela = soup.find("table", {"id": "listacolecao"})
            if not tabela:
                print(f"Nenhuma tabela encontrada na página {page} (provavelmente acabou a coleção).")
                break
            linhas = tabela.find_all("tr")[1:]
            if not linhas:
                print(f"Sem cartas na página {page}. Interrompendo busca.")
                break
    
            for linha in linhas:
                colunas = linha.find_all("td")
                if len(colunas) >= 11:
                    nome = colunas[3].get_text(strip=True)
                    extra = colunas[4].get_text(strip=True)
                    idioma = colunas[5].get_text(strip=True)
                    qualidade = colunas[6].get_text(strip=True)
                    quantidade = colunas[0].get_text(strip=True)
                    preco_venda = colunas[9].get_text(strip=True).replace("R$", "").strip()
                    cartas.append({
                        "Nome": nome,
                        "Qualidade": qualidade,
                        "Extra": extra,
                        "Idioma": idioma,
                        "Quantidade": quantidade,
                        "Preço Venda (R$)": preco_venda
                    })
            page += 1
    driver.quit()
    return cartas

    except Exception as e:
        return [{"Erro": f"Erro ao acessar {url}: {e}"}]

# ======================== APP STREAMLIT =============================

st.set_page_config(page_title="Troca de Cartas Magic", layout="wide")
st.title("💬 Plataforma de Troca e Venda de Cartas - Magic: The Gathering")

# Carrega dados da planilha
st.info("🔄 Carregando dados da planilha...")
cliente = autenticar_planilha()
planilha = cliente.open_by_url("https://docs.google.com/spreadsheets/d/1FmicnHU9caYH0NrxO1W49OyyJsfu-vYTKd9rzkyzZ7E/edit#gid=0")
aba = planilha.get_worksheet(0)
dados = aba.get_all_records()

# Estruturas auxiliares
jogadores = []

# Coleta dados de cada jogador
for linha in dados:
    nome = linha.get("Jogador")
    whatsapp = linha.get("Whatsapp (opcional)", "")
    link_have = linha.get("Link do Have", "").strip()
    link_want = linha.get("Link do Want", "").strip()

    lista_have = extrair_cartas_ligamagic(link_have) if link_have else []
    lista_want = extrair_cartas_ligamagic(link_want) if link_want else []

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

    st.markdown("---")
