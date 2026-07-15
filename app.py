import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import gspread
from google.oauth2.service_account import Credentials

# Configuração da página
st.set_page_config(page_title="SST Inspeções Pro", page_icon="🛡️", layout="wide")

# --- CONEXÃO COM O GOOGLE SHEETS VIA GSPREAD ---
def conectar_google_sheets():
    # Define os escopos necessários
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    # Busca as credenciais salvas nos Secrets do Streamlit
    creds_dict = dict(st.secrets["gcp_service_account"])
    credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(credentials)
    
    # Abre a planilha pelo ID (pode copiar da URL da sua planilha)
    # Exemplo de URL: https://docs.google.com/spreadsheets/d/ID_DA_PLANILHA/edit
    ID_PLANILHA = st.secrets["spreadsheet_id"]
    sheet = client.open_by_key(ID_PLANILHA).sheet1
    return sheet

try:
    sheet = conectar_google_sheets()
except Exception as e:
    st.error(f"Erro ao conectar ao Google Sheets: {e}")
    st.stop()

# --- BANCO DE DADOS DE NRs ---
DICIONARIO_NRS = {
    "Trabalho em Altura": {
        "nr": "NR-35 (Trabalho em Altura)",
        "recomendacao": "Garantir o uso de cinto de segurança tipo paraquedista conectado a cabo de segurança/linha de vida inspecionada."
    },
    "Instalações Elétricas": {
        "nr": "NR-10 (Segurança em Instalações Elétricas)",
        "recomendacao": "Sinalizar e bloquear o quadro elétrico de forma a impedir energização acidental (Lockout/Tagout)."
    },
    "Máquinas e Equipamentos": {
        "nr": "NR-12 (Segurança no Trabalho em Máquinas)",
        "recomendacao": "Instalar ou adequar as proteções físicas fixas ou móveis intertravadas na zona de perigo da máquina."
    },
    "Equipamentos de Proteção": {
        "nr": "NR-06 (Equipamentos de Proteção Individual)",
        "recomendacao": "Fornecer imediatamente o EPI adequado ao risco, registrar a entrega na ficha de EPI e treinar o colaborador."
    },
    "Sinalização de Segurança": {
        "nr": "NR-26 (Sinalização de Segurança)",
        "recomendacao": "Instalar placas de sinalização de advertência, rotas de fuga e saídas de emergência desobstruídas."
    }
}

# --- TÍTULO DO APP ---
st.title("🛡️ Sistema de Inspeção de Segurança do Trabalho")

menu = st.sidebar.selectbox("Navegação", ["Nova Inspeção", "Painel de Gestão (Plano de Ação)"])

