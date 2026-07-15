import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from streamlit_gsheets import GSheetsConnection
from fpdf import FPDF
import base64
import io

# Configuração da página
st.set_page_config(page_title="SST Inspeções Pro", page_icon="🛡️", layout="wide")

# --- CONEXÃO NATIVA COM O GOOGLE SHEETS ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_existente = conn.read(ttl=0)
    # Garante que todas as colunas venham como strings/tipos corretos para evitar desalinhamento
    df_existente = pd.DataFrame(df_existente)
except Exception as e:
    st.error(f"Erro ao conectar ao Google Sheets: {e}")
    st.stop()

# --- INICIALIZAÇÃO DO ESTADO DA SESSÃO ---
if "carrinho_desvios" not in st.session_state:
    st.session_state.carrinho_desvios = []

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

# --- FUNÇÃO PARA CONVERTER IMAGEM PARA BASE64 ---
def converter_imagem_para_base64(uploaded_file):
    if uploaded_file is not None:
        bytes_data = uploaded_file.getvalue()
        return base64.b64encode(bytes_data).decode()
    return ""

# --- FUNÇÃO PARA GERAR RELATÓRIO PDF ---
def gerar_pdf_inspecao(dados):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    pdf.set_fill_color(31, 78, 121)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(190, 15, "RELATÓRIO DE INSPEÇÃO DE SEGURANÇA DO TRABALHO", ln=True, align="C", fill=True)
    pdf.ln(10)
    
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", style="B", size=12)
    pdf.cell(190, 8, f"ID do Registro: #{dados['id']}", ln=True)
    pdf.set_font("Arial", size=11)
    
    pdf.cell(95, 8, f"Setor/Local: {dados['local']}", border=1)
    pdf.cell(95, 8, f"Data Limite: {dados['prazo']}", border=1, ln=True)
    pdf.cell(95, 8, f"Responsável: {dados['responsavel']}", border=1)
    pdf.cell(95, 8, f"Status Atual: {dados['status']}", border=1, ln=True)
    pdf.ln(5)
    
    pdf.set_font("Arial", style="B", size=12)
    pdf.set_fill_color(220, 220, 220)
    pdf.cell(190, 8, "Descrição da Não Conformidade", ln=True, fill=True)
    pdf.set_font("Arial", size=11)
    pdf.multi_cell(190, 8, str(dados['descricao']), border=1)
    pdf.ln(5)
    
    pdf.set_font("Arial", style="B", size=12)
    pdf.set_fill_color(220, 220, 220)
    pdf.cell(190, 8, "Fundamentação Legal e Recomendações", ln=True, fill=True)
    pdf.set_font("Arial", size=11)
    pdf.cell(190, 8, f"Enquadramento: {dados['nr']}", border=1, ln=True)
    pdf.multi_cell(190, 8, f"Recomendação:\n{dados['recomendacao']}", border=1)
    pdf.ln(10)
    
    fotos_adicionadas = False
    for i in range(1, 4):
        chave_foto = f'foto_{i}'
        if chave_foto in dados and dados[chave_foto] and str(dados[chave_foto]).strip() != "":
            if not fotos_adicionadas:
                pdf.set_font("Arial", style="B", size=12)
                pdf.cell(190, 8, "Evidências Fotográficas", ln=True, align="L")
                pdf.ln(2)
                fotos_adicionadas = True
            try:
                img_data = base64.b64decode(dados[chave_foto])
                img_io = io.BytesIO(img_data)
                pdf.image(img_io, w=60, h=45)
                pdf.ln(5)
            except:
                pass

    pdf.ln(10)
    pdf.set_font("Arial", size=9)
    pdf.cell(95, 10, "_________________________________________", align="C")
    pdf.cell(95, 10, "_________________________________________", ln=True, align="C")
    pdf.cell(95, 5, "Assinatura do Inspetor de SST", align="C")
    pdf.cell(95, 5, "Assinatura do Responsável", ln=True, align="C")
    
    return pdf.output()

# --- NAVEGAÇÃO ---
menu = st.sidebar.selectbox("Navegação", ["Nova Inspeção", "Painel de Gestão (Plano de Ação)"])

