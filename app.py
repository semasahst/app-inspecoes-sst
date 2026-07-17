import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from supabase import create_client, Client
from fpdf import FPDF
import base64
import io
from PIL import Image

# Configuração da página
st.set_page_config(page_title="SST Inspeções Pro", page_icon="🛡️", layout="wide")

# --- CONEXÃO COM O SUPABASE ---
# Certifique-se de que SUPABASE_URL e SUPABASE_KEY estão no Streamlit Secrets
url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# Função para carregar dados do Supabase
def carregar_dados():
    try:
        response = supabase.table("inspecoes").select("*").execute()
        df = pd.DataFrame(response.data)
        if df.empty:
            return pd.DataFrame(columns=[
                "id", "local", "categoria", "descricao", "nr", "recomendacao", 
                "prazo", "responsavel", "lat", "lon", "status", "foto_1", "foto_2", "foto_3"
            ])
        return df
    except Exception as e:
        st.error(f"Erro ao conectar ao Supabase: {e}")
        return pd.DataFrame()

df_existente = carregar_dados()

# --- INICIALIZAÇÃO DO ESTADO DA SESSÃO ---
if "carrinho_desvios" not in st.session_state:
    st.session_state.carrinho_desvios = []

# --- BANCO DE DADOS DE NRs ---
DICIONARIO_NRS = {
    "Trabalho em Altura": {"nr": "NR-35 (Trabalho em Altura)", "recomendacao": "Garantir o uso de cinto de segurança tipo paraquedista."},
    "Instalações Elétricas": {"nr": "NR-10 (Segurança em Instalações Elétricas)", "recomendacao": "Sinalizar e bloquear o quadro elétrico."},
    "Máquinas e Equipamentos": {"nr": "NR-12 (Segurança no Trabalho em Máquinas)", "recomendacao": "Instalar proteções físicas."},
    "Equipamentos de Proteção": {"nr": "NR-06 (Equipamentos de Proteção Individual)", "recomendacao": "Fornecer EPI adequado."},
    "Sinalização de Segurança": {"nr": "NR-26 (Sinalização de Segurança)", "recomendacao": "Instalar placas de sinalização."}
}

# --- FUNÇÕES AUXILIARES ---
def processar_e_converter_imagem(uploaded_file):
    if uploaded_file is not None:
        try:
            img = Image.open(uploaded_file)
            if img.mode in ("RGBA", "P"): img = img.convert("RGB")
            img.thumbnail((600, 600))
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=40, optimize=True)
            return base64.b64encode(buffer.getvalue()).decode()
        except: return ""
    return ""

def gerar_pdf_inspecao(dados):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(190, 10, "RELATÓRIO DE INSPEÇÃO DE SST", ln=True, align="C")
    pdf.cell(190, 10, f"ID: {dados.get('id')}", ln=True)
    pdf.cell(190, 10, f"Local: {dados.get('local')}", ln=True)
    return pdf.output(dest='S').encode('latin-1')

# --- NAVEGAÇÃO ---
menu = st.sidebar.selectbox("Navegação", ["Nova Inspeção", "Painel de Gestão (Plano de Ação)"])

if menu == "Nova Inspeção":
    st.header("📝 Registrar Inspeção em Lote")
    local_global = st.text_input("Local Geral:")
    col1, col2 = st.columns(2)
    with col1:
        categoria = st.selectbox("Categoria:", list(DICIONARIO_NRS.keys()))
        descricao = st.text_area("Descrição:")
    with col2:
        responsavel = st.text_input("Responsável:")
        foto1 = st.file_uploader("Foto 1:", type=["png", "jpg"], key="f1")
    
    if st.button("➕ Adicionar Desvio"):
        st.session_state.carrinho_desvios.append({
            "local": local_global, "categoria": categoria, "descricao": descricao,
            "responsavel": responsavel, "status": "Pendente", "foto_1": processar_e_converter_imagem(foto1)
        })
        st.toast("Adicionado!")

 iif st.session_state.carrinho_desvios:
for item in st.session_state.carrinho_desvios:
    # Removemos o ID antes de enviar, permitindo que o Supabase (Identity) gere o valor
    if "id" in item:
        del item["id"]
    
    # ... resto do seu código de envio ...
    supabase.table("inspecoes").insert(item_filtrado).execute()       
        st.markdown("---")
        st.subheader(f"📋 Desvios aguardando envio ({len(st.session_state.carrinho_desvios)})")
        
        df_carrinho = pd.DataFrame(st.session_state.carrinho_desvios)
        st.dataframe(df_carrinho, use_container_width=True)
        
        col_btn1, col_btn2 = st.columns([1, 5])
        
        with col_btn1:
            if st.button("🔥 Limpar Fila"):
                st.session_state.carrinho_desvios = []
                st.rerun()
                
        with col_btn2:
            if st.button("🚀 ENVIAR TODOS OS DESVIOS PARA O SUPABASE"):
                try:
                    for item in st.session_state.carrinho_desvios:
                        # 1. Removemos o ID se estiver vazio para o Supabase gerar o dele
                        if "id" in item and (item["id"] is None or item["id"] == ""):
                            del item["id"]
                        
                        # 2. Garantimos que apenas colunas existentes no banco sejam enviadas
                        colunas_banco = [
                            "local", "categoria", "descricao", "nr", "recomendacao", 
                            "prazo", "responsavel", "lat", "lon", "status", "foto_1", "foto_2", "foto_3"
                        ]
                        item_filtrado = {k: v for k, v in item.items() if k in colunas_banco}
                        
                        # 3. Inserção
                        supabase.table("inspecoes").insert(item_filtrado).execute()
                    
                    st.success("✅ Enviado com sucesso!")
                    st.session_state.carrinho_desvios = []
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro detalhado do Supabase: {e}")
elif menu == "Painel de Gestão (Plano de Ação)":
    st.header("📊 Painel")
    st.dataframe(df_existente)
    
    if not df_existente.empty:
        id_selec = st.selectbox("ID para atualizar:", df_existente["id"].unique())
        novo_status = st.selectbox("Novo Status:", ["Pendente", "Concluído"])
        if st.button("Atualizar Status"):
            supabase.table("inspecoes").update({"status": novo_status}).eq("id", id_selec).execute()
            st.rerun()
