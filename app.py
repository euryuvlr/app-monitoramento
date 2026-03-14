import streamlit as st
import pandas as pd
import os
import time
from datetime import datetime
from scrapers.linkedin_playwright import LinkedInCompetitorMonitor

# Configuração da página
st.set_page_config(
    page_title="Monitoramento de Concorrentes",
    page_icon="📊",
    layout="wide"
)

# ========== CREDENCIAIS (via variáveis de ambiente) ==========
LINKEDIN_EMAIL = os.environ.get("LINKEDIN_EMAIL")
LINKEDIN_PASSWORD = os.environ.get("LINKEDIN_PASSWORD")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Verificar se as variáveis foram carregadas
if not LINKEDIN_EMAIL or not LINKEDIN_PASSWORD:
    st.error("❌ Credenciais do LinkedIn não configuradas. Verifique as variáveis de ambiente no Railway.")
    st.stop()

# Lista de empresas (pode vir do config.py)
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
    
    status = st.empty()
    barra = st.progress(0)
    
    status.info("⏳ Iniciando monitoramento... Isso leva alguns minutos.")
    
    os.makedirs("temp_reports", exist_ok=True)
    
    barra.progress(10)
    status.text("🔑 Fazendo login no LinkedIn...")
    time.sleep(2)
    
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
                
                df = pd.DataFrame(todos_posts)
                
                # Selecionar colunas
                colunas = ['empresa', 'data_raw', 'conteudo', 'likes', 'comentarios']
                df = df[[c for c in colunas if c in df.columns]]
                df.columns = ['Concorrente', 'Data', 'Conteúdo', 'Likes', 'Comentários']
                
                # Salvar Excel
                timestamp = datetime.now().strftime("%Y%m%d_%H%M")
                filename = f"temp_reports/relatorio_{timestamp}.xlsx"
                df.to_excel(filename, index=False)
                
                barra.progress(100)
                status.success("✅ Relatório gerado com sucesso!")
                
                st.markdown("### 📋 Prévia do Relatório")
                st.dataframe(df.head(10), use_container_width=True)
                
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

with st.expander("📖 Como usar"):
    st.markdown("""
    1. Clique em **"GERAR RELATÓRIO AGORA"**
    2. Aguarde o processamento (cerca de 5-10 minutos)
    3. Visualize a prévia dos dados
    4. Faça o download do Excel completo
    """)

st.markdown("---")
st.markdown("🔒 Desenvolvido para AeC - Relacionamento com Responsabilidade")