# ------------------------------------------------------------------
# TELA 1: NOVA INSPEÇÃO
# ------------------------------------------------------------------
if menu == "Nova Inspeção":
    st.header("📝 Registrar Inspeção em Lote")
    
    st.subheader("📍 Dados Globais do Local")
    col_loc1, col_loc2 = st.columns(2)
    with col_loc1:
        local_global = st.text_input("Local / Setor Geral da Inspeção:", placeholder="Ex: Galpão Central, Almoxarifado")
    with col_loc2:
        col_lat, col_lon = st.columns(2)
        with col_lat:
            lat_global = st.number_input("Latitude", value=-23.55052, format="%.5f")
        with col_lon:
            lon_global = st.number_input("Longitude", value=-46.63330, format="%.5f")
            
    st.markdown("---")
    st.subheader("⚠️ Adicionar Não Conformidade ao Local")
    
    col1, col2 = st.columns(2)
    with col1:
        categoria = st.selectbox("Categoria do Desvio:", list(DICIONARIO_NRS.keys()))
        descricao = st.text_area("Descrição do Desvio:", placeholder="Descreva o problema encontrado...")
        
        nr_sugerida = DICIONARIO_NRS[categoria]["nr"]
        st.info(f"**Dispositivo Sugerido:** {nr_sugerida}")
        reco_usuario = st.text_area("Plano de Ação Sugerido:", value=DICIONARIO_NRS[categoria]["recomendacao"])
        
    with col2:
        prazo = st.date_input("Prazo limite:")
        responsavel = st.text_input("Responsável pela correção:")
        
        st.markdown("**📸 Evidências Fotográficas (Até 3 fotos):**")
        foto1 = st.file_uploader("Foto 1:", type=["png", "jpg", "jpeg"], key="f1")
        foto2 = st.file_uploader("Foto 2 (Opcional):", type=["png", "jpg", "jpeg"], key="f2")
        foto3 = st.file_uploader("Foto 3 (Opcional):", type=["png", "jpg", "jpeg"], key="f3")

    if st.button("➕ Adicionar Desvio à Lista"):
        if not local_global:
            st.error("Preencha o Local Geral antes de adicionar um desvio!")
        elif not descricao:
            st.error("Preencha a descrição do desvio!")
        else:
            f1_str = converter_imagem_para_base64(foto1)
            f2_str = converter_imagem_para_base64(foto2)
            f3_str = converter_imagem_para_base64(foto3)
            
            st.session_state.carrinho_desvios.append({
                "local": local_global,
                "categoria": categoria,
                "descricao": descricao,
                "nr": nr_sugerida,
                "recomendacao": reco_usuario,
                "prazo": prazo.strftime('%d/%m/%Y'),
                "responsavel": responsavel if responsavel else "Não Definido",
                "lat": lat_global,
                "lon": lon_global,
                "status": "Pendente",
                "foto_1": f1_str,
                "foto_2": f2_str,
                "foto_3": f3_str
            })
            st.toast("Desvio adicionado à fila!")

    if st.session_state.carrinho_desvios:
        st.markdown("---")
        st.subheader(f"📋 Desvios aguardando envio ({len(st.session_state.carrinho_desvios)})")
        
        df_carrinho = pd.DataFrame(st.session_state.carrinho_desvios)
        st.dataframe(df_carrinho[["categoria", "descricao", "nr", "responsavel"]], use_container_width=True)
        
        col_btn1, col_btn2 = st.columns([1, 5])
        with col_btn1:
            if st.button("🔥 Limpar Fila"):
                st.session_state.carrinho_desvios = []
                st.rerun()
        with col_btn2:
            if st.button("🚀 ENVIAR TODOS OS DESVIOS PARA A PLANILHA"):
                novos_itens = []
                id_atual = len(df_existente) + 1
                
                for item in st.session_state.carrinho_desvios:
                    item["id"] = id_atual
                    novos_itens.append(item)
                    id_atual += 1
                
                df_novos = pd.DataFrame(novos_itens)
                
                # Força o pandas a alinhar exatamente pelas colunas existentes da planilha original
                # Isso impede a criação de colunas duplicadas
                df_novos = df_novos.reindex(columns=df_existente.columns)
                
                df_final = pd.concat([df_existente, df_novos], ignore_index=True)
                
                conn.update(data=df_final)
                st.success(f"✅ Sucesso! {len(novos_itens)} desvios salvos corretamente!")
                st.session_state.carrinho_desvios = []
                st.rerun()

