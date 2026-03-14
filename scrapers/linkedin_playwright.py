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
        self.user_data_dir = "./playwright_data"
        os.makedirs(self.user_data_dir, exist_ok=True)
        self._setup_driver()
        self.load_cookies_from_file()

    def _setup_driver(self):
        """Inicializa o Playwright com suporte a sessão persistente"""
        self.playwright = sync_playwright().start()
        
        self.browser = self.playwright.chromium.launch_persistent_context(
            self.user_data_dir,
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu'
            ],
            user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080}
        )
        
        self.page = self.browser.new_page()

    def load_cookies_from_file(self):
        """Carrega cookies salvos manualmente"""
        try:
            cookies_file = os.path.join(self.user_data_dir, "cookies.json")
            if os.path.exists(cookies_file):
                with open(cookies_file, "r") as f:
                    cookies = json.load(f)
                
                for cookie in cookies:
                    try:
                        cookie_dict = {
                            'name': cookie['name'],
                            'value': cookie['value'],
                            'domain': cookie.get('domain', '.linkedin.com'),
                            'path': cookie.get('path', '/'),
                        }
                        if 'secure' in cookie:
                            cookie_dict['secure'] = cookie['secure']
                        if 'httpOnly' in cookie:
                            cookie_dict['httpOnly'] = cookie['httpOnly']
                        if 'expirationDate' in cookie:
                            cookie_dict['expires'] = int(cookie['expirationDate'])
                        if 'sameSite' in cookie:
                            cookie_dict['sameSite'] = cookie['sameSite']
                        
                        self.context.add_cookies([cookie_dict])
                    except Exception as e:
                        print(f"⚠️ Erro ao adicionar cookie {cookie.get('name')}: {e}")
                        continue
                
                print(f"✅ {len(cookies)} cookies carregados!")
                return True
        except Exception as e:
            print(f"❌ Erro ao carregar cookies: {e}")
        return False

    def login(self):
        """Verifica se já existe sessão válida"""
        try:
            self.page.goto("https://www.linkedin.com/feed/")
            time.sleep(3)
            if "feed" in self.page.url:
                print("✅ Sessão existente encontrada!")
                return True
            return False
        except Exception as e:
            print(f"❌ Erro ao verificar login: {e}")
            return False

    def _check_login(self):
        """Verifica se ainda está logado"""
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
        if not self._check_login():
            print("⚠️ Sessão expirada! Faça login novamente.")
            return []
        
        print(f"\n📊 {company_url.split('/')[-2]}")
        posts_data = []
        cutoff = datetime.now() - timedelta(days=days_back)
        posts_found = 0
        
        try:
            print(f"📍 Acessando URL: {company_url}")
            self.page.goto(company_url)
            time.sleep(5)
            print(f"📍 URL atual: {self.page.url}")
            print(f"📄 Título: {self.page.title()}")
            
            posts_inicial = self.page.query_selector_all("li[data-urn], article.feed-shared-update-v2, div.occludable-update")
            print(f"🔍 Posts encontrados na página inicial: {len(posts_inicial)}")
            
            try:
                posts_link = self.page.query_selector("a[href*='posts/']")
                if posts_link:
                    print(f"✅ Link 'posts' encontrado: {posts_link.get_attribute('href')}")
                    posts_link.click()
                    print("✅ Aba 'posts' clicada")
                else:
                    recent_link = self.page.query_selector("a[href*='recent-activity']")
                    if recent_link:
                        print(f"✅ Link 'recent-activity' encontrado: {recent_link.get_attribute('href')}")
                        recent_link.click()
                        print("✅ Aba 'recent-activity' clicada")
                    else:
                        print("⚠️ Nenhum link de posts encontrado. Tentando URL direta...")
                        posts_url = company_url.rstrip('/') + "/posts/?feedView=all"
                        print(f"📍 URL direta: {posts_url}")
                        self.page.goto(posts_url)
            except Exception as e:
                print(f"⚠️ Erro ao clicar na aba: {e}")
            
            time.sleep(5)
            print(f"📍 URL após navegação: {self.page.url}")
            
            last_height = self.page.evaluate("document.body.scrollHeight")
            print(f"📏 Altura inicial da página: {last_height}")
            
            scroll_attempts = 0
            max_scrolls = 8
            
            while posts_found < max_posts and scroll_attempts < max_scrolls:
                print(f"⬇️ Rolando página (tentativa {scroll_attempts + 1})...")
                self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(3)
                
                posts = self.page.query_selector_all("li[data-urn], article.feed-shared-update-v2, div.occludable-update")
                print(f"🔄 Total de elementos encontrados após rolagem: {len(posts)}")
                
                for post in posts[posts_found:]:
                    try:
                        post_text = post.inner_text()
                        print(f"  📝 Texto completo do post: {post_text[:200]}...")
                        
                        date_text = None
                        selectores = [
                            "span.feed-shared-actor__sub-description",
                            "span.feed-shared-actor__sub-meta",
                            ".update-components-actor__sub-description",
                            ".feed-shared-actor__sub-description"
                        ]
                        
                        for selector in selectores:
                            elem = post.query_selector(selector)
                            if elem:
                                elem_text = elem.inner_text()
                                print(f"  🔍 Seletor '{selector}' retornou: '{elem_text}'")
                                
                                partes = re.split(r' • |\•|\|', elem_text)
                                print(f"  🔪 Partes divididas: {partes}")
                                
                                if len(partes) >= 2:
                                    candidato = partes[1].strip()
                                    print(f"  📅 Candidato (parte 2): '{candidato}'")
                                    if re.search(r'\d+\s*[a-záéíóú]', candidato):
                                        date_text = candidato
                                        print(f"  ✅ Data encontrada na parte 2: '{date_text}'")
                                        break
                                
                                if not date_text:
                                    for j, parte in enumerate(partes):
                                        parte_clean = parte.strip()
                                        print(f"    Parte {j}: '{parte_clean}'")
                                        if re.search(r'\d+\s*[a-záéíóú]', parte_clean):
                                            date_text = parte_clean
                                            print(f"  ✅ Data encontrada na parte {j}: '{date_text}'")
                                            break
                                if date_text:
                                    break
                        
                        if not date_text:
                            print("  ⚠️ Nenhuma data encontrada neste post")
                            continue
                        
                        post_date = self._parse_date(date_text)
                        print(f"  📅 Data convertida: {post_date}")
                        
                        if not post_date:
                            print("  ⚠️ Data não reconhecida pelo parser")
                            continue
                        
                        if post_date < cutoff:
                            print(f"  ⏹️ Post antigo ({date_text}) - parando coleta")
                            return posts_data
                        
                        content = ""
                        content_el = post.query_selector("span.break-words, div.feed-shared-inline-show-more-text span")
                        if content_el:
                            content = content_el.inner_text()[:500]
                            print(f"  📝 Conteúdo extraído: {content[:100]}...")
                        else:
                            print("  ⚠️ Conteúdo não encontrado")
                        
                        likes = 0
                        likes_el = post.query_selector("span.social-details-social-counts__reactions-count")
                        if likes_el:
                            likes_text = likes_el.inner_text()
                            likes = self._extract_number(likes_text)
                            print(f"  👍 Likes: {likes} (raw: '{likes_text}')")
                        
                        comments = 0
                        comments_el = post.query_selector("li.social-details-social-counts__comments button")
                        if comments_el:
                            comments_text = comments_el.inner_text()
                            comments = self._extract_number(comments_text)
                            print(f"  💬 Comentários: {comments} (raw: '{comments_text}')")
                        
                        posts_data.append({
                            'empresa': company_url.split('/')[-2].split('?')[0],
                            'data_raw': date_text,
                            'conteudo': content,
                            'likes': likes,
                            'comentarios': comments
                        })
                        
                        posts_found += 1
                        print(f"  ✅ Post {posts_found}/{max_posts} adicionado")
                        
                        if posts_found >= max_posts:
                            break
                            
                    except Exception as e:
                        print(f"  ❌ Erro ao processar post: {e}")
                        continue
                
                new_height = self.page.evaluate("document.body.scrollHeight")
                print(f"📏 Altura da página: {last_height} -> {new_height}")
                if new_height == last_height:
                    scroll_attempts += 1
                    print(f"⏳ Fim da página alcançado (tentativa {scroll_attempts}/{max_scrolls})")
                else:
                    scroll_attempts = 0
                last_height = new_height
            
            print(f"\n✅ Coleta finalizada. Total de posts encontrados: {len(posts_data)}")
            return posts_data
            
        except Exception as e:
            print(f"❌ Erro na coleta: {e}")
            import traceback
            traceback.print_exc()
            return posts_data

    def close(self):
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()