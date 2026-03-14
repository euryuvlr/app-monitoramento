import streamlit as st
import pandas as pd
import os
import time
from datetime import datetime
from scrapers.linkedin_scraper import LinkedInCompetitorMonitor

# Configuração da página
st.set_page_config(
    page_title="Monitoramento de Concorrentes",
    page_icon="📊",
    layout="wide"
)

# ========== CREDENCIAIS (INSERIDAS DIRETAMENTE) ==========
LINKEDIN_EMAIL = "euowlie@gmail.com"
LINKEDIN_PASSWORD = "Ryuvlr*963,@"
GEMINI_API_KEY = "AIzaSyDQWWGMVcfZA6VW66iPruZk6Zh-BTR93wY"

# Lista de empresas (mantida fixa)
EMPRESAS = [
    "https://www.linkedin.com/company/atento/",
    "https://www.linkedin.com/company/wearetpgroup/",
    "https://www.linkedin.com/company/callink-call-center/",
    "https://www.linkedin.com/company/csu-digital/",
    "https://www.linkedin.com/company/algar-oficial/",
    "https://www.linkedin.com/company/almavivaexperience/",
    "https://www.linkedin.com/company/concentrix/",
    "https://www.linkedin.com/company/neohypeco/",
    "https://www.linkedin.com/company/konecta-group/",
    "https://www.linkedin.com/company/vgx-contact-center/",
    "https://www.linkedin.com/showcase/concentrixbr/",
    "https://www.linkedin.com/company/foundever/",
    "https://www.linkedin.com/company/stefanini/",
]

# ========== TÍTULO ==========
st.title("📊 Monitoramento Semanal de Concorrentes")
st.markdown("---")

# ========== BOTÃO PRINCIPAL ==========
if st.button("🚀 GERAR RELATÓRIO AGORA", type="primary", use_container_width=True):
    
    # Container para mostrar o progresso
    status = st.empty()
    barra = st.progress(0)
    
    status.info("⏳ Iniciando monitoramento... Isso leva alguns minutos.")
    
    # Criar uma pasta temporária para salvar o relatório
    os.makedirs("temp_reports", exist_ok=True)
    
    # ===== PROGRESSO =====
    barra.progress(10)
    status.text("🔑 Fazendo login no LinkedIn...")
    time.sleep(2)
    
    # Inicializar o monitor
    try:
        monitor = LinkedInCompetitorMonitor(
            email=LINKEDIN_EMAIL,
            password=LINKEDIN_PASSWORD,
            headless=True
        )
        
        if not monitor.login():
            st.error("❌ Falha no login do LinkedIn. Verifique as credenciais.")
            barra.progress(100)
        else:
            barra.progress(30)
            status.text("📥 Coletando posts das empresas...")
            
            # Coletar posts
            todos_posts = []
            for i, url in enumerate(EMPRESAS):
                status.text(f"📥 Processando {i+1}/{len(EMPRESAS)}: {url.split('/')[-2]}")
                posts = monitor.scrape_company_posts(url, max_posts=30, days_back=7)
                todos_posts.extend(posts)
                barra.progress(30 + int((i+1)/len(EMPRESAS) * 30))
                time.sleep(2)
            
            monitor.close()
            
            if not todos_posts:
                st.warning("⚠️ Nenhum post encontrado no período.")
                barra.progress(100)
            else:
                barra.progress(70)
                status.text("📊 Organizando dados...")
                
                # Criar DataFrame
                df = pd.DataFrame(todos_posts)
                
                # Selecionar e renomear colunas
                colunas_disponiveis = ['empresa', 'data_raw', 'conteudo', 'likes', 'comentarios']
                colunas_existentes = [col for col in colunas_disponiveis if col in df.columns]
                df = df[colunas_existentes]
                
                # Renomear para português
                mapa_nomes = {
                    'empresa': 'Concorrente',
                    'data_raw': 'Data',
                    'conteudo': 'Conteúdo',
                    'likes': 'Likes',
                    'comentarios': 'Comentários'
                }
                df = df.rename(columns=mapa_nomes)
                
                # Salvar Excel
                timestamp = datetime.now().strftime("%Y%m%d_%H%M")
                filename = f"temp_reports/relatorio_{timestamp}.xlsx"
                df.to_excel(filename, index=False)
                
                barra.progress(100)
                status.success("✅ Relatório gerado com sucesso!")
                
                # Mostrar prévia
                st.markdown("### 📋 Prévia do Relatório")
                st.dataframe(df.head(10), use_container_width=True)
                
                # Botão de download
                with open(filename, "rb") as f:
                    st.download_button(
                        label="📥 BAIXAR EXCEL COMPLETO",
                        data=f,
                        file_name=os.path.basename(filename),
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                
    except Exception as e:
        st.error(f"❌ Erro durante execução: {str(e)}")
        try:
            monitor.close()
        except:
            pass

# ========== INSTRUÇÕES ==========
with st.expander("📖 Como usar"):
    st.markdown("""
    1. Clique em **"GERAR RELATÓRIO AGORA"**
    2. Aguarde o processamento (cerca de 5-10 minutos)
    3. Visualize a prévia dos dados
    4. Faça o download do Excel completo
    
    O relatório contém posts dos últimos 7 dias de 13 concorrentes.
    """)

# Rodapé
st.markdown("---")
st.markdown("🔒 Desenvolvido para AeC - Relacionamento com Responsabilidade")