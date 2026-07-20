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

# --- CATÁLOGO AMPLIADO DE NÃO CONFORMIDADES (AGILIDADE EM CAMPO) ---
DICIONARIO_NRS = {
    "NR 01 - PGR (Gerenciamento de Riscos)": {
        "nr": "NR-01 (Disposições Gerais e Gerenciamento de Riscos Ocupacionais)",
        "recomendacao": "Elaborar ou revisar o PGR anualmente (ou a cada 2 anos), mapeando todos os perigos e implementando um plano de ação claro com o cronograma 5W2H."
    },
    "NR 06 - EPIs (Falta de Registro ou CA Válido)": {
        "nr": "NR-06 (Equipamentos de Proteção Individual)",
        "recomendacao": "Implementar uma ficha de EPI (física ou digital) com assinatura do trabalhador no ato da entrega e criar um sistema de alerta para validade dos CAs em estoque."
    },
    "NR 10 - Instalações Elétricas (Prontuário/Unifilar)": {
        "nr": "NR-10 (Segurança em Instalações e Serviços em Eletricidade)",
        "recomendacao": "Contratar um profissional habilitado (Engenheiro Eletricista) para atualizar os esquemas unifilares e centralizar os laudos de aterramento e SPDA no Prontuário."
    },
    "NR 10 - Painéis Elétricos (Abertos / Gambiarras)": {
        "nr": "NR-10 (Segurança em Instalações e Serviços em Eletricidade)",
        "recomendacao": "Realizar o fechamento dos painéis, instalar barreiras plásticas internas contra contatos acidentais e colar etiquetas de sinalização 'Risco de Choque Elétrico'."
    },
    "NR 12 - Máquinas e Equipamentos (Falta de Proteção)": {
        "nr": "NR-12 (Segurança no Trabalho em Máquinas e Equipamentos)",
        "recomendacao": "Realizar uma Apreciação de Riscos na máquina e instalar proteções físicas mecânicas integradas a chaves de segurança com intertravamento."
    },
    "NR 12 - Painéis e Comandos (Botão de Emergência)": {
        "nr": "NR-12 (Segurança no Trabalho em Máquinas e Equipamentos)",
        "recomendacao": "Adequar o painel instalando botões de parada de emergência do tipo cogumelo em locais de fácil acesso ao operador e realizar testes periódicos de funcionamento."
    },
    "NR 35 - Trabalho em Altura (Falta de AR e PT)": {
        "nr": "NR-35 (Trabalho em Altura)",
        "recomendacao": "Adotar um procedimento rígido onde nenhuma atividade acima de 2 metros inicie sem a emissão da AR/PT assinada pelo supervisor e executores."
    },
    "NR 35 - Ancoragem e EPIs (Ponto Inadequado)": {
        "nr": "NR-35 (Trabalho em Altura)",
        "recomendacao": "Instalar e certificar Linhas de Vida e Pontos de Ancoragem definitivos (ou usar provisórios devidamente calculados por engenheiro mecânico/civil)."
    }
}

# --- FUNÇÃO PARA COMPRIMIR E CONVERTER IMAGEM PARA BASE64 ---
def processar_e_converter_imagem(uploaded_file):
    if uploaded_file is not None:
        try:
            img = Image.open(uploaded_file)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            img.thumbnail((600, 600))
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=40, optimize=True)
            bytes_data = buffer.getvalue()
            string_b64 = base64.b64encode(bytes_data).decode()
            if len(string_b64) > 45000:
                buffer_mini = io.BytesIO()
                img.thumbnail((400, 400))
                img.save(buffer_mini, format="JPEG", quality=25, optimize=True)
                string_b64 = base64.b64encode(buffer_mini.getvalue()).decode()
            return string_b64
        except Exception as e:
            st.error(f"Erro ao processar imagem: {e}")
            return ""
    return ""

