import streamlit as st
import pandas as pd
import json
import gspread
import re
import time
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
placeholder = st.empty()
placeholder.info("🔄 Carregando dados da planilha...")

cliente = autenticar_planilha()
planilha = cliente.open_by_url("https://docs.google.com/spreadsheets/d/1FmicnHU9caYH0NrxO1W49OyyJsfu-vYTKd9rzkyzZ7E/edit#gid=0")
aba = planilha.get_worksheet(0)
dados = aba.get_all_records()

placeholder.success("✅ Dados carregados com sucesso!")
time.sleep(3)
placeholder.empty()  # Remove a mensagem do placeholder

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

def carta_com_link_e_imagem(nome, url, img_url):
    if not url:
        return nome  # se não houver link, só o nome
    return (
        f'<a href="{url}" target="_blank" '
        f'style="text-decoration:none; color:#1967d2;">'
        f'{nome}'
        f'</a>'
        f'&nbsp;<img src="{img_url}" style="height:42px; margin-bottom:-10px; box-shadow:1px 1px 7px #aaa; vertical-align:middle;">'
        if img_url else
        f'<a href="{url}" target="_blank" style="text-decoration:none; color:#1967d2;">{nome}</a>'
    )
colunas_desejadas_have = ["Nome", "Quantidade", "Qualidade", "Extra", "Idioma", "Preço Venda (R$)"]
colunas_desejadas_want = ["Nome", "Quantidade", "Qualidade", "Extra", "Idioma"]
def tabela_html_cartas(cartas, altura_px=350, colunas_desejadas=None):
    if not cartas:
        return "<i>Nenhuma carta cadastrada.</i>"
    # Se não for especificado, usa todas as colunas inclusive preço
    if colunas_desejadas is None:
        colunas_desejadas = ["Nome", "Quantidade", "Qualidade", "Extra", "Idioma", "Preço Venda (R$)"]
    colunas = [c for c in colunas_desejadas if c in cartas[0]]
    html = f"""
    <div style="border-radius:15px;border:1.5px solid #e6e6ef;box-shadow:0 2px 10px #0001;background:#fff;margin-bottom:14px;margin-top:2px;padding:0px;overflow: hidden;box-sizing: border-box;max-width: 100%;">
        <div style="max-height:{altura_px+55}px;overflow-y:hidden;overflow-x:auto;border-radius:15px;padding-bottom: 6px;box-sizing: border-box;">
        <table style='border-collapse:collapse;width:100%;font-family:"Segoe UI",Roboto,Arial,sans-serif;font-size:12px;background:#f7f8fa;table-layout:fixed;'>
            <thead>
            <tr>
    """
    for c in colunas:
        if c == "Nome":
            width = "min-width:340px;max-width:400px;width:33%;"
        elif c == "Preço Venda (R$)":
            width = "width:90px;max-width:120px;"
        else:
            width = "width:66px;max-width:88px;"
        html += f'<th style="border-bottom:2px solid #e6e6ef;color:#2e4a66;background:#f0f2fa;padding:6px 5px;text-align:left;font-weight:600;position:sticky;top:0;z-index:2;{width}">{c}</th>'
    html += "</tr></thead></table>"
    html += f"""<div style="max-height:{altura_px}px;overflow-y:auto;overflow-x:hidden;"><table style='border-collapse:collapse;width:100%;font-family:"Segoe UI",Roboto,Arial,sans-serif;font-size:12px;table-layout:fixed;'><tbody>"""
    for carta in cartas:
        html += "<tr style='background:#fff;'>"
        for c in colunas:
            if c == "Nome":
                link = carta.get("Link Detalhe") or carta.get("Imagem") or "#"
                cell = f'<a href="{link}" target="_blank" style="color:#1976d2;text-decoration:none;font-weight:600;min-width:180px;display:inline-block;line-height:1.3;word-break:break-word;">{carta.get("Nome","")}</a>'
                tdstyle = 'padding:6px 5px;border-bottom:1px solid #e6e6ef;color:#222;vertical-align:middle;word-break:break-word;min-width:180px;max-width:400px;width:33%;'
            elif c == "Preço Venda (R$)":
                cell = carta.get(c, "-")
                tdstyle = 'padding:6px 5px;border-bottom:1px solid #e6e6ef;color:#222;text-align:right;width:90px;max-width:120px;'
            else:
                cell = carta.get(c, "-")
                tdstyle = 'padding:6px 5px;border-bottom:1px solid #e6e6ef;color:#222;width:66px;max-width:88px;text-align:center;'
            html += f'<td style="{tdstyle}">{cell}</td>'
        html += "</tr>"
    html += "</tbody></table></div>"
    return html

# ========== RESULTADO DA BUSCA, LOGO ABAIXO DO CAMPO ==========
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
        for item in resultado:
            st.markdown(
                carta_com_link_e_imagem(
                    item["Carta"],
                    item.get("Link Detalhe") or item.get("Imagem") or "#",  # preferencialmente Link Detalhe, depois Imagem
                    item.get("Imagem", "")
                ),
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<b>Jogador:</b> {item["Jogador"]}<br>'
                f'<b>Whatsapp:</b> {item["WhatsApp"]}<br>'
                f'<b>Qtd:</b> {item["Qtd"]}<hr>',
                unsafe_allow_html=True
            )
    else:
        st.warning("Nenhum jogador possui carta com esse nome.")

# Mostra dados por jogador
for jogador in jogadores:
    st.subheader(f"🧙 {jogador['nome']}")
    if jogador['whatsapp']:
        numero = re.sub(r'\D', '', jogador['whatsapp'])
        if not numero.startswith('55'):
            numero = f'55{numero}'
        link_whatsapp = f"https://wa.me/{numero}"
        st.write(f"📱 WhatsApp: [{jogador['whatsapp']}]({link_whatsapp})")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Cartas disponíveis (Have):**")
        if jogador["have"]:
            html = tabela_html_cartas(jogador["have"], colunas_desejadas=colunas_desejadas_have)
            st.markdown(html, unsafe_allow_html=True)
        else:
            st.info("Nenhuma carta cadastrada.")

    with col2:
        st.markdown("**Cartas desejadas (Want):**")
        if jogador["want"]:
            html = tabela_html_cartas(jogador["want"], colunas_desejadas=colunas_desejadas_want)
            st.markdown(html, unsafe_allow_html=True)
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
st.markdown(
    """
    <style>
    .footer {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: #f0f2f6;
        color: #999999;
        text-align: center;
        padding: 10px 0;
        font-size: 14px;
        border-top: 1px solid #e6e6ef;
        z-index: 1000;
    }
    </style>
    <div class="footer">
        &copy; 2025 Projeto de código aberto, disponível sob a licença MIT. Desenvolvido por André Dienes Friedrich. WhatsApp: <a href="https://wa.me/5547996280770" style="color:#999999;text-decoration:none;">+55 47 99628-0770</a><br>
    </div>
    """,
    unsafe_allow_html=True
)