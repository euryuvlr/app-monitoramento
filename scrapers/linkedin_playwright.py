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

    def check_page_status(self):
        """Verifica o status atual da página para diagnóstico"""
        try:
            return {
                'url': self.page.url,
                'title': self.page.title(),
                'cookies': len(self.context.cookies()),
                'html_length': len(self.page.content())
            }
        except Exception as e:
            return {'error': str(e)}

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
            
            # TENTATIVA 1: Procurar por links de posts
            try:
                # Lista de possíveis seletores para a aba de posts
                post_tab_selectors = [
                    "a[href*='posts/']",
                    "a[href*='recent-activity']",
                    "a:has-text('Posts')",
                    "a:has-text('Publicações')",
                    "button:has-text('Posts')",
                    "button:has-text('Publicações')"
                ]
                
                tab_found = False
                for selector in post_tab_selectors:
                    tab = self.page.query_selector(selector)
                    if tab:
                        print(f"✅ Aba encontrada com seletor: {selector}")
                        tab.click()
                        tab_found = True
                        break
                
                if not tab_found:
                    print("⚠️ Nenhuma aba de posts encontrada. Tentando URL direta...")
                    posts_url = company_url.rstrip('/') + "/posts/?feedView=all"
                    self.page.goto(posts_url)
            except Exception as e:
                print(f"⚠️ Erro ao clicar na aba: {e}")
                posts_url = company_url.rstrip('/') + "/posts/?feedView=all"
                self.page.goto(posts_url)
            
            time.sleep(5)
            print(f"📍 URL após navegação: {self.page.url}")
            
            # TENTATIVA 2: Rolar a página para carregar posts
            last_height = self.page.evaluate("document.body.scrollHeight")
            scroll_attempts = 0
            max_scrolls = 10
            
            while posts_found < max_posts and scroll_attempts < max_scrolls:
                print(f"⬇️ Rolando página (tentativa {scroll_attempts + 1}/{max_scrolls})...")
                self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(3)
                
                # TENTATIVA 3: Múltiplos seletores para posts
                post_selectors = [
                    "li[data-urn]",
                    "article.feed-shared-update-v2",
                    "div.occludable-update",
                    "div.feed-shared-update-v2",
                    ".feed-shared-update-v2",
                    "[data-urn]",
                    ".update-components-article"
                ]
                
                all_posts = []
                for selector in post_selectors:
                    posts = self.page.query_selector_all(selector)
                    if posts:
                        print(f"🔍 Seletor '{selector}' encontrou {len(posts)} elementos")
                        all_posts.extend(posts)
                
                # Remover duplicatas (por texto)
                unique_posts = []
                seen_texts = set()
                for post in all_posts:
                    try:
                        text = post.inner_text()[:100]
                        if text not in seen_texts:
                            seen_texts.add(text)
                            unique_posts.append(post)
                    except:
                        continue
                
                print(f"🔄 Total de posts únicos encontrados: {len(unique_posts)}")
                
                for post in unique_posts[posts_found:]:
                    try:
                        # TENTATIVA 4: Extrair data de vários lugares
                        date_text = None
                        date_selectors = [
                            "span.feed-shared-actor__sub-description",
                            "span.feed-shared-actor__sub-meta",
                            ".update-components-actor__sub-description",
                            ".feed-shared-actor__sub-description",
                            "span.t-black--light",
                            ".visually-hidden"
                        ]
                        
                        for selector in date_selectors:
                            date_elem = post.query_selector(selector)
                            if date_elem:
                                elem_text = date_elem.inner_text()
                                # Procurar por padrões de data (números + letras)
                                date_match = re.search(r'(\d+\s*[a-záéíóú]+)', elem_text.lower())
                                if date_match:
                                    date_text = date_match.group(1)
                                    print(f"  ✅ Data encontrada: '{date_text}' (seletor: {selector})")
                                    break
                        
                        if not date_text:
                            # Se não encontrou com seletores específicos, tenta no texto todo
                            full_text = post.inner_text()
                            date_match = re.search(r'(\d+\s*[a-záéíóú]+)', full_text.lower())
                            if date_match:
                                date_text = date_match.group(1)
                                print(f"  ✅ Data encontrada no texto completo: '{date_text}'")
                        
                        if not date_text:
                            print("  ⚠️ Nenhuma data encontrada")
                            continue
                        
                        post_date = self._parse_date(date_text)
                        if not post_date:
                            print(f"  ⚠️ Data não reconhecida: '{date_text}'")
                            continue
                        
                        if post_date < cutoff:
                            print(f"  ⏹️ Post antigo ({date_text}) - parando coleta")
                            return posts_data
                        
                        # Extrair conteúdo
                        content = ""
                        content_selectors = [
                            "span.break-words",
                            "div.feed-shared-inline-show-more-text span",
                            "div.feed-shared-text span",
                            ".feed-shared-text"
                        ]
                        
                        for selector in content_selectors:
                            content_el = post.query_selector(selector)
                            if content_el:
                                content = content_el.inner_text()[:500]
                                break
                        
                        # Likes
                        likes = 0
                        likes_selectors = [
                            "span.social-details-social-counts__reactions-count",
                            "button.social-details-social-counts__reactions-count",
                            "[data-anonymize='reaction-count']"
                        ]
                        
                        for selector in likes_selectors:
                            likes_el = post.query_selector(selector)
                            if likes_el:
                                likes_text = likes_el.inner_text()
                                likes = self._extract_number(likes_text)
                                break
                        
                        # Comentários
                        comments = 0
                        comments_selectors = [
                            "li.social-details-social-counts__comments button",
                            "button[aria-label*='comment']",
                            "[data-anonymize='comment-count']"
                        ]
                        
                        for selector in comments_selectors:
                            comments_el = post.query_selector(selector)
                            if comments_el:
                                comments_text = comments_el.inner_text()
                                comments = self._extract_number(comments_text)
                                break
                        
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