# ------------------------------------------------------------------
# TELA 1: NOVA INSPEÇÃO (GRAVA NO GOOGLE SHEETS)
# ------------------------------------------------------------------
if menu == "Nova Inspeção":
    st.header("📝 Registrar Não Conformidade")
    
    with st.form("form_inspeção", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            local = st.text_input("Local / Setor da Inspeção:", placeholder="Ex: Galpão de Solda, Almoxarifado")
            categoria = st.selectbox("Categoria do Desvio:", list(DICIONARIO_NRS.keys()))
            
            st.markdown("**Geolocalização Aproximada:**")
            lat = st.number_input("Latitude", value=-23.55052, format="%.5f")
            lon = st.number_input("Longitude", value=-46.63330, format="%.5f")
            
        with col2:
            descricao = st.text_area("Descrição Detalhada do Desvio:", placeholder="Descreva o que está errado...")
            # Como imagens pesadas não cabem bem no Sheets diretamente, podemos guardar um link de imagem futuramente.
            # Por enquanto, focamos nos dados do relatório.

        st.markdown("---")
        st.subheader("📋 Enquadramento Legal Sugerido")
        
        nr_sugerida = DICIONARIO_NRS[categoria]["nr"]
        reco_sugerida = DICIONARIO_NRS[categoria]["recomendacao"]
        
        st.info(f"**Dispositivo Legal aplicável:** {nr_sugerida}")
        reco_usuario = st.text_area("Recomendação/Plano de Ação Proposto:", value=reco_sugerida)
        
        prazo = st.date_input("Prazo para Regularização:")
        responsavel = st.text_input("Responsável pela Ação:")

        salvar = st.form_submit_button("Gravar Inspeção")
        
        if salvar:
            if not local or not descricao:
                st.error("Por favor, preencha o Local e a Descrição!")
            else:
                # Obter todos os registros existentes para gerar o novo ID
                todos_registros = sheet.get_all_records()
                novo_id = len(todos_registros) + 1
                
                # Prepara a linha para o Google Sheets
                nova_linha = [
                    novo_id,
                    local,
                    categoria,
                    descricao,
                    nr_sugerida,
                    reco_usuario,
                    prazo.strftime('%d/%m/%Y'),
                    responsavel if responsavel else "Não Definido",
                    lat,
                    lon,
                    "Pendente"
                ]
                
                # Grava no Google Sheets
                sheet.append_row(nova_linha)
                st.success("✅ Inspeção registada com sucesso na Planilha Google!")

# ------------------------------------------------------------------
# TELA 2: PAINEL DE GESTÃO (LÊ E ATUALIZA O GOOGLE SHEETS)
# ------------------------------------------------------------------
elif menu == "Painel de Gestão (Plano de Ação)":
    st.header("📊 Painel de Controle e Plano de Ação")
    
    # Lê os dados em tempo real da Planilha Google
    dados_planilha = sheet.get_all_records()
    
    if not dados_planilha:
        st.info("Nenhuma não conformidade registada até o momento.")
    else:
        df = pd.DataFrame(dados_planilha)
        
        # Filtros rápidos
        status_filtro = st.multiselect("Filtrar por Status:", ["Pendente", "Em Andamento", "Concluído"], default=["Pendente", "Em Andamento", "Concluído"])
        df_filtrado = df[df["status"].isin(status_filtro)]
        
        st.dataframe(
            df_filtrado[["id", "local", "categoria", "nr", "prazo", "responsavel", "status"]],
            use_container_width=True,
            hide_index=True
        )
        
        # Mapa de Ocorrências
        st.markdown("---")
        st.subheader("🗺️ Mapa de Riscos / Ocorrências")
        try:
            mapa = folium.Map(location=[float(df_filtrado["lat"].mean()), float(df_filtrado["lon"].mean())], zoom_start=12)
            for idx, row in df_filtrado.iterrows():
                folium.Marker(
                    [float(row["lat"]), float(row["lon"])],
                    popup=f"<b>Local:</b> {row['local']}<br><b>Status:</b> {row['status']}",
                    tooltip=f"{row['local']}"
                ).add_to(mapa)
            st_folium(mapa, width=1000, height=400)
        except Exception:
            st.warning("Não foi possível carregar as coordenadas para o mapa.")

        # Atualizar status de um item
        st.markdown("---")
        st.subheader("🔍 Atualizar Ocorrência")
        id_selecionado = st.selectbox("Escolha o ID para atualizar o status:", df_filtrado["id"])
        
        if id_selecionado:
            # Encontra a linha correspondente no Sheets (lembrando que a linha 1 é o cabeçalho)
            index_linha = df[df["id"] == id_selecionado].index[0] + 2 # +2 compensa o índice 0 e o cabeçalho
            detalhe = df[df["id"] == id_selecionado].iloc[0]
            
            novo_status = st.selectbox(
                f"Novo status para o ID {id_selecionado}:", 
                ["Pendente", "Em Andamento", "Concluído"],
                index=["Pendente", "Em Andamento", "Concluído"].index(detalhe["status"])
            )
            
            if st.button("Atualizar na Planilha"):
                # A coluna "status" é a 11ª coluna (id, local, categoria, descricao, nr, recomendacao, prazo, responsavel, lat, lon, status)
                sheet.update_cell(index_linha, 11, novo_status)
                st.success("Status atualizado no Google Sheets!")
                st.rerun()
