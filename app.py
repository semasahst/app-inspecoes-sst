import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

# Configuração da página do Streamlit
st.set_page_config(
    page_title="SST Inspeções Pro",
    page_icon="🛡️",
    layout="wide"
)

# --- BANCO DE DADOS DE NRs (EXEMPLO) ---
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

# --- ESTADOS DO APP (Simulação de Banco de Dados na Memória) ---
if "inspecoes" not in st.session_state:
    st.session_state.inspecoes = []

# --- TÍTULO DO APP ---
st.title("🛡️ Sistema de Inspeção de Segurança do Trabalho")
st.markdown("Registre inconformidades em campo, associe às NRs e gere relatórios instantâneos.")

# --- BARRA LATERAL (MENU) ---
menu = st.sidebar.selectbox(
    "Navegação", 
    ["Nova Inspeção", "Painel de Gestão (Plano de Ação)"]
)

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
            
            # Geolocalização manual rápida (enquanto não integramos o script GPS)
            st.markdown("**Geolocalização Aproximada (para o Mapa):**")
            lat = st.number_input("Latitude", value=-23.55052, format="%.5f")
            lon = st.number_input("Longitude", value=-46.63330, format="%.5f")
            
        with col2:
            descricao = st.text_area("Descrição Detalhada do Desvio:", placeholder="Descreva o que está errado...")
            # Câmera fotográfica integrada
            foto = st.camera_input("Capturar Foto da Não Conformidade")

        st.markdown("---")
        st.subheader("📋 Enquadramento Legal Sugerido")
        
        # Busca automática da NR baseada na categoria selecionada
        nr_sugerida = DICIONARIO_NRS[categoria]["nr"]
        reco_sugerida = DICIONARIO_NRS[categoria]["recomendacao"]
        
        st.info(f"**Dispositivo Legal aplicável:** {nr_sugerida}")
        reco_usuario = st.text_area("Recomendação/Plano de Ação Proposto:", value=reco_sugerida)
        
        prazo = st.date_input("Prazo para Regularização:")
        responsavel = st.text_input("Responsável pela Ação:")

        # Botão para salvar
        salvar = st.form_submit_button("Gravar Inspeção")
        
        if salvar:
            if not local or not descricao:
                st.error("Por favor, preencha o Local e a Descrição!")
            else:
                # Salva o registro temporariamente na memória
                novo_registro = {
                    "id": len(st.session_state.inspecoes) + 1,
                    "local": local,
                    "categoria": categoria,
                    "descricao": descricao,
                    "nr": nr_sugerida,
                    "recomendacao": reco_usuario,
                    "prazo": prazo.strftime('%d/%m/%Y'),
                    "responsavel": responsavel if responsavel else "Não Definido",
                    "lat": lat,
                    "lon": lon,
                    "status": "Pendente",
                    "foto": foto # Guarda a imagem capturada
                }
                st.session_state.inspecoes.append(novo_registro)
                st.success("✅ Inspeção registrada com sucesso com base nas NRs!")

# ------------------------------------------------------------------
# TELA 2: PAINEL DE GESTÃO / PLANO DE AÇÃO
# ------------------------------------------------------------------
elif menu == "Painel de Gestão (Plano de Ação)":
    st.header("📊 Painel de Controle e Plano de Ação")
    
    if not st.session_state.inspecoes:
        st.info("Nenhuma não conformidade registrada até o momento. Vá em 'Nova Inspeção' para começar!")
    else:
        # Criar DataFrame para exibição dos dados
        df = pd.DataFrame(st.session_state.inspecoes)
        
        # Filtros rápidos no painel
        status_filtro = st.multiselect("Filtrar por Status:", ["Pendente", "Em Andamento", "Concluído"], default=["Pendente", "Em Andamento", "Concluído"])
        df_filtrado = df[df["status"].isin(status_filtro)]
        
        # Exibe a tabela do plano de ação
        st.dataframe(
            df_filtrado[["id", "local", "categoria", "nr", "prazo", "responsavel", "status"]],
            use_container_width=True,
            hide_index=True
        )
        
        st.markdown("---")
        st.subheader("🗺️ Mapa de Riscos / Ocorrências")
        
        # Centraliza o mapa na média das coordenadas cadastradas
        mapa = folium.Map(location=[df_filtrado["lat"].mean(), df_filtrado["lon"].mean()], zoom_start=12)
        
        for idx, row in df_filtrado.iterrows():
            folium.Marker(
                [row["lat"], row["lon"]],
                popup=f"<b>Local:</b> {row['local']}<br><b>Risco:</b> {row['categoria']}<br><b>Status:</b> {row['status']}",
                tooltip=f"{row['local']} ({row['categoria']})"
            ).add_to(mapa)
            
        st_folium(mapa, width=1000, height=400)
        
        st.markdown("---")
        st.subheader("🔍 Detalhes e Evidências")
        
        # Seletor para ver detalhes e fotos de um item específico
        item_selecionado = st.selectbox("Escolha uma ocorrência para ver fotos e gerar PDF:", df_filtrado["id"])
        
        if item_selecionado:
            detalhe = next(item for item in st.session_state.inspecoes if item["id"] == item_selecionado)
            col_det1, col_det2 = st.columns(2)
            
            with col_det1:
                st.write(f"**📍 Local:** {detalhe['local']}")
                st.write(f"**⚠️ Risco:** {detalhe['categoria']}")
                st.write(f"**⚖️ Enquadramento:** {detalhe['nr']}")
                st.write(f"**📝 Descrição:** {detalhe['descricao']}")
                st.write(f"**💡 Recomendação:** {detalhe['recomendacao']}")
                st.write(f"**👤 Responsável:** {detalhe['responsavel']}")
                st.write(f"**📅 Prazo:** {detalhe['prazo']}")
                
                # Mudar o status do plano de ação
                novo_status = st.selectbox(
                    f"Atualizar Status (ID {detalhe['id']}):", 
                    ["Pendente", "Em Andamento", "Concluído"], 
                    index=["Pendente", "Em Andamento", "Concluído"].index(detalhe["status"])
                )
                if st.button("Atualizar Status"):
                    detalhe["status"] = novo_status
                    st.success("Status atualizado!")
                    st.rerun()
                    
            with col_det2:
                if detalhe["foto"] is not None:
                    st.image(detalhe["foto"], caption=f"Evidência fotográfica do ID {detalhe['id']}", use_container_width=True)
                else:
                    st.warning("Nenhuma evidência fotográfica anexada para este item.")