# --- FUNÇÃO PARA GERAR RELATÓRIO PDF (COM CAPA, MÚLTIPLOS ITENS E FOTOS) ---
def gerar_pdf_inspecao(lista_dados):
    pdf = FPDF()
    
    # --- CAPA DO RELATÓRIO ---
    pdf.add_page()
    pdf.set_font("Arial", style="B", size=20)
    pdf.set_fill_color(31, 78, 121)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(190, 25, "RELATÓRIO TÉCNICO DE INSPEÇÃO", ln=True, align="C", fill=True)
    pdf.ln(20)
    
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", size=14)
    pdf.cell(190, 10, "Segurança e Saúde no Trabalho - SST", ln=True, align="C")
    pdf.ln(30)
    
    pdf.set_font("Arial", style="B", size=12)
    pdf.cell(190, 8, f"Total de Não Conformidades no Relatório: {len(lista_dados)}", ln=True, align="C")
    pdf.cell(190, 8, f"Data de Emissão: {pd.Timestamp.now().strftime('%d/%m/%Y')}", ln=True, align="C")
    pdf.ln(40)
    
    pdf.set_font("Arial", size=10)
    pdf.cell(190, 8, "Documento gerado automaticamente pelo sistema SST Inspeções Pro.", ln=True, align="C")

    # --- PÁGINAS DE CONTEÚDO (UMA PÁGINA POR NÃO CONFORMIDADE) ---
    for dados in lista_dados:
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        
        pdf.set_fill_color(31, 78, 121)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(190, 12, f"DETALHES DA NÃO CONFORMIDADE - ID #{dados.get('id')}", ln=True, align="C", fill=True)
        pdf.ln(5)
        
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Arial", size=11)
        pdf.cell(95, 8, f"Setor/Local: {dados.get('local')}", border=1)
        pdf.cell(95, 8, f"Data Limite: {dados.get('prazo')}", border=1, ln=True)
        pdf.cell(95, 8, f"Responsável: {dados.get('responsavel')}", border=1)
        pdf.cell(95, 8, f"Status Atual: {dados.get('status')}", border=1, ln=True)
        pdf.ln(5)
        
        pdf.set_font("Arial", style="B", size=11)
        pdf.set_fill_color(220, 220, 220)
        pdf.cell(190, 8, "Descrição do Desvio", ln=True, fill=True)
        pdf.set_font("Arial", size=10)
        pdf.multi_cell(190, 8, str(dados.get('descricao', '')), border=1)
        pdf.ln(5)
        
        pdf.set_font("Arial", style="B", size=11)
        pdf.set_fill_color(220, 220, 220)
        pdf.cell(190, 8, "Fundamentação Legal e Recomendações", ln=True, fill=True)
        pdf.set_font("Arial", size=10)
        pdf.cell(190, 8, f"Enquadramento: {dados.get('nr')}", border=1, ln=True)
        pdf.multi_cell(190, 8, f"Recomendação:\n{dados.get('recomendacao')}", border=1)
        pdf.ln(5)
        
        # Renderização das Fotos via arquivo temporário para o FPDF
        fotos_adicionadas = False
        for i in range(1, 4):
            chave_foto = f'foto_{i}'
            valor_foto = dados.get(chave_foto)
            if valor_foto and str(valor_foto).strip() not in ["", "nan", "None"]:
                if not fotos_adicionadas:
                    pdf.set_font("Arial", style="B", size=11)
                    pdf.cell(190, 8, "Evidências Fotográficas", ln=True, align="L")
                    fotos_adicionadas = True
                try:
                    import os
                    img_data = base64.b64decode(valor_foto)
                    temp_filename = f"temp_foto_{i}_{dados.get('id', 'item')}.jpg"
                    with open(temp_filename, "wb") as f:
                        f.write(img_data)
                    pdf.image(temp_filename, w=50, h=38)
                    pdf.ln(2)
                    if os.path.exists(temp_filename):
                        os.remove(temp_filename)
                except Exception as ex:
                    print(f"Erro ao inserir imagem {i} no PDF: {ex}")
                    pass

        pdf.ln(10)
        pdf.set_font("Arial", size=9)
        pdf.cell(95, 10, "_________________________________________", align="C")
        pdf.cell(95, 10, "_________________________________________", ln=True, align="C")
        pdf.cell(95, 5, "Assinatura do Inspetor de SST", align="C")
        pdf.cell(95, 5, "Assinatura do Responsável", ln=True, align="C")
    
    return pdf.output(dest='S').encode('latin-1')

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
        categoria = st.selectbox("Selecione o Cenário / Desvio Frequente:", list(DICIONARIO_NRS.keys()))
        descricao = st.text_area("Descrição detalhada do desvio:", placeholder="Descreva o problema encontrado...")
        
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
            f1_str = processar_e_converter_imagem(foto1)
            f2_str = processar_e_converter_imagem(foto2)
            f3_str = processar_e_converter_imagem(foto3)
            
            st.session_state.carrinho_desvios.append({
                "local": str(local_global),
                "categoria": str(categoria),
                "descricao": str(descricao),
                "nr": str(nr_sugerida),
                "recomendacao": str(reco_usuario),
                "prazo": prazo.strftime('%d/%m/%Y'),
                "responsavel": str(responsavel) if responsavel else "Não Definido",
                "lat": str(lat_global),
                "lon": str(lon_global),
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
            if st.button("🚀 ENVIAR TODOS OS DESVIOS PARA O SUPABASE"):
                try:
                    for item in st.session_state.carrinho_desvios:
                        if "id" in item:
                            del item["id"]
                        
                        colunas_banco = [
                            "local", "categoria", "descricao", "nr", "recomendacao", 
                            "prazo", "responsavel", "lat", "lon", "status", "foto_1", "foto_2", "foto_3"
                        ]
                        item_filtrado = {k: v for k, v in item.items() if k in colunas_banco}
                        
                        supabase.table("inspecoes").insert(item_filtrado).execute()
                        
                    st.success(f"✅ Sucesso! {len(st.session_state.carrinho_desvios)} desvios salvos no Supabase!")
                    st.session_state.carrinho_desvios = []
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro detalhado do Supabase: {e}")

# ------------------------------------------------------------------
# TELA 2: PAINEL DE GESTÃO
# ------------------------------------------------------------------
elif menu == "Painel de Gestão (Plano de Ação)":
    st.header("📊 Painel de Controle e Plano de Ação")
    
    if df_existente.empty or len(df_existente) == 0 or "id" not in df_existente.columns:
        st.info("Nenhuma não conformidade registrada até o momento.")
    else:
        status_filtro = st.multiselect("Filtrar por Status:", ["Pendente", "Em Andamento", "Concluído"], default=["Pendente", "Em Andamento", "Concluído"])
        df_filtrado = df_existente[df_existente["status"].isin(status_filtro)]
        
        if df_filtrado.empty:
            st.info("Nenhum registro encontrado para os filtros selecionados.")
        else:
            st.dataframe(
                df_filtrado[["id", "local", "categoria", "nr", "prazo", "responsavel", "status"]],
                use_container_width=True
            )
            
            st.markdown("---")
            st.subheader("🗺️ Mapa de Riscos / Ocorrências")
            try:
                mapa = folium.Map(location=[float(df_filtrado["lat"].astype(float).mean()), float(df_filtrado["lon"].astype(float).mean())], zoom_start=12)
                for idx, row in df_filtrado.iterrows():
                    folium.Marker(
                        [float(row["lat"]), float(row["lon"])],
                        popup=f"<b>Local:</b> {row['local']}<br><b>Status:</b> {row['status']}"
                    ).add_to(mapa)
                st_folium(mapa, width=1000, height=400)
            except Exception:
                st.warning("Sem coordenadas válidas para exibir o mapa.")

            st.markdown("---")
            st.subheader("🔍 Ações, Atualização de Status e Relatório Consolidado")
            
            ids_disponiveis = df_filtrado["id"].unique().tolist()
            ids_selecionados = st.multiselect("Selecione os IDs para gerar o Relatório PDF Consolidado:", ids_disponiveis, default=ids_disponiveis[:1] if ids_disponiveis else [])
            
            if ids_selecionados:
                registros_selecionados = df_existente[df_existente["id"].isin(ids_selecionados)].to_dict(orient="records")
                try:
                    pdf_bytes = gerar_pdf_inspecao(registros_selecionados)
                    st.download_button(
                        label=f"📥 Baixar Relatório em PDF ({len(ids_selecionados)} ocorrência(s))",
                        data=bytes(pdf_bytes),
                        file_name="Relatorio_Consolidado_SST.pdf",
                        mime="application/pdf"
                    )
                except Exception as e:
                    st.error(f"Erro ao gerar PDF: {e}")

            st.markdown("---")
            st.subheader("⚙️ Gerenciar Ocorrência Individual")
            id_individual = st.selectbox("Escolha um ID para atualizar o status:", ids_disponiveis)
            
            if id_individual:
                detalhe = df_existente[df_existente["id"].astype(str) == str(id_individual)].iloc[0]
                idx_original = df_existente[df_existente["id"].astype(str) == str(id_individual)].index[0]
                
                col_det1, col_det2 = st.columns(2)
                with col_det1:
                    st.write(f"**📍 Local:** {detalhe['local']}")
                    st.write(f"**⚠️ Risco:** {detalhe['categoria']}")
                    st.write(f"**⚖️ Enquadramento:** {detalhe['nr']}")
                    st.write(f"**📝 Descrição:** {detalhe['descricao']}")
                    st.write(f"**📅 Prazo:** {detalhe['prazo']}")
                    
                    for i in range(1, 4):
                        campo_f = f"foto_{i}"
                        if campo_f in detalhe and detalhe[campo_f] and str(detalhe[campo_f]).strip() not in ["", "nan", "None"]:
                            st.markdown(f"**Visualização da Foto {i}:**")
                            try:
                                st.image(base64.b64decode(detalhe[campo_f]), width=300)
                            except:
                                st.caption("Erro ao processar imagem.")
                
                with col_det2:
                    status_opcoes = ["Pendente", "Em Andamento", "Concluído"]
                    status_atual = detalhe["status"] if detalhe["status"] in status_opcoes else "Pendente"
                    novo_status = st.selectbox("Atualizar status:", status_opcoes, index=status_opcoes.index(status_atual), key=f"status_{id_individual}")
                    
                    if st.button("Atualizar Status no Banco"):
                        try:
                            supabase.table("inspecoes").update({"status": novo_status}).eq("id", int(id_individual)).execute()
                            st.success("Status atualizado com sucesso!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao atualizar status: {e}")
