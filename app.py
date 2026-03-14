import streamlit as st
import pandas as pd
import os
import time
import json
import traceback
from datetime import datetime
from scrapers.linkedin_playwright import LinkedInCompetitorMonitor

st.set_page_config(page_title="Monitoramento de Concorrentes", page_icon="📊", layout="wide")

# Credenciais via variáveis de ambiente
LINKEDIN_EMAIL = os.environ.get("LINKEDIN_EMAIL", "")
LINKEDIN_PASSWORD = os.environ.get("LINKEDIN_PASSWORD", "")

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

st.title("📊 Monitoramento Semanal de Concorrentes")
st.markdown("---")

# ========== CONFIGURAÇÃO DE COOKIES ==========
st.sidebar.header("🔐 Configuração de Cookies")

if 'cookies_saved' not in st.session_state:
    st.session_state.cookies_saved = False
if 'login_verified' not in st.session_state:
    st.session_state.login_verified = False

with st.sidebar.expander("📋 Instruções", expanded=True):
    st.markdown("""
    1. Use uma extensão como **EditThisCookie** no Chrome
    2. Faça login no LinkedIn e exporte todos os cookies
    3. Copie o JSON completo
    4. Cole abaixo e clique em "Salvar Cookies"
    """)

cookies_json = st.sidebar.text_area("Cole os cookies aqui (formato JSON)", height=300)

if st.sidebar.button("💾 Salvar Cookies"):
    if cookies_json:
        try:
            cookies = json.loads(cookies_json)
            os.makedirs("playwright_data", exist_ok=True)
            with open("playwright_data/cookies.json", "w") as f:
                json.dump(cookies, f, indent=2)
            st.sidebar.success(f"✅ {len(cookies)} cookies salvos!")
            st.session_state.cookies_saved = True
        except Exception as e:
            st.sidebar.error(f"❌ Erro ao salvar cookies: {e}")
    else:
        st.sidebar.warning("⚠️ Cole os cookies primeiro")

if st.sidebar.button("🔍 Verificar Login"):
    with st.spinner("Verificando sessão..."):
        try:
            monitor = LinkedInCompetitorMonitor(LINKEDIN_EMAIL, LINKEDIN_PASSWORD, headless=True)
            if monitor.login():
                st.session_state.login_verified = True
                st.sidebar.success("✅ Login OK!")
            else:
                st.sidebar.error("❌ Sessão não encontrada. Verifique os cookies.")
            monitor.close()
        except Exception as e:
            st.sidebar.error(f"❌ Erro na verificação: {e}")
        st.rerun()

if st.session_state.cookies_saved:
    st.sidebar.success("✅ Cookies configurados!")
if st.session_state.login_verified:
    st.sidebar.success("✅ Login verificado!")

# ========== BOTÃO PRINCIPAL ==========
if st.button("🚀 GERAR RELATÓRIO AGORA", type="primary", use_container_width=True):
    if not st.session_state.login_verified:
        st.error("❌ Verifique o login na barra lateral primeiro.")
        st.stop()
    
    # Container para logs
    log_container = st.empty()
    status = st.empty()
    barra = st.progress(0)
    status.info("⏳ Iniciando monitoramento...")
    
    # Criar área de logs expansível
    with st.expander("📋 Logs em tempo real", expanded=True):
        log_area = st.empty()
        logs = []
        
        def add_log(msg):
            logs.append(msg)
            log_area.code("\n".join(logs[-20:]), language="text")
    
    os.makedirs("temp_reports", exist_ok=True)

    try:
        add_log("🚀 Iniciando monitor...")
        monitor = LinkedInCompetitorMonitor(LINKEDIN_EMAIL, LINKEDIN_PASSWORD, headless=True)
        
        barra.progress(10)
        status.text("📥 Coletando posts...")
        todos_posts = []
        
        for i, url in enumerate(EMPRESAS):
            empresa_nome = url.split('/')[-2]
            add_log(f"\n--- Processando {i+1}/{len(EMPRESAS)}: {empresa_nome} ---")
            status.text(f"📥 Processando {i+1}/{len(EMPRESAS)}: {empresa_nome}")
            
            try:
                posts = monitor.scrape_company_posts(url, max_posts=30, days_back=7)
                add_log(f"📊 Posts encontrados: {len(posts)}")
                todos_posts.extend(posts)
            except Exception as e:
                add_log(f"❌ Erro ao processar {empresa_nome}: {str(e)}")
                add_log(traceback.format_exc())
            
            barra.progress(30 + int((i+1)/len(EMPRESAS) * 30))
            time.sleep(2)
        
        monitor.close()
        add_log("\n✅ Coleta finalizada!")

        if not todos_posts:
            add_log("⚠️ Nenhum post encontrado no período.")
            st.warning("⚠️ Nenhum post encontrado no período.")
            barra.progress(100)
        else:
            add_log(f"📊 Total de posts coletados: {len(todos_posts)}")
            barra.progress(70)
            status.text("📊 Organizando dados...")
            
            df = pd.DataFrame(todos_posts)
            add_log(f"📋 Colunas disponíveis: {list(df.columns)}")
            
            colunas = ['empresa', 'data_raw', 'conteudo', 'likes', 'comentarios']
            df = df[[c for c in colunas if c in df.columns]]
            df.columns = ['Concorrente', 'Data', 'Conteúdo', 'Likes', 'Comentários']

            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            filename = f"temp_reports/relatorio_{timestamp}.xlsx"
            df.to_excel(filename, index=False)
            add_log(f"💾 Arquivo salvo: {filename}")

            barra.progress(100)
            status.success("✅ Relatório gerado!")
            st.markdown("### 📋 Prévia")
            st.dataframe(df.head(10), use_container_width=True)
            
            with open(filename, "rb") as f:
                st.download_button(
                    "📥 BAIXAR EXCEL",
                    data=f,
                    file_name=os.path.basename(filename),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
    except Exception as e:
        add_log(f"❌ Erro geral: {str(e)}")
        add_log(traceback.format_exc())
        st.error(f"❌ Erro durante execução: {e}")
        try:
            monitor.close()
        except:
            pass

# ========== INSTRUÇÕES ==========
with st.expander("📖 Como usar"):
    st.markdown("""
    1. **Primeira vez:** 
       - Instale a extensão EditThisCookie no Chrome
       - Faça login no LinkedIn normalmente
       - Exporte os cookies e cole na barra lateral
       - Clique em "Salvar Cookies" e depois "Verificar Login"
    
    2. **Executar relatório:**
       - Clique em "GERAR RELATÓRIO AGORA"
       - Acompanhe os logs em tempo real
       - Aguarde o processamento (5-10 minutos)
       - Baixe o Excel completo
    """)

st.markdown("---")
st.markdown("🔒 Desenvolvido para AeC")