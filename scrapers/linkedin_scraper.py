from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time
from datetime import datetime, timedelta
import re

class LinkedInCompetitorMonitor:
    def __init__(self, email, password, headless=True):
        self.email = email
        self.password = password
        self.driver = self._setup_driver(headless)
        self.wait = WebDriverWait(self.driver, 15)

    def _setup_driver(self, headless):
        options = Options()
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        if headless:
            options.add_argument("--headless=new")
            options.add_argument("--window-size=1920,1080")
        
        driver = webdriver.Chrome(options=options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return driver

    def login(self):
        try:
            print("🔑 Fazendo login no LinkedIn...")
            self.driver.get("https://www.linkedin.com/login")
            time.sleep(1.5)
            self.wait.until(EC.presence_of_element_located((By.ID, "username"))).send_keys(self.email)
            self.driver.find_element(By.ID, "password").send_keys(self.password)
            self.driver.find_element(By.XPATH, "//button[@type='submit']").click()
            time.sleep(3)
            print("✅ Login realizado!")
            return True
        except Exception as e:
            print(f"❌ Erro no login: {e}")
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

        # Padrão para abreviaturas simples (1d, 2 sem, 3 m)
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

        # Padrão completo em português
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

        # Padrão inglês
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
        print(f"\n📊 {company_url.split('/')[-2]}")
        posts_data = []
        cutoff = datetime.now() - timedelta(days=days_back)
        posts_found = 0
        try:
            self.driver.get(company_url)
            time.sleep(3)
            print(f"📍 URL atual: {self.driver.current_url}")
            print(f"📄 Título da página: {self.driver.title}")
            
            # Tentar encontrar a aba de posts
            try:
                posts_tab = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, 'posts/')]")))
                posts_tab.click()
                print("✅ Aba 'posts' encontrada e clicada")
            except Exception as e:
                print(f"⚠️ Erro ao clicar em 'posts': {e}")
                try:
                    posts_tab = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, 'recent-activity')]")))
                    posts_tab.click()
                    print("✅ Aba 'recent-activity' encontrada e clicada")
                except Exception as e:
                    print(f"⚠️ Erro ao clicar em 'recent-activity': {e}")
                    print("⚠️ Usando URL direta...")
                    self.driver.get(company_url.rstrip('/') + "/posts/?feedView=all")
            time.sleep(3)
            print(f"📍 URL após navegação: {self.driver.current_url}")

            last_height = self.driver.execute_script("return document.body.scrollHeight")
            scroll_attempts = 0
            max_scrolls = 8

            while posts_found < max_posts and scroll_attempts < max_scrolls:
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)

                posts = self.driver.find_elements(By.CSS_SELECTOR,
                    "li[data-urn], article.feed-shared-update-v2, div.occludable-update, div.feed-shared-update-v2")
                print(f"🔄 Encontrados {len(posts)} elementos candidatos a post")

                for post in posts[posts_found:]:
                    try:
                        # Tentar extrair o texto completo do elemento que contém a data
                        date_text = None
                        
                        # Procurar em vários seletores possíveis
                        selectores = [
                            "span.feed-shared-actor__sub-description",
                            "span.feed-shared-actor__sub-meta",
                            "span.t-black--light span",
                            ".update-components-actor__sub-description",
                            ".feed-shared-actor__sub-description"
                        ]
                        
                        for seletor in selectores:
                            try:
                                elementos = post.find_elements(By.CSS_SELECTOR, seletor)
                                for elem in elementos:
                                    texto_completo = elem.text
                                    print(f"  📝 Texto do seletor '{seletor}': '{texto_completo}'")
                                    
                                    # Dividir por separadores comuns
                                    partes = re.split(r' • |\•|\|', texto_completo)
                                    print(f"  🔪 Partes divididas: {partes}")
                                    
                                    # A data geralmente é a segunda parte após os seguidores
                                    if len(partes) >= 2:
                                        candidato = partes[1].strip()
                                        if re.search(r'\d+\s*[a-záéíóú]', candidato) and len(candidato) < 20:
                                            date_text = candidato
                                            print(f"  ✅ Data encontrada: '{date_text}' (parte 2)")
                                            break
                                    
                                    # Se não achou na parte 2, procura em todas as partes
                                    if not date_text:
                                        for parte in partes:
                                            parte_clean = parte.strip()
                                            if re.search(r'\d+\s*[a-záéíóú]', parte_clean) and len(parte_clean) < 20:
                                                date_text = parte_clean
                                                print(f"  ✅ Data encontrada: '{date_text}' (outra parte)")
                                                break
                                    if date_text:
                                        break
                            except Exception as e:
                                continue
                            if date_text:
                                break
                        
                        if not date_text:
                            print(f"  ⚠️ Nenhuma data encontrada neste post")
                            continue
                        
                        # Converter a data
                        post_date = self._parse_date(date_text)
                        print(f"  📅 Data convertida: {post_date} (raw: {date_text})")
                        
                        if post_date is None:
                            print(f"  ⚠️ Data não reconhecida pelo parser: '{date_text}'")
                            continue
                        
                        if post_date < cutoff:
                            print(f"⏹️ Post antigo ({date_text}). Parando coleta desta empresa.")
                            return posts_data
                        
                        # Extrair conteúdo
                        content = ""
                        try:
                            content_el = post.find_element(By.CSS_SELECTOR,
                                "span.break-words, div.feed-shared-inline-show-more-text span, div.feed-shared-text span")
                            content = content_el.text[:500]
                        except:
                            pass
                        
                        # Likes
                        likes = 0
                        try:
                            likes_el = post.find_element(By.CSS_SELECTOR,
                                "span.social-details-social-counts__reactions-count")
                            likes = self._extract_number(likes_el.text)
                        except:
                            pass
                        
                        # Comentários
                        comments = 0
                        try:
                            comm_el = post.find_element(By.CSS_SELECTOR,
                                "li.social-details-social-counts__comments button")
                            comments = self._extract_number(comm_el.text)
                        except:
                            pass
                        
                        posts_data.append({
                            'empresa': company_url.split('/')[-2] if company_url.endswith('/') else company_url.split('/')[-1],
                            'data_raw': date_text,
                            'conteudo': content,
                            'likes': likes,
                            'comentarios': comments
                        })
                        
                        posts_found += 1
                        print(f"  ✅ Post {posts_found}/{max_posts} adicionado - Data: {date_text}")
                        
                        if posts_found >= max_posts:
                            break
                            
                    except Exception as e:
                        print(f"  ❌ Erro ao processar post: {e}")
                        continue

                # Verificar fim da página
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    scroll_attempts += 1
                    print(f"⏳ Fim da página alcançado (tentativa {scroll_attempts}/{max_scrolls})")
                else:
                    scroll_attempts = 0
                last_height = new_height

            print(f"✅ Coleta finalizada. Total de posts: {len(posts_data)}")
        except Exception as e:
            print(f"❌ Erro na coleta: {e}")
            import traceback
            traceback.print_exc()

        return posts_data

    def close(self):
        if self.driver:
            self.driver.quit()