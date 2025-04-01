import streamlit as st
import pandas as pd
import json
import io
import matplotlib.pyplot as plt
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload

# --- CONFIGURAÇÕES ---
CAMINHO_CREDENCIAIS = 'credenciais/service_account.json'
FILE_ID = '12kD7T6qg5J-A5dRpTm7wiQZjLqHzzQaP'
ARQUIVO_TEMP = 'temp.json'

# --- AUTENTICAÇÃO COM GOOGLE DRIVE API ---
creds = service_account.Credentials.from_service_account_file(
    CAMINHO_CREDENCIAIS,
    scopes=["https://www.googleapis.com/auth/drive"]
)
drive_service = build('drive', 'v3', credentials=creds)

def carregar_json_drive(file_id):
    request = drive_service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    fh.seek(0)
    return json.load(fh)

def salvar_json_drive(file_id, dados):
    with open(ARQUIVO_TEMP, 'w') as f:
        json.dump(dados, f, indent=2)
    media = MediaFileUpload(ARQUIVO_TEMP, mimetype='application/json')
    drive_service.files().update(fileId=file_id, media_body=media).execute()

# --- INTERFACE STREAMLIT ---
st.title("Editor de Lançamentos Financeiros (JSON no Google Drive)")

try:
    dados_json = carregar_json_drive(FILE_ID)

    meses_disponiveis = sorted(set([item.get("Mês/Ano", "") for item in dados_json if item.get("Mês/Ano")]), reverse=True)
    mes_selecionado = st.selectbox("Filtrar por Mês/Ano", meses_disponiveis)
    dados_filtrados = [item for item in dados_json if item.get("Mês/Ano") == mes_selecionado]

    df = pd.DataFrame(dados_filtrados)

    if not df.empty:
        df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce").fillna(0)

        aba1, aba2, aba3, aba4 = st.tabs([
            "📄 Lançamentos Detalhados",
            "🔹 Tipo de Operação",
            "📊 Categoria Financeira",
            "🏦 Conta Contábil"
        ])

        with aba1:
            st.markdown("### Lançamentos Detalhados")
            st.dataframe(df, use_container_width=True)

        with aba2:
            st.markdown("### Total por Tipo de Operação")
            resumo_tipo = df.groupby("TipoOperacao")["Valor"].sum().sort_values(ascending=False)
            for tipo, total in resumo_tipo.items():
                st.metric(label=f"{tipo}", value=f"R$ {total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

        with aba3:
            st.markdown("### Total por Categoria Financeira (dividido por Tipo de Operação)")
            resumo_cat = (
                df.groupby(["TipoOperacao", "Categoria Financeira"])["Valor"]
                .sum()
                .reset_index()
                .sort_values(by="Valor", ascending=False)
            )
            resumo_cat["Valor"] = resumo_cat["Valor"].apply(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            st.dataframe(resumo_cat, use_container_width=True)

        with aba4:
            st.markdown("### Total por Conta Contábil (dividido por Tipo de Operação)")
            resumo_conta = (
                df.groupby(["TipoOperacao", "Conta Contábil"])["Valor"]
                .sum()
                .reset_index()
                .sort_values(by="Valor", ascending=False)
            )
            resumo_conta["Valor"] = resumo_conta["Valor"].apply(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            st.dataframe(resumo_conta, use_container_width=True)

        # 🔹 MENU DE EDIÇÃO EM POPOVER
        with st.popover("Editar lançamento"):
            id_selecionado = st.selectbox("Escolha o ID do lançamento", df["id"].tolist())
            item = df[df["id"] == id_selecionado].iloc[0]

            tipo_operacao = st.text_input("Tipo de Operação", value=item.get("TipoOperacao", ""))
            categoria = st.text_input("Categoria", value=item.get("Categoria", ""))
            fornecedor = st.text_input("Fornecedor", value=item.get("Fornecedor", ""))
            descricao = st.text_area("Descrição", value=item.get("Descrição", ""))
            categoria_fin = st.text_input("Categoria Financeira", value=item.get("Categoria Financeira", ""))
            conta_contabil = st.text_input("Conta Contábil", value=item.get("Conta Contábil", ""))
            valor = st.number_input("Valor", value=item.get("Valor", 0.0), step=0.01)

            if st.button("Salvar alterações"):
                for original in dados_json:
                    if original["id"] == id_selecionado:
                        original["TipoOperacao"] = tipo_operacao
                        original["Categoria"] = categoria
                        original["Fornecedor"] = fornecedor
                        original["Descrição"] = descricao
                        original["Categoria Financeira"] = categoria_fin
                        original["Conta Contábil"] = conta_contabil
                        original["Valor"] = float(valor)

                salvar_json_drive(FILE_ID, dados_json)
                st.success("Alterações salvas com sucesso no Google Drive!")
    else:
        st.warning("Nenhum dado encontrado para o mês selecionado.")

except Exception as e:
    st.error(f"Erro ao acessar ou editar JSON: {e}")
