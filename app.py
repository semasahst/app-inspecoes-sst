import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from streamlit_gsheets import GSheetsConnection
from fpdf import FPDF

# Configuração da página
st.set_page_config(page_title="SST Inspeções Pro", page_icon="🛡️", layout="wide")

# --- CONEXÃO NATIVA COM O GOOGLE SHEETS ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    # Lê todos os dados existentes
    df_existente = conn.read(ttl=0) # ttl=0 garante dados em tempo real sem cache
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
    pdf.cell(190, 8, "Fundamentação Legal e Recomendações Técnicas", ln=True, fill=True)
    pdf.set_font("Arial", size=11)
    pdf.cell(190, 8, f"Enquadramento: {dados['nr']}", border=1, ln=True)
    
    pdf.set_font("Arial", style="I", size=11)
    pdf.multi_cell(190, 8, f"Recomendação Proposta:\n{dados['recomendacao']}", border=1)
    pdf.ln(15)
    
    pdf.set_font("Arial", size=9)
    pdf.cell(95, 10, "_________________________________________", ln=False, align="C")
    pdf.cell(95, 10, "_________________________________________", ln=True, align="C")
    pdf.cell(95, 5, "Assinatura do Inspetor de SST", ln=False, align="C")
    pdf.cell(95, 5, "Assinatura do Responsável pelo Setor", ln=True, align="C")
    
    return pdf.output()

# --- TÍTULO DO APP ---
menu = st.sidebar.selectbox("Navegação", ["Nova Inspeção", "Painel de Gestão (Plano de Ação)"])

# ------------------------------------------------------------------
# TELA 1: NOVA INSPEÇÃO
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
                novo_id = len(df_existente) + 1
                
                nova_linha = pd.DataFrame([{
                    "id": novo_id,
                    "local": local,
                    "categoria": categoria,
                    "descricao": descricao,
                    "nr": nr_sugerida,
                    "recomendacao": reco_usuario,
                    "prazo": prazo.strftime('%d/%m/%Y'),
                    "responsavel": responsavel if responsavel else "Não Definido",
                    "lat": lat,
                    "lon": lon,
                    "status": "Pendente"
                }])
                
                # Junta o dado novo com os antigos e faz o update na planilha
                df_atualizado = pd.concat([df_existente, nova_linha], ignore_index=True)
                conn.update(data=df_atualizado)
                st.success("✅ Inspeção registrada com sucesso na Planilha Google!")
                st.rerun()

# ------------------------------------------------------------------
# TELA 2: PAINEL DE GESTÃO
# ------------------------------------------------------------------
elif menu == "Painel de Gestão (Plano de Ação)":
    st.header("📊 Painel de Controle e Plano de Ação")
    
    if df_existente.empty:
        st.info("Nenhuma não conformidade registrada até o momento.")
    else:
        status_filtro = st.multiselect("Filtrar por Status:", ["Pendente", "Em Andamento", "Concluído"], default=["Pendente", "Em Andamento", "Concluído"])
        df_filtrado = df_existente[df_existente["status"].isin(status_filtro)]
        
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

        # Atualizar status e Detalhes
        st.markdown("---")
        st.subheader("🔍 Ações e Detalhes da Ocorrência")
        
        id_selecionado = st.selectbox("Escolha o ID para ver detalhes, atualizar status ou gerar PDF:", df_filtrado["id"])
        
        if id_selecionado:
            detalhe = df_existente[df_existente["id"] == id_selecionado].iloc[0]
            idx_original = df_existente[df_existente["id"] == id_selecionado].index[0]
            
            col_det1, col_det2 = st.columns(2)
            
            with col_det1:
                st.write(f"**📍 Local:** {detalhe['local']}")
                st.write(f"**⚠️ Risco:** {detalhe['categoria']}")
                st.write(f"**⚖️ Enquadramento:** {detalhe['nr']}")
                st.write(f"**📝 Descrição:** {detalhe['descricao']}")
                st.write(f"**💡 Recomendação:** {detalhe['recomendacao']}")
                st.write(f"**📅 Prazo:** {detalhe['prazo']}")
                st.write(f"**👤 Responsável:** {detalhe['responsavel']}")
                
            with col_det2:
                novo_status = st.selectbox(
                    f"Atualizar status do ID {id_selecionado}:", 
                    ["Pendente", "Em Andamento", "Concluído"],
                    index=["Pendente", "Em Andamento", "Concluído"].index(detalhe["status"])
                )
                
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
