# scraping_local_para_json.py
import json
import time
import gspread
import requests
from oauth2client.service_account import ServiceAccountCredentials
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from lxml import html

# Configuração do Google Sheets (ou substitua por lista manual para testar)
def autenticar_planilha():
    escopo = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name("credenciais_google.json", escopo)
    cliente = gspread.authorize(creds)
    return cliente

def set_page_in_url(url, page_number):
    url_parts = list(urlparse(url))
    query = parse_qs(url_parts[4])
    query['page'] = [str(page_number)]
    url_parts[4] = urlencode(query, doseq=True)
    return urlunparse(url_parts)

def extrair_cartas_ligamagic(url, max_paginas=25):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--log-level=3")
    driver = webdriver.Chrome(options=chrome_options)
    cartas = []
    page = 1
    while page <= max_paginas:
        url_pagina = set_page_in_url(url, page)
        driver.get(url_pagina)
        try:
            WebDriverWait(driver, 8).until(
                EC.presence_of_element_located((By.ID, "listacolecao"))
            )
        except:
            break
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        tabela = soup.find("table", {"id": "listacolecao"})
        if not tabela:
            break
        linhas = tabela.find_all("tr")[1:]
        if not linhas:
            break
        for linha in linhas:
            colunas = linha.find_all("td")
            if len(colunas) >= 11:
                div_nome = colunas[3].find("div", attrs={"data-tooltip": True})
                nome_pt = ""
                nome_en = ""
                if div_nome:
                    nomes = div_nome.find_all("a")
                    if len(nomes) >= 2:
                        nome_pt = nomes[0].get_text(strip=True)
                        nome_en = nomes[1].get_text(strip=True)
                    elif len(nomes) == 1:
                        nome_pt = nomes[0].get_text(strip=True)

                if nome_en:
                    nome = f"{nome_pt} / {nome_en}"
                else:
                    nome = nome_pt
                link_carta_tag = colunas[3].find("a")
                carta_url = ""
                if link_carta_tag and link_carta_tag.get("href"):
                    raw_href = link_carta_tag.get("href")
                    if raw_href.startswith("http"):
                        carta_url = raw_href
                    elif raw_href.startswith("/"):
                        carta_url = "https://ligamagic.com.br" + raw_href
                    else:  # Começa com './' ou não tem barra, típico da LigaMagic
                        carta_url = "https://ligamagic.com.br/" + raw_href.lstrip("./")
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
                    "Preço Venda (R$)": preco_venda,
                    "Imagem": carta_url
                })
        page += 1
    driver.quit()
    return cartas


if __name__ == "__main__":
    # --- Config Google Sheets: ---
    cliente = autenticar_planilha()
    planilha = cliente.open_by_url("https://docs.google.com/spreadsheets/d/1FmicnHU9caYH0NrxO1W49OyyJsfu-vYTKd9rzkyzZ7E/edit#gid=0")
    aba = planilha.get_worksheet(0)
    dados = aba.get_all_records()

    jogadores = []
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

    # Salva em JSON para commit no GitHub!
    with open('cartas.json', 'w', encoding='utf-8') as f:
        json.dump(jogadores, f, ensure_ascii=False, indent=2)

    print("Scraping concluído! Arquivo cartas.json salvo.")