import streamlit as st
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import tempfile
import os

# ========================
# 🔐 Autenticação Google
# ========================
def autenticar_google(scopes):
    info = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
    creds = Credentials.from_service_account_info(info, scopes=scopes)
    return creds


# ========================
# 📄 Autenticar Google Sheets
# ========================
def autenticar_planilha():
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    creds = autenticar_google(scopes)
    cliente = gspread.authorize(creds)
    return cliente


# ========================
# ☁️ Upload CSV para Google Drive
# ========================
def upload_csv_para_drive(nome_arquivo, caminho_arquivo, pasta_id=None):
    creds = autenticar_google(['https://www.googleapis.com/auth/drive'])
    service = build('drive', 'v3', credentials=creds)

    file_metadata = {'name': nome_arquivo}
    if pasta_id:
        file_metadata['parents'] = [pasta_id]

    media = MediaFileUpload(caminho_arquivo, mimetype='text/csv')

    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id'
    ).execute()

    return file.get('id')


# ========================
# 📥 Upload e salvar CSV no Drive
# ========================
def processar_upload_csv(tipo_lista):
    uploaded_file = st.file_uploader(f"📤 Upload CSV da lista {tipo_lista}", type=["csv"])
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
            tmp.write(uploaded_file.getvalue())
            tmp_path = tmp.name

        file_id = upload_csv_para_drive(f"{tipo_lista}.csv", tmp_path)
        os.remove(tmp_path)

        st.success(f"Arquivo {tipo_lista}.csv enviado ao Google Drive com ID: {file_id}")

        return df
    return None


# ========================
# 🔗 Ler dados do Google Sheets
# ========================
def ler_dados_planilha(sheet_url, aba):
    cliente = autenticar_planilha()
    planilha = cliente.open_by_url(sheet_url)
    aba_dados = planilha.worksheet(aba)
    dados = aba_dados.get_all_records()
    df = pd.DataFrame(dados)
    return df


# ========================
# 🔀 Combinar dados
# ========================
def combinar_dados(df_planilha, df_csv, nome_fonte):
    df_csv["Fonte"] = nome_fonte
    if df_planilha is not None:
        df_planilha["Fonte"] = "Planilha"
        df_total = pd.concat([df_planilha, df_csv], ignore_index=True)
    else:
        df_total = df_csv
    return df_total


# ========================
# 🔍 Comparar listas HAVE x WANT
# ========================
def comparar_listas(df_have, df_want):
    resultado = pd.merge(df_have, df_want, on="Card", how="inner", suffixes=('_Have', '_Want'))
    return resultado


# ========================
# 🚀 App Streamlit
# ========================
st.set_page_config(page_title="Magic Card Manager", layout="wide")
st.title("🧙‍♂️ Magic Card Manager - Listas e Comparação")

st.subheader("1️⃣ Upload das listas locais (CSV)")
df_have_csv = processar_upload_csv("HAVE")
df_want_csv = processar_upload_csv("WANT")

st.subheader("2️⃣ Dados da Planilha Google")
url_planilha = st.text_input("🔗 URL da sua planilha do Google Sheets", key="planilha_url")
df_planilha_have = None
df_planilha_want = None

if url_planilha:
    try:
        df_planilha_have = ler_dados_planilha(url_planilha, "Have")
        df_planilha_want = ler_dados_planilha(url_planilha, "Want")
        st.success("✅ Dados da planilha carregados com sucesso!")
    except Exception as e:
        st.error(f"Erro ao carregar planilha: {e}")

st.subheader("3️⃣ Listas Combinadas")

if df_have_csv is not None and df_want_csv is not None:
    df_have_total = combinar_dados(df_planilha_have, df_have_csv, "CSV")
    df_want_total = combinar_dados(df_planilha_want, df_want_csv, "CSV")

    st.write("🃏 Lista HAVE")
    st.dataframe(df_have_total)

    st.write("🎯 Lista WANT")
    st.dataframe(df_want_total)

    st.subheader("4️⃣ 🔍 Comparação HAVE x WANT")
    df_comparacao = comparar_listas(df_have_total, df_want_total)

    st.dataframe(df_comparacao)

else:
    st.warning("🚨 Faça upload dos CSVs HAVE e WANT para continuar.")


st.subheader("5️⃣ 💾 (Opcional) Salvar listas combinadas em JSON")

if st.button("💾 Salvar listas em JSON local"):
    df_have_total.to_json("have_total.json", orient="records", indent=4)
    df_want_total.to_json("want_total.json", orient="records", indent=4)
    st.success("✅ JSONs salvos na pasta do app (have_total.json e want_total.json)")
