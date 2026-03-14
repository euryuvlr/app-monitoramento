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
        print(f"\n📊 {company_url.split('/')[-2]}")
        posts_data = []
        cutoff = datetime.now() - timedelta(days=days_back)
        posts_found = 0
        try:
            self.driver.get(company_url)
            time.sleep(2)
            try:
                posts_tab = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, 'posts/')]")))
                posts_tab.click()
            except:
                try:
                    posts_tab = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, 'recent-activity')]")))
                    posts_tab.click()
                except:
                    print("⚠️ Usando URL direta...")
                    self.driver.get(company_url.rstrip('/') + "/posts/?feedView=all")
            time.sleep(2)

            last_height = self.driver.execute_script("return document.body.scrollHeight")
            scroll_attempts = 0
            max_scrolls = 8

            while posts_found < max_posts and scroll_attempts < max_scrolls:
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1.5)

                posts = self.driver.find_elements(By.CSS_SELECTOR,
                    "li[data-urn], article.feed-shared-update-v2, div.occludable-update")

                for post in posts[posts_found:]:
                    try:
                        date_text = None
                        selectores_data = [
                            "span.feed-shared-actor__sub-description",
                            "span.feed-shared-actor__sub-meta",
                            "span.t-black--light span",
                            ".update-components-actor__sub-description"
                        ]
                        for seletor in selectores_data:
                            try:
                                elemento = post.find_element(By.CSS_SELECTOR, seletor)
                                texto = elemento.text
                                partes = re.split(r' • |\•|\|', texto)
                                for parte in partes:
                                    candidato = parte.strip()
                                    if (re.search(r'\d+\s*[a-záéíóú]', candidato) 
                                        and "seguidor" not in candidato.lower()
                                        and len(candidato) < 20):
                                        date_text = candidato
                                        break
                                if date_text:
                                    break
                            except:
                                continue

                        if not date_text:
                            continue

                        post_date = self._parse_date(date_text)
                        if post_date is None:
                            continue

                        if post_date < cutoff:
                            print(f"⏹️ Post antigo ({date_text}). Parando.")
                            return posts_data

                        content = ""
                        try:
                            content_el = post.find_element(By.CSS_SELECTOR,
                                "span.break-words, div.feed-shared-inline-show-more-text span")
                            content = content_el.text[:500]
                        except:
                            pass

                        likes = 0
                        try:
                            likes_el = post.find_element(By.CSS_SELECTOR,
                                "span.social-details-social-counts__reactions-count")
                            likes = self._extract_number(likes_el.text)
                        except:
                            pass

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
                        print(f"  ✅ {posts_found}/{max_posts} - {date_text}")

                        if posts_found >= max_posts:
                            break
                    except Exception:
                        continue

                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    scroll_attempts += 1
                else:
                    scroll_attempts = 0
                last_height = new_height

            print(f"✅ Coletados {len(posts_data)} posts")
        except Exception as e:
            print(f"❌ Erro na coleta: {e}")

        return posts_data

    def close(self):
        if self.driver:
            self.driver.quit()