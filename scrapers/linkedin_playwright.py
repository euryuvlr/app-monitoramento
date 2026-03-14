from playwright.sync_api import sync_playwright
import time
from datetime import datetime, timedelta
import re
import os
import json

class LinkedInCompetitorMonitor:
    def __init__(self, email, password, headless=True):
        self.email = email
        self.password = password
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.page = None
        self.context = None
        self._setup_driver()

    def _setup_driver(self):
        """Inicializa o Playwright com suporte a sessão persistente"""
        self.playwright = sync_playwright().start()
        
        # Configurar pasta para salvar sessão
        user_data_dir = "./playwright_data"
        os.makedirs(user_data_dir, exist_ok=True)
        
        self.browser = self.playwright.chromium.launch_persistent_context(
            user_data_dir,
            headless=self.headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu'
            ],
            user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080}
        )
        
        # Abrir uma nova página
        self.page = self.browser.new_page()

    def login(self):
        """
        FAÇA LOGIN MANUAL UMA ÚNICA VEZ.
        Depois disso, a sessão será salva e reutilizada automaticamente.
        """
        print("="*50)
        print("🔑 INSTRUÇÕES PARA LOGIN MANUAL")
        print("="*50)
        print("O LinkedIn está pedindo verificação (2FA/código).")
        print("Por favor, faça o login manualmente no navegador que vai abrir.")
        print("\nPassos:")
        print("1. Digite seu email e senha NORMALMENTE")
        print("2. Quando pedir o código de verificação, DIGITE")
        print("3. Após entrar no feed, volte aqui e pressione ENTER")
        print("="*50)
        
        # Abrir página de login
        self.page.goto("https://www.linkedin.com/login")
        time.sleep(2)
        
        # Pré-preencher email e senha (opcional, pode fazer manual)
        try:
            self.page.fill("#username", self.email)
            self.page.fill("#password", self.password)
            print("✅ Campos de email/senha preenchidos (confirme se estão corretos)")
        except:
            print("⚠️ Preencha email e senha manualmente")
        
        print("\n🖥️ FAÇA O LOGIN MANUALMENTE AGORA...")
        input("⏸️  Pressione ENTER DEPOIS de fazer o login completo (já no feed) >>> ")
        
        # Verificar se está no feed
        current_url = self.page.url
        if "feed" in current_url:
            print("✅ Login confirmado! Sessão salva para próximas execuções.")
            
            # Salvar cookies explicitamente (já é persistente pelo user_data_dir)
            cookies = self.context.cookies()
            with open("linkedin_cookies_backup.json", "w") as f:
                json.dump(cookies, f)
            print("💾 Backup de cookies salvo!")
            return True
        else:
            print(f"❌ Parece que você não está no feed. URL atual: {current_url}")
            return False

    def _check_login(self):
        """Verifica se a sessão ainda é válida"""
        try:
            self.page.goto("https://www.linkedin.com/feed/")
            time.sleep(2)
            if "feed" in self.page.url:
                return True
            return False
        except:
            return False

    def _extract_number(self, text):
        if not text:
            return 0
        text = str(text).replace(",", "").replace(".", "")
        multipliers = {'K': 1000, 'M': 1000000}
        for suffix, multiplier in multipliers.items():
            if suffix in text:
                try:
                    return int(float(re.sub(r'[^0-9.]', '', text)) * multiplier)
                except:
                    return 0
        try:
            return int(re.sub(r'[^0-9]', '', text))
        except:
            return 0

    def _parse_date(self, date_text):
        date_text = date_text.lower().strip()
        now = datetime.now()
        padrao_abrev = r"^(\d+)\s*([a-záéíóú]+)$"
        match = re.search(padrao_abrev, date_text)
        if match:
            num = int(match.group(1))
            unid = match.group(2)
            if unid in ['d', 'dia', 'dias']:
                return now - timedelta(days=num)
            if unid in ['sem', 'semana', 'semanas']:
                return now - timedelta(weeks=num)
            if unid in ['m', 'mês', 'meses']:
                return now - timedelta(days=num * 30)
            if unid in ['a', 'ano', 'anos', 'y']:
                return now - timedelta(days=num * 365)
            if unid in ['h', 'hora', 'horas']:
                return now - timedelta(hours=num)
        padrao_port = r"há\s+(\d+)\s+(hora|horas|dia|dias|semana|semanas|mês|meses|ano|anos)"
        match = re.search(padrao_port, date_text)
        if match:
            num = int(match.group(1))
            unid = match.group(2)
            if unid in ["hora", "horas"]:
                return now - timedelta(hours=num)
            if unid in ["dia", "dias"]:
                return now - timedelta(days=num)
            if unid in ["semana", "semanas"]:
                return now - timedelta(weeks=num)
            if unid in ["mês", "meses"]:
                return now - timedelta(days=num*30)
            if unid in ["ano", "anos"]:
                return now - timedelta(days=num*365)
        padrao_eng = r"(\d+)\s+(hour|hours|day|days|week|weeks|month|months|year|years)\s+ago"
        match = re.search(padrao_eng, date_text)
        if match:
            num = int(match.group(1))
            unid = match.group(2)
            if unid in ["hour", "hours"]:
                return now - timedelta(hours=num)
            if unid in ["day", "days"]:
                return now - timedelta(days=num)
            if unid in ["week", "weeks"]:
                return now - timedelta(weeks=num)
            if unid in ["month", "months"]:
                return now - timedelta(days=num*30)
            if unid in ["year", "years"]:
                return now - timedelta(days=num*365)
        return None

    def scrape_company_posts(self, company_url, max_posts=30, days_back=7):
        """Coleta posts usando a sessão já autenticada"""
        # Verificar se ainda está logado
        if not self._check_login():
            print("⚠️ Sessão expirada! Você precisa fazer login manual novamente.")
            if not self.login():
                print("❌ Falha no login. Abortando.")
                return []
        
        print(f"\n📊 {company_url.split('/')[-2]}")
        posts_data = []
        cutoff = datetime.now() - timedelta(days=days_back)
        posts_found = 0
        
        try:
            self.page.goto(company_url)
            time.sleep(3)
            
            # Tentar aba de posts
            try:
                self.page.click("a[href*='posts/']")
                print("✅ Aba 'posts' clicada")
            except:
                try:
                    self.page.click("a[href*='recent-activity']")
                    print("✅ Aba 'recent-activity' clicada")
                except:
                    print("⚠️ Usando URL direta...")
                    self.page.goto(company_url.rstrip('/') + "/posts/?feedView=all")
            
            time.sleep(3)
            
            last_height = self.page.evaluate("document.body.scrollHeight")
            scroll_attempts = 0
            max_scrolls = 8
            
            while posts_found < max_posts and scroll_attempts < max_scrolls:
                self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(2)
                
                posts = self.page.query_selector_all("li[data-urn], article.feed-shared-update-v2, div.occludable-update")
                print(f"🔄 Encontrados {len(posts)} elementos")
                
                for post in posts[posts_found:]:
                    try:
                        # Extrair data (segunda parte após "•")
                        date_text = None
                        selectores = [
                            "span.feed-shared-actor__sub-description",
                            "span.feed-shared-actor__sub-meta",
                            ".update-components-actor__sub-description"
                        ]
                        
                        for selector in selectores:
                            elem = post.query_selector(selector)
                            if elem:
                                texto = elem.inner_text()
                                partes = re.split(r' • |\•|\|', texto)
                                if len(partes) >= 2:
                                    candidato = partes[1].strip()
                                    if re.search(r'\d+\s*[a-záéíóú]', candidato):
                                        date_text = candidato
                                        break
                                if not date_text:
                                    for parte in partes:
                                        if re.search(r'\d+\s*[a-záéíóú]', parte):
                                            date_text = parte.strip()
                                            break
                            if date_text:
                                break
                        
                        if not date_text:
                            continue
                        
                        post_date = self._parse_date(date_text)
                        if not post_date:
                            continue
                        
                        if post_date < cutoff:
                            print(f"⏹️ Post antigo ({date_text})")
                            return posts_data
                        
                        # Conteúdo
                        content = ""
                        content_el = post.query_selector("span.break-words, div.feed-shared-inline-show-more-text span")
                        if content_el:
                            content = content_el.inner_text()[:500]
                        
                        # Likes
                        likes = 0
                        likes_el = post.query_selector("span.social-details-social-counts__reactions-count")
                        if likes_el:
                            likes = self._extract_number(likes_el.inner_text())
                        
                        # Comentários
                        comments = 0
                        comments_el = post.query_selector("li.social-details-social-counts__comments button")
                        if comments_el:
                            comments = self._extract_number(comments_el.inner_text())
                        
                        posts_data.append({
                            'empresa': company_url.split('/')[-2].split('?')[0],
                            'data_raw': date_text,
                            'conteudo': content,
                            'likes': likes,
                            'comentarios': comments
                        })
                        
                        posts_found += 1
                        print(f"  ✅ {posts_found}/{max_posts} - {date_text}")
                        
                        if posts_found >= max_posts:
                            break
                            
                    except Exception as e:
                        continue
                
                new_height = self.page.evaluate("document.body.scrollHeight")
                if new_height == last_height:
                    scroll_attempts += 1
                else:
                    scroll_attempts = 0
                last_height = new_height
            
            print(f"✅ Coletados {len(posts_data)} posts")
            return posts_data
            
        except Exception as e:
            print(f"❌ Erro: {e}")
            return posts_data

    def close(self):
        """Fecha o navegador"""
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()