# ------------------------------------------------------------------
# TELA 2: PAINEL DE GESTÃO
# ------------------------------------------------------------------
elif menu == "Painel de Gestão (Plano de Ação)":
    st.header("📊 Painel de Controle e Plano de Ação")
    
    if df_existente.empty or len(df_existente.columns) < 2:
        st.info("Nenhuma não conformidade registrada até o momento.")
    else:
        status_filtro = st.multiselect("Filtrar por Status:", ["Pendente", "Em Andamento", "Concluído"], default=["Pendente", "Em Andamento", "Concluído"])
        df_filtrado = df_existente[df_existente["status"].isin(status_filtro)]
        
        st.dataframe(
            df_filtrado[["id", "local", "categoria", "nr", "prazo", "responsavel", "status"]],
            use_container_width=True, index=False
        )
        
        st.markdown("---")
        st.subheader("🗺️ Mapa de Riscos / Ocorrências")
        try:
            mapa = folium.Map(location=[float(df_filtrado["lat"].mean()), float(df_filtrado["lon"].mean())], zoom_start=12)
            for idx, row in df_filtrado.iterrows():
                folium.Marker(
                    [float(row["lat"]), float(row["lon"])],
                    popup=f"<b>Local:</b> {row['local']}<br><b>Status:</b> {row['status']}"
                ).add_to(mapa)
            st_folium(mapa, width=1000, height=400)
        except Exception:
            st.warning("Sem coordenadas válidas para exibir o mapa.")

        st.markdown("---")
        st.subheader("🔍 Ações e Detalhes da Ocorrência")
        id_selecionado = st.selectbox("Escolha o ID para ver detalhes:", df_filtrado["id"])
        
        if id_selecionado:
            detalhe = df_existente[df_existente["id"] == id_selecionado].iloc[0]
            idx_original = df_existente[df_existente["id"] == id_selecionado].index[0]
            
            col_det1, col_det2 = st.columns(2)
            with col_det1:
                st.write(f"**📍 Local:** {detalhe['local']}")
                st.write(f"**⚠️ Risco:** {detalhe['categoria']}")
                st.write(f"**⚖️ Enquadramento:** {detalhe['nr']}")
                st.write(f"**📝 Descrição:** {detalhe['descricao']}")
                st.write(f"**📅 Prazo:** {detalhe['prazo']}")
                
                for i in range(1, 4):
                    campo_f = f"foto_{i}"
                    if campo_f in detalhe and detalhe[campo_f] and str(detalhe[campo_f]).strip() != "":
                        st.markdown(f"**Visualização da Foto {i}:**")
                        try:
                            st.image(base64.b64decode(detalhe[campo_f]), width=300)
                        except:
                            st.caption("Erro ao processar imagem.")
                
            with col_det2:
                novo_status = st.selectbox("Atualizar status:", ["Pendente", "Em Andamento", "Concluído"], index=["Pendente", "Em Andamento", "Concluído"].index(detalhe["status"]))
                if st.button("Atualizar Status"):
                    df_existente.at[idx_original, "status"] = novo_status
                    conn.update(data=df_existente)
                    st.success("Status atualizado!")
                    st.rerun()
                
                st.markdown("---")
                st.markdown("**Gerar Relatório Técnico:**")
                try:
                    pdf_bytes = gerar_pdf_inspecao(detalhe)
                    st.download_button(
                        label="📥 Descarregar Relatório em PDF",
                        data=bytes(pdf_bytes),
                        file_name=f"Relatorio_Inspecao_SST_ID_{id_selecionado}.pdf",
                        mime="application/pdf"
                    )
                except Exception as e:
                    st.error(f"Erro ao gerar PDF: {e}")
